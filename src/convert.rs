//! Converter from ruff's AST to CPython `ast` model objects (D3).
//!
//! The converter walks the parsed ruff AST and materialises real CPython
//! `ast` objects through pyo3: one Python object per node, fields passed
//! positionally in `_fields` order, and positions attached as keyword
//! arguments (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`).
//!
//! Position contract: ruff's `TextSize` offsets are UTF-8 byte offsets over
//! the decoded text, which is exactly CPython 3.8+'s position contract; the
//! offsets are translated to (lineno, byte column) pairs using a line index
//! built over the newline-normalized source text.
//!
//! Object identity: every ruff node is converted exactly once, so references
//! inside the tree (for example `statement.targets[0]` and the target node the
//! visitor visits) are the same Python object, as the Q2 contract requires.
//!
//! Error contract: an unmapped ruff node shape raises (fails the parse)
//! loudly — a degraded tree is never emitted. `slice-05` completes the
//! remaining grammar (match statements, t-strings, type params, walrus,
//! star expressions, yield/await, type comments).

use pyo3::conversion::IntoPyObject;
use pyo3::prelude::*;
use pyo3::types::{PyAnyMethods, PyBytes, PyDict, PyDictMethods, PyList, PyModule, PyString, PyTuple};
use std::cell::RefCell;
use std::collections::{BTreeMap, HashMap, HashSet};

use ruff_python_ast as rast;
use ruff_python_ast::str_prefix::StringLiteralPrefix;
use ruff_text_size::{Ranged, TextRange, TextSize};

/// One f-string value element kept in raw form so adjacent constants can be
/// merged the way CPython merges implicitly concatenated literal chunks.
enum RawValue {
    Constant { text: String, range: TextRange, kind: Option<&'static str> },
    Formatted(PyObject),
}

/// The code tokens the type-comment attachment rules look at.
#[derive(Clone, Copy, PartialEq)]
enum CodeKind {
    Colon,
    Comma,
    Star,
    Lpar,
    Lsqb,
    Lbrace,
    Rpar,
    Rsqb,
    Rbrace,
    Other,
}

struct CodeToken {
    kind: CodeKind,
    start: u32,
    end: u32,
}

/// One token of the parser stream CPython's PEG parser sees: every code
/// token, the logical-line newlines, INDENT/DEDENT, and — in place of the
/// comment — the type comment itself. Regular comments, blank-line newlines,
/// and newlines inside brackets are absent, exactly like CPython's parser
/// stream (the lexer only reports them to the `tokenize` module).
enum StreamToken {
    Code(CodeToken),
    Newline,
    Indent,
    Dedent,
    TypeComment { text: String, range: TextRange },
}

/// Token-level context built once per parse from the lexed token stream.
pub struct TokenContext {
    pub type_comments: bool,
    stream: Vec<StreamToken>,
    /// `# type: ignore` comments as (line, tag) pairs in source order.
    ignores: Vec<(u32, String)>,
    /// Raw text between the braces of every interpolation, keyed by the `{`
    /// offset: the t-string `Interpolation.str` field (CPython keeps the
    /// verbatim source between `{` and the conversion/`:`/`}`).
    interpolation_strs: HashMap<u32, String>,
}

impl TokenContext {
    pub fn interpolation_str(&self, interpolation_start: u32) -> Option<&str> {
        self.interpolation_strs.get(&interpolation_start).map(String::as_str)
    }

    /// Classify every comment token the way CPython's lexer does (`# type:`
    /// prefix with optional spaces/tabs around the words), build the parser
    /// stream, and record the `# type: ignore` tags.
    pub fn collect(source: &str, tokens: &[ruff_python_ast::token::Token]) -> Self {
        let line_starts = build_line_index(source);
        let mut stream: Vec<StreamToken> = vec![];
        let mut ignores: Vec<(u32, String)> = vec![];
        // Whether any code token was seen on the current physical line so far.
        let mut code_on_line = false;
        // Bracket depth of the parser stream so far.
        let mut depth = 0_u32;
        for token in tokens {
            match token.kind() {
                ruff_python_ast::token::TokenKind::Comment => {
                    let range = token.range();
                    let comment = &source[range.start().to_usize()..range.end().to_usize()];
                    let alone = !code_on_line;
                    match classify_type_comment(comment, alone) {
                        TypeComment::None => {}
                        TypeComment::Ignore { tag } => {
                            ignores.push((line_number(&line_starts, range.start()), tag));
                        }
                        TypeComment::Comment { text } => {
                            // The type comment replaces the comment token.
                            stream.push(StreamToken::TypeComment { text, range });
                        }
                    }
                }
                ruff_python_ast::token::TokenKind::NonLogicalNewline => {
                    // Blank lines and in-bracket newlines are invisible to the
                    // parser — except the newline of a top-level `# type:`
                    // comment line, which CPython reports as a logical NEWLINE
                    // (only `# type: ignore` lines are swallowed whole).
                    let follows_type_comment = matches!(stream.last(), Some(StreamToken::TypeComment { .. }));
                    if follows_type_comment && depth == 0 {
                        stream.push(StreamToken::Newline);
                    }
                    code_on_line = false;
                }
                ruff_python_ast::token::TokenKind::Newline => {
                    stream.push(StreamToken::Newline);
                    code_on_line = false;
                }
                ruff_python_ast::token::TokenKind::Indent => stream.push(StreamToken::Indent),
                ruff_python_ast::token::TokenKind::Dedent => stream.push(StreamToken::Dedent),
                _ => {
                    match token.kind() {
                        ruff_python_ast::token::TokenKind::Lpar
                        | ruff_python_ast::token::TokenKind::Lsqb
                        | ruff_python_ast::token::TokenKind::Lbrace => depth += 1,
                        ruff_python_ast::token::TokenKind::Rpar
                        | ruff_python_ast::token::TokenKind::Rsqb
                        | ruff_python_ast::token::TokenKind::Rbrace => depth -= 1,
                        _ => {}
                    }
                    stream.push(StreamToken::Code(CodeToken {
                        kind: code_kind(token.kind()),
                        start: token.start().to_u32(),
                        end: token.end().to_u32(),
                    }));
                    code_on_line = true;
                }
            }
        }
        let interpolation_strs = collect_interpolation_strs(source, tokens);
        Self {
            type_comments: true,
            stream,
            ignores,
            interpolation_strs,
        }
    }

    /// The context for parses without `type_comments=True`: no comment is
    /// visible to the parser, so nothing is attached or collected.
    pub fn without_type_comments(source: &str, tokens: &[ruff_python_ast::token::Token]) -> Self {
        let mut context = Self::collect(source, tokens);
        context.type_comments = false;
        context
    }
}

enum TypeComment {
    None,
    Ignore { tag: String },
    Comment { text: String },
}

/// CPython's lexer rule (`Parser/lexer/lexer.c`): the comment must match
/// `# type: ` where each space matches zero or more spaces or tabs; the
/// remainder is the type comment text. Text starting with `ignore` followed
/// by a non-alphanumeric ASCII byte (or the end of the line) is a type
/// ignore, and its tag is everything after `ignore` — plus the newline when
/// the comment is the only thing on its line (the lexer consumes it).
fn classify_type_comment(comment: &str, alone_on_line: bool) -> TypeComment {
    let mut index = 1; // Skip '#'.
    index += leading_spaces_or_tabs(&comment[index..]);
    if !comment[index..].starts_with("type:") {
        return TypeComment::None;
    }
    index += "type:".len();
    index += leading_spaces_or_tabs(&comment[index..]);
    let content = &comment[index..];
    if let Some(after) = content.strip_prefix("ignore") {
        let is_ignore = match after.as_bytes().first() {
            None => true,
            Some(&byte) => byte < 128 && !byte.is_ascii_alphanumeric(),
        };
        if is_ignore {
            let mut tag = after.to_string();
            if alone_on_line {
                tag.push('\n');
            }
            return TypeComment::Ignore { tag };
        }
    }
    TypeComment::Comment {
        text: content.to_string(),
    }
}

fn leading_spaces_or_tabs(text: &str) -> usize {
    text.bytes().take_while(|byte| matches!(byte, b' ' | b'\t')).count()
}

fn line_number(line_starts: &[u32], offset: ruff_text_size::TextSize) -> u32 {
    let offset = offset.to_u32();
    let index = line_starts
        .binary_search(&offset)
        .unwrap_or_else(|insertion| insertion - 1);
    index as u32 + 1
}

fn code_kind(kind: ruff_python_ast::token::TokenKind) -> CodeKind {
    use ruff_python_ast::token::TokenKind;
    match kind {
        TokenKind::Colon => CodeKind::Colon,
        TokenKind::Comma => CodeKind::Comma,
        TokenKind::Star => CodeKind::Star,
        TokenKind::Lpar => CodeKind::Lpar,
        TokenKind::Lsqb => CodeKind::Lsqb,
        TokenKind::Lbrace => CodeKind::Lbrace,
        TokenKind::Rpar => CodeKind::Rpar,
        TokenKind::Rsqb => CodeKind::Rsqb,
        TokenKind::Rbrace => CodeKind::Rbrace,
        _ => CodeKind::Other,
    }
}

/// Record the raw text between the braces of every interpolation: the source
/// between the `{` token and the first conversion (`!`), format-spec (`:`) or
/// debug (`=`) token at the interpolation's own level, or the closing `}`
/// (CPython keeps this text verbatim in the t-string `Interpolation.str`
/// field).
fn collect_interpolation_strs(source: &str, tokens: &[ruff_python_ast::token::Token]) -> HashMap<u32, String> {
    use ruff_python_ast::token::TokenKind;
    let mut result = HashMap::new();
    // Strings currently open; the stack carries whether each is a t-string so
    // nested f-strings inside a t-string are skipped as units.
    let mut strings: Vec<bool> = vec![];
    // Open interpolations: (brace offset, bracket depth so far, boundary).
    let mut interpolations: Vec<(u32, u32, Option<usize>)> = vec![];
    for (index, token) in tokens.iter().enumerate() {
        match token.kind() {
            TokenKind::FStringStart => strings.push(false),
            TokenKind::TStringStart => strings.push(true),
            TokenKind::FStringEnd => {
                strings.pop();
            }
            TokenKind::Lbrace if !strings.is_empty() => {
                interpolations.push((token.start().to_u32(), 0, None));
            }
            _ => {
                if let Some(interpolation) = interpolations.last_mut() {
                    match token.kind() {
                        TokenKind::Lpar | TokenKind::Lsqb | TokenKind::Lbrace => {
                            interpolation.1 += 1;
                        }
                        TokenKind::Rpar | TokenKind::Rsqb | TokenKind::Rbrace => {
                            if interpolation.1 == 0 {
                                let (start, _, boundary) = interpolations.pop().unwrap();
                                let end = match boundary {
                                    Some(boundary) => tokens[boundary].start().to_u32(),
                                    None => token.start().to_u32(),
                                };
                                // The text starts after the `{` token itself.
                                result.insert(start, source[start as usize + 1..end as usize].to_string());
                            } else {
                                interpolation.1 -= 1;
                            }
                        }
                        TokenKind::Colon | TokenKind::Exclamation | TokenKind::Equal => {
                            // The first of `:` (format spec), `!` (conversion)
                            // or `=` (debug text) at the interpolation's own
                            // level ends the expression source; `=` can only
                            // appear at this level as a debug marker.
                            if interpolation.1 == 0 && interpolation.2.is_none() {
                                interpolation.2 = Some(index);
                            }
                        }
                        _ => {}
                    }
                }
            }
        }
    }
    result
}

/// Which statement a block-introducing colon belongs to, for the type-comment
/// attachment positions that may follow it (D8).
#[derive(Clone, Copy)]
enum ColonOwnerKind {
    Def,
    For,
    With,
}

#[derive(Clone)]
struct ColonOwner {
    kind: ColonOwnerKind,
    node: PyObject,
}

pub struct Converter<'py> {
    py: Python<'py>,
    source: &'py str,
    line_starts: Vec<u32>,
    ast_module: Bound<'py, PyModule>,
    builtins: Bound<'py, PyModule>,
    /// Classes are resolved on first use: `ast.TryStar` (and other newer
    /// nodes) does not exist on every supported interpreter, and an absent
    /// class only matters when a source actually uses that construct.
    classes: RefCell<HashMap<&'static str, Option<PyObject>>>,
    /// Assignment statements keyed by their end offset: a trailing `# type:`
    /// comment (D8) must directly follow the statement's last token, and the
    /// statement is the one that ends there (D8: only `ast.Assign` accepts
    /// one, including inside one-line suites).
    assign_ends: RefCell<BTreeMap<u32, PyObject>>,
    /// Every statement node keyed by its end offset: CPython's rule spans make
    /// a statement extend through a trailing type comment, and so does every
    /// compound statement whose block ends with it.
    stmt_ends: RefCell<BTreeMap<u32, Vec<PyObject>>>,
    /// The end offsets already extended to a type comment, to keep a comment
    /// from extending the same node twice.
    extended_ends: RefCell<HashSet<u32>>,
    /// `arg` nodes of function definitions (not lambdas) keyed by their end
    /// offset, for type comments inside a parameter list.
    arg_ends: RefCell<BTreeMap<u32, PyObject>>,
    /// Block-introducing colons that accept a following type comment, keyed by
    /// the colon's start offset.
    colon_owners: RefCell<HashMap<u32, ColonOwner>>,
    /// Offsets of the `(` tokens that open a function definition's parameter
    /// list (lambdas excluded): a type comment directly inside them attaches
    /// to the parameter it follows.
    parameter_list_opens: RefCell<HashSet<u32>>,
    /// Token context for the t-string `Interpolation.str` extraction, set by
    /// `module` (the only entry point that builds a full module).
    tokens: RefCell<Option<&'py TokenContext>>,
}

impl<'py> Converter<'py> {
    /// Build a converter over the newline-normalized, decoded source text.
    pub fn new(py: Python<'py>, source: &'py str) -> PyResult<Self> {
        let line_starts = build_line_index(source);
        let ast_module = py.import("ast")?;
        let builtins = py.import("builtins")?;
        Ok(Self {
            py,
            source,
            line_starts,
            ast_module,
            builtins,
            classes: RefCell::new(HashMap::new()),
            assign_ends: RefCell::new(BTreeMap::new()),
            stmt_ends: RefCell::new(BTreeMap::new()),
            extended_ends: RefCell::new(HashSet::new()),
            arg_ends: RefCell::new(BTreeMap::new()),
            colon_owners: RefCell::new(HashMap::new()),
            parameter_list_opens: RefCell::new(HashSet::new()),
            tokens: RefCell::new(None),
        })
    }

    /// Convert the module, applying the type-comment contract (D8) when the
    /// seam asked for `type_comments=True`.
    pub fn module(
        &self,
        module: &rast::ModModule,
        tokens: &'py TokenContext,
    ) -> PyResult<PyObject> {
        self.tokens.replace(Some(tokens));
        let body = self.body(&module.body)?;
        let type_ignores = if tokens.type_comments {
            self.apply_type_comments(tokens)?
        } else {
            self.py_list(vec![])?
        };
        self.make("Module", vec![body, type_ignores], None)
    }

    /// Convert a parsed expression (`ast.parse(..., mode='eval')` shape): a
    /// position-less `ast.Expression` wrapping the expression node.
    pub fn expression(
        &self,
        parsed: &rast::ModExpression,
        tokens: &'py TokenContext,
    ) -> PyResult<PyObject> {
        self.tokens.replace(Some(tokens));
        let body = self.expr(&parsed.body)?;
        self.make_nopositions("Expression", vec![body])
    }

    /// Materialise an `ast.FunctionType` (the `mode='func_type'` shape) from
    /// already converted argument types and the return type.
    pub fn function_type(&self, argtypes: Vec<PyObject>, returns: PyObject) -> PyResult<PyObject> {
        let argtypes = self.py_list(argtypes)?;
        self.make_nopositions("FunctionType", vec![argtypes, returns])
    }

    /// Publish the token context for entry points whose tree is built by
    /// helpers outside `module` (the t-string `Interpolation.str` extraction
    /// reads it).
    pub fn set_tokens(&self, tokens: &'py TokenContext) {
        self.tokens.replace(Some(tokens));
    }

    /// Attach the `# type:` comments to the nodes CPython's parser attaches
    /// them to, and collect the `# type: ignore` comments as `TypeIgnore`
    /// nodes for `Module.type_ignores`.
    fn apply_type_comments(&self, tokens: &TokenContext) -> PyResult<PyObject> {
        let mut type_ignores: Vec<PyObject> = vec![];
        let stream = &tokens.stream;
        let mut brackets: Vec<u32> = vec![];
        for (index, token) in stream.iter().enumerate() {
            match token {
                StreamToken::Code(code) => match code.kind {
                    CodeKind::Lpar | CodeKind::Lsqb | CodeKind::Lbrace => {
                        brackets.push(code.start);
                    }
                    CodeKind::Rpar | CodeKind::Rsqb | CodeKind::Rbrace => {
                        brackets.pop();
                    }
                    _ => {}
                },
                StreamToken::TypeComment { text, range } => {
                    let previous = if index >= 1 { stream.get(index - 1) } else { None };
                    match previous {
                        Some(StreamToken::Newline) => {
                            // The comment is alone on its line: it attaches to
                            // a function definition whose block starts on the
                            // next line (the `func_type_comment` position).
                            let colon = match index.checked_sub(2) {
                                Some(previous_index) => match &stream[previous_index] {
                                    StreamToken::Code(code) if code.kind == CodeKind::Colon => code.start,
                                    _ => return Err(self.type_comment_error()),
                                },
                                None => return Err(self.type_comment_error()),
                            };
                            let owner = self.colon_owner(colon);
                            let is_def = matches!(owner.as_ref().map(|owner| owner.kind), Some(ColonOwnerKind::Def));
                            let block_follows = matches!(stream.get(index + 1), Some(StreamToken::Newline))
                                && matches!(stream.get(index + 2), Some(StreamToken::Indent));
                            if !is_def || !block_follows {
                                return Err(self.type_comment_error());
                            }
                            owner.unwrap().node.setattr(self.py, "type_comment", text)?;
                        }
                        Some(StreamToken::Code(previous)) => {
                            if previous.kind == CodeKind::Colon {
                                let Some(owner) = self.colon_owner(previous.start) else {
                                    return Err(self.type_comment_error());
                                };
                                let block_follows = matches!(stream.get(index + 1), Some(StreamToken::Newline))
                                    && matches!(stream.get(index + 2), Some(StreamToken::Indent));
                                // `for`/`with` accept the comment only right
                                // before an indented block; a second type
                                // comment after a def's trailing comment is the
                                // "two type comments on def" rejection.
                                if !block_follows {
                                    return Err(self.type_comment_error());
                                }
                                owner.node.setattr(self.py, "type_comment", text)?;
                            } else if self
                                .parameter_list_opens
                                .borrow()
                                .contains(brackets.last().unwrap_or(&u32::MAX))
                            {
                                let next = stream.get(index + 1);
                                if previous.kind == CodeKind::Comma {
                                    if matches!(
                                        index.checked_sub(2).and_then(|position| stream.get(position)),
                                        Some(StreamToken::Code(code)) if code.kind == CodeKind::Star
                                    ) {
                                        return Err(self.type_comment_error());
                                    }
                                    // Attach to the parameter whose own syntax
                                    // ends at the comma: the grammar position is
                                    // right after a parameter's own comma, so the
                                    // `/` and bare `*` separators have no owner.
                                    let arg = self.arg_ends.borrow().get(&previous.start).cloned();
                                    let Some(arg) = arg else {
                                        return Err(self.type_comment_error());
                                    };
                                    arg.setattr(self.py, "type_comment", text)?;
                                } else if matches!(next, Some(StreamToken::Code(code)) if code.kind == CodeKind::Rpar) {
                                    // Attach to the parameter the comment follows:
                                    // its own syntax ends at the previous token.
                                    let arg = self.arg_ends.borrow().get(&previous.end).cloned();
                                    let Some(arg) = arg else {
                                        return Err(self.type_comment_error());
                                    };
                                    arg.setattr(self.py, "type_comment", text)?;
                                } else {
                                    return Err(self.type_comment_error());
                                }
                            } else if !brackets.is_empty() {
                                // Inside any other bracket pair (call arguments,
                                // display literals, ...): no rule accepts it.
                                return Err(self.type_comment_error());
                            } else if let Some(assign) = self
                                .assign_ends
                                .borrow()
                                .get(&previous.end)
                                .cloned()
                            {
                                assign.setattr(self.py, "type_comment", text)?;
                                // CPython's Assign node spans through the type
                                // comment (the comment is the rule's last token),
                                // and so does every statement whose block ends
                                // with the assign.
                                self.extend_statement_ends(previous.end, range.end())?;
                            } else {
                                return Err(self.type_comment_error());
                            }
                        }
                        // Directly after INDENT/DEDENT there is no rule that
                        // accepts a type comment.
                        _ => return Err(self.type_comment_error()),
                    }
                }
                _ => {}
            }
        }
        for (line, tag) in &tokens.ignores {
            let line = self.int_obj(u64::from(*line))?;
            let tag = self.str_obj(tag);
            type_ignores.push(self.make_nopositions("TypeIgnore", vec![line, tag])?);
        }
        self.py_list(type_ignores)
    }

    /// Move the end position of the statement that ends at `original_end` —
    /// and of every enclosing compound statement ending there — to `new_end`
    /// (the end of the trailing type comment).
    fn extend_statement_ends(&self, original_end: u32, new_end: TextSize) -> PyResult<()> {
        if !self.extended_ends.borrow_mut().insert(original_end) {
            return Ok(());
        }
        let (end_lineno, end_col_offset) = self.position(new_end);
        let statements = self
            .stmt_ends
            .borrow()
            .range(original_end..=original_end)
            .next_back()
            .map(|(_, nodes)| nodes.clone());
        if let Some(statements) = statements {
            for statement in statements {
                statement.setattr(self.py, "end_lineno", end_lineno)?;
                statement.setattr(self.py, "end_col_offset", end_col_offset)?;
            }
        }
        Ok(())
    }

    fn colon_owner(&self, colon_start: u32) -> Option<ColonOwner> {
        self.colon_owners.borrow().get(&colon_start).cloned()
    }

    fn type_comment_error(&self) -> PyErr {
        PyErr::new::<crate::ParseError, _>("invalid type comment placement")
    }

    // -- primitive builders -------------------------------------------------

    fn cls(&self, name: &'static str) -> PyResult<Bound<'py, PyAny>> {
        if let Some(cached) = self.classes.borrow().get(name) {
            return match cached {
                Some(class) => Ok(class.bind(self.py).clone()),
                None => self.unsupported(&format!("ast.{name} is not available on this interpreter")),
            };
        }
        let class = match self.ast_module.getattr(name) {
            Ok(class) => Some(class.unbind()),
            Err(_) => None,
        };
        self.classes.borrow_mut().insert(name, class.clone());
        match class {
            Some(class) => Ok(class.into_bound(self.py)),
            None => self.unsupported(&format!("ast.{name} is not available on this interpreter")),
        }
    }

    fn str_obj(&self, text: &str) -> PyObject {
        PyString::new(self.py, text).unbind().into_any()
    }

    fn int_obj(&self, value: u64) -> PyResult<PyObject> {
        Ok(value.into_pyobject(self.py)?.unbind().into_any())
    }

    fn signed_int_obj(&self, value: i64) -> PyResult<PyObject> {
        Ok(value.into_pyobject(self.py)?.unbind().into_any())
    }

    fn float_obj(&self, value: f64) -> PyResult<PyObject> {
        Ok(value.into_pyobject(self.py)?.unbind().into_any())
    }

    fn bool_obj(&self, value: bool) -> PyObject {
        use pyo3::types::PyBool;
        let borrowed = PyBool::new(self.py, value);
        borrowed.to_owned().unbind().into_any()
    }

    fn bytes_obj(&self, value: &[u8]) -> PyObject {
        PyBytes::new(self.py, value).unbind().into_any()
    }

    fn none_obj(&self) -> PyObject {
        self.py.None()
    }

    fn py_list(&self, items: Vec<PyObject>) -> PyResult<PyObject> {
        Ok(PyList::new(self.py, items)?.unbind().into_any())
    }

    /// Create an `ast` node: fields positionally, positions as kwargs.
    fn make(&self, name: &'static str, fields: Vec<PyObject>, range: Option<TextRange>) -> PyResult<PyObject> {
        let args = PyTuple::new(self.py, fields)?;
        let kwargs = match range {
            Some(range) => {
                let (lineno, col_offset, end_lineno, end_col_offset) = self.positions(range);
                let kwargs = PyDict::new(self.py);
                kwargs.set_item("lineno", lineno)?;
                kwargs.set_item("col_offset", col_offset)?;
                kwargs.set_item("end_lineno", end_lineno)?;
                kwargs.set_item("end_col_offset", end_col_offset)?;
                Some(kwargs)
            }
            None => None,
        };
        self.cls(name)?.call(args, kwargs.as_ref()).map(|node| node.unbind())
    }

    /// Create an `ast` node without position attributes (helper nodes).
    fn make_nopositions(&self, name: &'static str, fields: Vec<PyObject>) -> PyResult<PyObject> {
        let args = PyTuple::new(self.py, fields)?;
        self.cls(name)?.call(args, None).map(|node| node.unbind())
    }

    fn positions(&self, range: TextRange) -> (u32, u32, u32, u32) {
        let (lineno, col_offset) = self.position(range.start());
        let (end_lineno, end_col_offset) = self.position(range.end());
        (lineno, col_offset, end_lineno, end_col_offset)
    }

    /// Translate a byte offset into a (1-based lineno, byte column) pair.
    fn position(&self, offset: TextSize) -> (u32, u32) {
        let offset = offset.to_u32();
        let index = self
            .line_starts
            .binary_search(&offset)
            .unwrap_or_else(|insertion| insertion - 1);
        (index as u32 + 1, offset - self.line_starts[index])
    }

    /// Raise for ruff node shapes this slice does not map yet (slice 5's scope).
    fn unsupported<T>(&self, description: &str) -> PyResult<T> {
        Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>(format!(
            "ruff-to-ast converter: unmapped node shape: {description}"
        )))
    }

    // -- statement lists ----------------------------------------------------

    fn body(&self, statements: &[rast::Stmt]) -> PyResult<PyObject> {
        let mut converted: Vec<PyObject> = vec![];
        for statement in statements {
            let node = self.stmt(statement)?;
            self.stmt_ends
                .borrow_mut()
                .entry(statement.range().end().to_u32())
                .or_default()
                .push(node.clone_ref(self.py));
            converted.push(node);
        }
        self.py_list(converted)
    }

    fn stmt(&self, statement: &rast::Stmt) -> PyResult<PyObject> {
        match statement {
            rast::Stmt::Expr(stmt) => {
                let value = self.expr(&stmt.value)?;
                self.make("Expr", vec![value], Some(stmt.range()))
            }
            rast::Stmt::Assign(stmt) => {
                let targets = stmt
                    .targets
                    .iter()
                    .map(|target| self.expr(target))
                    .collect::<PyResult<Vec<_>>>()?;
                let targets = self.py_list(targets)?;
                let value = self.expr(&stmt.value)?;
                let type_comment = self.none_obj();
                let node = self.make("Assign", vec![targets, value, type_comment], Some(stmt.range()))?;
                self.assign_ends.borrow_mut().insert(stmt.range().end().to_u32(), node.clone());
                Ok(node)
            }
            rast::Stmt::AnnAssign(stmt) => {
                let target = self.expr(&stmt.target)?;
                let annotation = self.expr(&stmt.annotation)?;
                let value = match &stmt.value {
                    Some(value) => self.expr(value)?,
                    None => self.none_obj(),
                };
                let simple = self.int_obj(u64::from(stmt.simple))?;
                self.make("AnnAssign", vec![target, annotation, value, simple], Some(stmt.range()))
            }
            rast::Stmt::AugAssign(stmt) => {
                let target = self.expr(&stmt.target)?;
                let op = self.operator(&stmt.op)?;
                let value = self.expr(&stmt.value)?;
                self.make("AugAssign", vec![target, op, value], Some(stmt.range()))
            }
            rast::Stmt::Return(stmt) => {
                let value = match &stmt.value {
                    Some(value) => self.expr(value)?,
                    None => self.none_obj(),
                };
                self.make("Return", vec![value], Some(stmt.range()))
            }
            rast::Stmt::Delete(stmt) => {
                let targets = stmt
                    .targets
                    .iter()
                    .map(|target| self.expr(target))
                    .collect::<PyResult<Vec<_>>>()?;
                let targets = self.py_list(targets)?;
                self.make("Delete", vec![targets], Some(stmt.range()))
            }
            rast::Stmt::Pass(stmt) => self.make("Pass", vec![], Some(stmt.range())),
            rast::Stmt::Break(stmt) => self.make("Break", vec![], Some(stmt.range())),
            rast::Stmt::Continue(stmt) => self.make("Continue", vec![], Some(stmt.range())),
            rast::Stmt::Global(stmt) => {
                let names = stmt.names.iter().map(|name| self.str_obj(name.as_str())).collect::<Vec<_>>();
                let names = self.py_list(names)?;
                self.make("Global", vec![names], Some(stmt.range()))
            }
            rast::Stmt::Nonlocal(stmt) => {
                let names = stmt.names.iter().map(|name| self.str_obj(name.as_str())).collect::<Vec<_>>();
                let names = self.py_list(names)?;
                self.make("Nonlocal", vec![names], Some(stmt.range()))
            }
            rast::Stmt::Assert(stmt) => {
                let test = self.expr(&stmt.test)?;
                let msg = match &stmt.msg {
                    Some(msg) => self.expr(msg)?,
                    None => self.none_obj(),
                };
                self.make("Assert", vec![test, msg], Some(stmt.range()))
            }
            rast::Stmt::Raise(stmt) => {
                let exc = match &stmt.exc {
                    Some(exc) => self.expr(exc)?,
                    None => self.none_obj(),
                };
                let cause = match &stmt.cause {
                    Some(cause) => self.expr(cause)?,
                    None => self.none_obj(),
                };
                self.make("Raise", vec![exc, cause], Some(stmt.range()))
            }
            rast::Stmt::Import(stmt) => {
                let names = stmt.names.iter().map(|alias| self.alias(alias)).collect::<PyResult<Vec<_>>>()?;
                let names = self.py_list(names)?;
                self.make("Import", vec![names], Some(stmt.range()))
            }
            rast::Stmt::ImportFrom(stmt) => {
                let module = match &stmt.module {
                    Some(module) => self.str_obj(module.as_str()),
                    None => self.none_obj(),
                };
                let names = stmt.names.iter().map(|alias| self.alias(alias)).collect::<PyResult<Vec<_>>>()?;
                let names = self.py_list(names)?;
                let level = self.int_obj(u64::from(stmt.level))?;
                self.make("ImportFrom", vec![module, names, level], Some(stmt.range()))
            }
            rast::Stmt::FunctionDef(stmt) => {
                let class_name = if stmt.is_async { "AsyncFunctionDef" } else { "FunctionDef" };
                self.definition(
                    class_name,
                    stmt.is_async,
                    &stmt.decorator_list,
                    &stmt.name,
                    &stmt.parameters,
                    &stmt.returns,
                    &stmt.body,
                    &stmt.type_params,
                    stmt.range(),
                )
            }
            rast::Stmt::ClassDef(stmt) => {
                let decorator_list = stmt
                    .decorator_list
                    .iter()
                    .map(|decorator| self.expr(&decorator.expression))
                    .collect::<PyResult<Vec<_>>>()?;
                let decorators = self.py_list(decorator_list)?;
                let bases = match &stmt.arguments {
                    Some(arguments) => {
                        let bases = arguments.args.iter().map(|base| self.expr(base)).collect::<PyResult<Vec<_>>>()?;
                        self.py_list(bases)?
                    }
                    None => self.py_list(vec![])?,
                };
                let keywords = match &stmt.arguments {
                    Some(arguments) => arguments
                        .keywords
                        .iter()
                        .map(|keyword| self.keyword(keyword))
                        .collect::<PyResult<Vec<_>>>()?,
                    None => vec![],
                };
                let keywords = self.py_list(keywords)?;
                let body = self.body(&stmt.body)?;
                let type_params = self.type_params(&stmt.type_params)?;
                let name = self.str_obj(stmt.name.as_str());
                let start = match stmt.decorator_list.last() {
                    Some(decorator) => self.definition_keyword_start(decorator.range().end(), "class")?,
                    None => stmt.range().start(),
                };
                self.make(
                    "ClassDef",
                    vec![name, bases, keywords, body, decorators, type_params],
                    Some(TextRange::new(start, stmt.range().end())),
                )
            }
            rast::Stmt::If(stmt) => self.if_statement(stmt),
            rast::Stmt::While(stmt) => {
                let test = self.expr(&stmt.test)?;
                let body = self.body(&stmt.body)?;
                let orelse = self.body(&stmt.orelse)?;
                self.make("While", vec![test, body, orelse], Some(stmt.range()))
            }
            rast::Stmt::For(stmt) => {
                let class_name = if stmt.is_async { "AsyncFor" } else { "For" };
                let target = self.expr(&stmt.target)?;
                let iter = self.expr(&stmt.iter)?;
                let body = self.body(&stmt.body)?;
                let orelse = self.body(&stmt.orelse)?;
                let type_comment = self.none_obj();
                let node = self.make(class_name, vec![target, iter, body, orelse, type_comment], Some(stmt.range()))?;
                self.register_block_colon(ColonOwnerKind::For, stmt.iter.range().end(), &node);
                Ok(node)
            }
            rast::Stmt::With(stmt) => {
                let class_name = if stmt.is_async { "AsyncWith" } else { "With" };
                let items = stmt.items.iter().map(|item| self.with_item(item)).collect::<PyResult<Vec<_>>>()?;
                let items = self.py_list(items)?;
                let body = self.body(&stmt.body)?;
                let type_comment = self.none_obj();
                let last_item_end = stmt.items.last().map(|item| item.range().end());
                let node = self.make(class_name, vec![items, body, type_comment], Some(stmt.range()))?;
                if let Some(last_item_end) = last_item_end {
                    self.register_block_colon(ColonOwnerKind::With, last_item_end, &node);
                }
                Ok(node)
            }
            rast::Stmt::Match(stmt) => {
                let subject = self.expr(&stmt.subject)?;
                let cases = stmt
                    .cases
                    .iter()
                    .map(|case| self.match_case(case))
                    .collect::<PyResult<Vec<_>>>()?;
                let cases = self.py_list(cases)?;
                self.make("Match", vec![subject, cases], Some(stmt.range()))
            }
            rast::Stmt::TypeAlias(stmt) => {
                let name = self.expr(&stmt.name)?;
                let type_params = self.type_params(&stmt.type_params)?;
                let value = self.expr(&stmt.value)?;
                self.make("TypeAlias", vec![name, type_params, value], Some(stmt.range()))
            }
            rast::Stmt::Try(stmt) => {
                let class_name = if stmt.is_star { "TryStar" } else { "Try" };
                let body = self.body(&stmt.body)?;
                let handlers = stmt
                    .handlers
                    .iter()
                    .map(|handler| match handler {
                        rast::ExceptHandler::ExceptHandler(handler) => self.except_handler(handler),
                    })
                    .collect::<PyResult<Vec<_>>>()?;
                let handlers = self.py_list(handlers)?;
                let orelse = self.body(&stmt.orelse)?;
                let finalbody = self.body(&stmt.finalbody)?;
                self.make(class_name, vec![body, handlers, orelse, finalbody], Some(stmt.range()))
            }
            rast::Stmt::IpyEscapeCommand(_) => self.unsupported("IPython escape command"),
        }
    }

    /// Shared FunctionDef/AsyncFunctionDef builder.
    #[allow(clippy::too_many_arguments)]
    fn definition(
        &self,
        class_name: &'static str,
        is_async: bool,
        decorators: &[rast::Decorator],
        name: &rast::Identifier,
        parameters: &rast::Parameters,
        returns: &Option<Box<rast::Expr>>,
        body: &[rast::Stmt],
        type_params: &Option<Box<rast::TypeParams>>,
        range: TextRange,
    ) -> PyResult<PyObject> {
        let decorator_list = decorators
            .iter()
            .map(|decorator| self.expr(&decorator.expression))
            .collect::<PyResult<Vec<_>>>()?;
        let decorator_list = self.py_list(decorator_list)?;
        let name = self.str_obj(name.as_str());
        // The signature's colon search starts right after the return
        // annotation, or the closing parenthesis when there is none.
        let colon_search_start = returns
            .as_ref()
            .map(|returns| returns.range().end())
            .unwrap_or_else(|| parameters.range().end());
        let args = self.arguments(parameters, true)?;
        self.parameter_list_opens.borrow_mut().insert(parameters.range().start().to_u32());
        let body = self.body(body)?;
        let returns = match returns {
            Some(returns) => self.expr(returns)?,
            None => self.none_obj(),
        };
        let type_comment = self.none_obj();
        let type_params = self.type_params(type_params)?;
        let start = match decorators.last() {
            Some(decorator) => {
                let keyword = if is_async { "async" } else { "def" };
                self.definition_keyword_start(decorator.range().end(), keyword)?
            }
            None => range.start(),
        };
        let node = self.make(
            class_name,
            vec![name, args, body, decorator_list, returns, type_comment, type_params],
            Some(TextRange::new(start, range.end())),
        )?;
        // A `# type:` comment after the signature colon (or on the line before
        // the indented block) attaches to the definition.
        if let Some(colon_offset) = self.skip_to_char(colon_search_start, b':') {
            self.colon_owners.borrow_mut().insert(
                colon_offset,
                ColonOwner {
                    kind: ColonOwnerKind::Def,
                    node: node.clone_ref(self.py),
                },
            );
        }
        Ok(node)
    }

    /// Register the block-introducing colon of a `for`/`with` statement: the
    /// first code byte after the header, when it is a colon.
    fn register_block_colon(&self, kind: ColonOwnerKind, header_end: TextSize, node: &PyObject) {
        if let Some(colon_offset) = self.skip_to_char(header_end, b':') {
            self.colon_owners.borrow_mut().insert(
                colon_offset,
                ColonOwner {
                    kind,
                    node: node.clone_ref(self.py),
                },
            );
        }
    }

    /// Skip whitespace and backslash-newline continuations from an offset and
    /// return the offset when the byte there is `expected`.
    fn skip_to_char(&self, from: TextSize, expected: u8) -> Option<u32> {
        let bytes = self.source.as_bytes();
        let mut index = from.to_usize();
        while index < bytes.len() {
            let byte = bytes[index];
            if matches!(byte, b' ' | b'\t' | b'\r' | b'\n' | b'\x0c' | b'\\') {
                index += 1;
                continue;
            }
            return (byte == expected).then_some(index as u32);
        }
        None
    }

    /// Find the `def`/`async`/`class` keyword offset for a definition that has
    /// decorators: the first non-blank, non-comment line after the last
    /// decorator starts with the keyword (CPython uses that token's position).
    fn definition_keyword_start(&self, after: TextSize, keyword: &str) -> PyResult<TextSize> {
        let after = after.to_usize();
        let bytes = self.source.as_bytes();
        let mut index = after;
        while index < bytes.len() {
            // Skip to the end of the current line.
            while index < bytes.len() && bytes[index] != b'\n' {
                index += 1;
            }
            index += 1;
            // Skip leading whitespace.
            let mut cursor = index;
            while cursor < bytes.len() && (bytes[cursor] == b' ' || bytes[cursor] == b'\t' || bytes[cursor] == b'\x0c') {
                cursor += 1;
            }
            if cursor >= bytes.len() {
                break;
            }
            // Blank or comment-only lines cannot carry the keyword.
            if bytes[cursor] == b'\n' || bytes[cursor] == b'#' || bytes[cursor] == b'\r' {
                continue;
            }
            let rest = &self.source.as_bytes()[cursor..];
            let starts_with = |word: &str| {
                rest.len() >= word.len()
                    && &rest[..word.len()] == word.as_bytes()
                    && rest
                        .get(word.len())
                        .is_some_and(|byte| byte.is_ascii_whitespace() || *byte == b'(')
            };
            if starts_with(keyword) {
                return Ok(TextSize::new(cursor as u32));
            }
        }
        self.unsupported("definition keyword after decorators not found")
    }

    fn if_statement(&self, stmt: &rast::StmtIf) -> PyResult<PyObject> {
        let test = self.expr(&stmt.test)?;
        let body = self.body(&stmt.body)?;
        let orelse = self.if_chain(&stmt.elif_else_clauses, stmt.range().end())?;
        self.make("If", vec![test, body, orelse], Some(stmt.range()))
    }

    /// Convert ruff's `elif_else_clauses` into CPython's nested If statements.
    ///
    /// CPython's chain rule: every If node in the chain starts at its
    /// `if`/`elif` keyword and ends at the end of the whole chain, and the
    /// `else` block becomes the `orelse` of the preceding If. The returned
    /// value is always the `orelse` list of the preceding If.
    fn if_chain(&self, clauses: &[rast::ElifElseClause], chain_end: TextSize) -> PyResult<PyObject> {
        if clauses.is_empty() {
            return self.py_list(vec![]);
        }
        let first = &clauses[0];
        let Some(test) = &first.test else {
            // A leading else clause attaches directly as orelse.
            return self.body(&first.body);
        };
        let body = self.body(&first.body)?;
        let orelse = if clauses.len() > 1 {
            let next = &clauses[1];
            if next.test.is_some() {
                self.if_chain(&clauses[1..], chain_end)?
            } else {
                self.body(&next.body)?
            }
        } else {
            self.py_list(vec![])?
        };
        let nested_if = self.make(
            "If",
            vec![self.expr(test)?, body, orelse],
            Some(TextRange::new(first.range().start(), chain_end)),
        )?;
        self.register_positioned_end(&nested_if, chain_end);
        self.py_list(vec![nested_if])
    }

    /// Register a converted node by its end offset for the type-comment end
    /// extension (handlers and nested `elif` chain nodes are not statements,
    /// but they end where their last statement ends).
    fn register_positioned_end(&self, node: &PyObject, end: TextSize) {
        self.stmt_ends
            .borrow_mut()
            .entry(end.to_u32())
            .or_default()
            .push(node.clone_ref(self.py));
    }

    // -- expressions --------------------------------------------------------

    pub fn expr(&self, expression: &rast::Expr) -> PyResult<PyObject> {
        match expression {
            rast::Expr::Name(expr) => {
                let id = self.str_obj(expr.id.as_str());
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("Name", vec![id, ctx], Some(expr.range()))
            }
            rast::Expr::Attribute(expr) => {
                let value = self.expr(&expr.value)?;
                let attr = self.str_obj(expr.attr.as_str());
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("Attribute", vec![value, attr, ctx], Some(expr.range()))
            }
            rast::Expr::Call(expr) => {
                let func = self.expr(&expr.func)?;
                let arguments_range = expr.arguments.range();
                let args = expr
                    .arguments
                    .args
                    .iter()
                    .map(|argument| self.call_argument(argument, arguments_range))
                    .collect::<PyResult<Vec<_>>>()?;
                let args = self.py_list(args)?;
                let keywords = expr
                    .arguments
                    .keywords
                    .iter()
                    .map(|keyword| self.keyword(keyword))
                    .collect::<PyResult<Vec<_>>>()?;
                let keywords = self.py_list(keywords)?;
                let range = TextRange::new(expr.range_start, expr.arguments.range().end());
                self.make("Call", vec![func, args, keywords], Some(range))
            }
            rast::Expr::NumberLiteral(expr) => self.number_constant(&expr.value, expr.range()),
            rast::Expr::StringLiteral(expr) => self.string_constant(expr),
            rast::Expr::BytesLiteral(expr) => {
                let mut value: Vec<u8> = vec![];
                for part in expr.value.iter() {
                    value.extend_from_slice(&part.value);
                }
                let value = self.bytes_obj(&value);
                self.make("Constant", vec![value, self.none_obj()], Some(expr.range()))
            }
            rast::Expr::BooleanLiteral(expr) => {
                let value = self.bool_obj(expr.value);
                self.make("Constant", vec![value, self.none_obj()], Some(expr.range()))
            }
            rast::Expr::NoneLiteral(expr) => {
                let value = self.none_obj();
                self.make("Constant", vec![value, self.none_obj()], Some(expr.range()))
            }
            rast::Expr::EllipsisLiteral(expr) => {
                let value = self.py.Ellipsis();
                self.make("Constant", vec![value, self.none_obj()], Some(expr.range()))
            }
            rast::Expr::FString(expr) => self.joined_str(expr),
            rast::Expr::BinOp(expr) => {
                let left = self.expr(&expr.left)?;
                let op = self.operator(&expr.op)?;
                let right = self.expr(&expr.right)?;
                self.make("BinOp", vec![left, op, right], Some(expr.range()))
            }
            rast::Expr::UnaryOp(expr) => {
                let op = self.unary_operator(&expr.op)?;
                let operand = self.expr(&expr.operand)?;
                self.make("UnaryOp", vec![op, operand], Some(expr.range()))
            }
            rast::Expr::BoolOp(expr) => {
                let op = self.bool_operator(&expr.op)?;
                let values = expr.values.iter().map(|value| self.expr(value)).collect::<PyResult<Vec<_>>>()?;
                let values = self.py_list(values)?;
                self.make("BoolOp", vec![op, values], Some(expr.range()))
            }
            rast::Expr::Compare(expr) => {
                let left = self.expr(&expr.operands[0])?;
                let ops = expr.ops.iter().map(|op| self.compare_operator(op)).collect::<PyResult<Vec<_>>>()?;
                let ops = self.py_list(ops)?;
                let comparators =
                    expr.operands[1..].iter().map(|comparator| self.expr(comparator)).collect::<PyResult<Vec<_>>>()?;
                let comparators = self.py_list(comparators)?;
                self.make("Compare", vec![left, ops, comparators], Some(expr.range()))
            }
            rast::Expr::If(expr) => {
                let test = self.expr(&expr.test)?;
                let body = self.expr(&expr.body)?;
                let orelse = self.expr(&expr.orelse)?;
                self.make("IfExp", vec![test, body, orelse], Some(expr.range()))
            }
            rast::Expr::Lambda(expr) => {
                let args = match &expr.parameters {
                    Some(parameters) => self.arguments(parameters, false)?,
                    None => self.arguments(&rast::Parameters::default(), false)?,
                };
                let body = self.expr(&expr.body)?;
                self.make("Lambda", vec![args, body], Some(expr.range()))
            }
            rast::Expr::List(expr) => {
                let elts = expr.elts.iter().map(|element| self.expr(element)).collect::<PyResult<Vec<_>>>()?;
                let elts = self.py_list(elts)?;
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("List", vec![elts, ctx], Some(expr.range()))
            }
            rast::Expr::Tuple(expr) => {
                let elts = expr.elts.iter().map(|element| self.expr(element)).collect::<PyResult<Vec<_>>>()?;
                let elts = self.py_list(elts)?;
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("Tuple", vec![elts, ctx], Some(expr.range()))
            }
            rast::Expr::Dict(expr) => {
                let mut keys: Vec<PyObject> = vec![];
                let mut values: Vec<PyObject> = vec![];
                for item in &expr.items {
                    match &item.key {
                        Some(key) => keys.push(self.expr(key)?),
                        None => keys.push(self.none_obj()),
                    }
                    values.push(self.expr(&item.value)?);
                }
                let keys = self.py_list(keys)?;
                let values = self.py_list(values)?;
                self.make("Dict", vec![keys, values], Some(expr.range()))
            }
            rast::Expr::Set(expr) => {
                let elts = expr.elts.iter().map(|element| self.expr(element)).collect::<PyResult<Vec<_>>>()?;
                let elts = self.py_list(elts)?;
                self.make("Set", vec![elts], Some(expr.range()))
            }
            rast::Expr::ListComp(expr) => {
                let elt = self.expr(&expr.elt)?;
                let generators = self.comprehensions(&expr.generators)?;
                self.make("ListComp", vec![elt, generators], Some(expr.range()))
            }
            rast::Expr::SetComp(expr) => {
                let elt = self.expr(&expr.elt)?;
                let generators = self.comprehensions(&expr.generators)?;
                self.make("SetComp", vec![elt, generators], Some(expr.range()))
            }
            rast::Expr::DictComp(expr) => {
                let key = match &expr.key {
                    Some(key) => self.expr(key)?,
                    None => self.none_obj(),
                };
                let value = self.expr(&expr.value)?;
                let generators = self.comprehensions(&expr.generators)?;
                self.make("DictComp", vec![key, value, generators], Some(expr.range()))
            }
            rast::Expr::Generator(expr) => self.generator_expr(expr, expr.range()),
            rast::Expr::Subscript(expr) => {
                let value = self.expr(&expr.value)?;
                let slice = self.expr(&expr.slice)?;
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("Subscript", vec![value, slice, ctx], Some(expr.range()))
            }
            rast::Expr::Slice(expr) => {
                let lower = self.optional_expr(&expr.lower)?;
                let upper = self.optional_expr(&expr.upper)?;
                let step = self.optional_expr(&expr.step)?;
                self.make("Slice", vec![lower, upper, step], Some(expr.range()))
            }
            rast::Expr::Named(expr) => {
                let target = self.expr(&expr.target)?;
                let value = self.expr(&expr.value)?;
                self.make("NamedExpr", vec![target, value], Some(expr.range()))
            }
            rast::Expr::Starred(expr) => {
                let value = self.expr(&expr.value)?;
                let ctx = self.expr_context(&expr.ctx)?;
                self.make("Starred", vec![value, ctx], Some(expr.range()))
            }
            rast::Expr::Yield(expr) => {
                let value = self.optional_expr(&expr.value)?;
                self.make("Yield", vec![value], Some(expr.range()))
            }
            rast::Expr::YieldFrom(expr) => {
                let value = self.expr(&expr.value)?;
                self.make("YieldFrom", vec![value], Some(expr.range()))
            }
            rast::Expr::Await(expr) => {
                let value = self.expr(&expr.value)?;
                self.make("Await", vec![value], Some(expr.range()))
            }
            rast::Expr::TString(expr) => self.template_str(expr),
            rast::Expr::IpyEscapeCommand(_) => self.unsupported("IPython escape expression"),
        }
    }

    /// A call argument needs the enclosing argument-list span: an
    /// unparenthesized generator expression takes CPython's range of the
    /// whole `(...)` argument list.
    fn call_argument(&self, argument: &rast::Expr, arguments_range: TextRange) -> PyResult<PyObject> {
        match argument {
            rast::Expr::Generator(generator) if !generator.parenthesized => {
                self.generator_expr(generator, arguments_range)
            }
            _ => self.expr(argument),
        }
    }

    fn generator_expr(&self, expr: &rast::ExprGenerator, range: TextRange) -> PyResult<PyObject> {
        let elt = self.expr(&expr.elt)?;
        let generators = self.comprehensions(&expr.generators)?;
        self.make("GeneratorExp", vec![elt, generators], Some(range))
    }

    fn optional_expr(&self, expression: &Option<Box<rast::Expr>>) -> PyResult<PyObject> {
        match expression {
            Some(expression) => self.expr(expression),
            None => Ok(self.none_obj()),
        }
    }

    /// CPython materialises `type_params` as an empty list when a definition
    /// has no type parameters (`ast.dump` suppresses empty lists).
    fn type_params(&self, type_params: &Option<Box<rast::TypeParams>>) -> PyResult<PyObject> {
        match type_params {
            Some(type_params) => {
                let converted = type_params
                    .type_params
                    .iter()
                    .map(|type_param| self.type_param(type_param))
                    .collect::<PyResult<Vec<_>>>()?;
                self.py_list(converted)
            }
            None => self.py_list(vec![]),
        }
    }

    fn type_param(&self, type_param: &rast::TypeParam) -> PyResult<PyObject> {
        let name = self.str_obj(type_param.name().as_str());
        match type_param {
            rast::TypeParam::TypeVar(param) => {
                let bound = self.optional_expr(&param.bound)?;
                let default = self.optional_expr(&param.default)?;
                self.make("TypeVar", vec![name, bound, default], Some(param.range()))
            }
            rast::TypeParam::TypeVarTuple(param) => {
                let default = self.optional_expr(&param.default)?;
                self.make("TypeVarTuple", vec![name, default], Some(param.range()))
            }
            rast::TypeParam::ParamSpec(param) => {
                let default = self.optional_expr(&param.default)?;
                self.make("ParamSpec", vec![name, default], Some(param.range()))
            }
        }
    }

    // -- f-strings ----------------------------------------------------------

    /// Materialise ruff's `ExprFString` as a CPython `JoinedStr`.
    fn joined_str(&self, expr: &rast::ExprFString) -> PyResult<PyObject> {
        let mut raw: Vec<RawValue> = vec![];
        for part in expr.value.iter() {
            match part {
                rast::FStringPartRef::Literal(literal) => {
                    let kind = literal_kind(literal.flags.prefix());
                    raw.push(RawValue::Constant {
                        text: literal.value.to_string(),
                        range: literal.range(),
                        kind,
                    });
                }
                rast::FStringPartRef::FString(fstring) => {
                    self.append_fstring_elements(&fstring.elements, false, &mut raw)?;
                }
            }
        }
        let values = self.raw_values_to_list(raw)?;
        self.make("JoinedStr", vec![values], Some(expr.range()))
    }

    fn append_fstring_elements(
        &self,
        elements: &rast::InterpolatedStringElements,
        template: bool,
        raw: &mut Vec<RawValue>,
    ) -> PyResult<()> {
        for element in elements.iter() {
            match element {
                rast::InterpolatedStringElement::Literal(literal) => {
                    raw.push(RawValue::Constant {
                        text: literal.value.to_string(),
                        range: literal.range(),
                        kind: None,
                    });
                }
                rast::InterpolatedStringElement::Interpolation(interpolation) => {
                    raw.extend(self.formatted_values(interpolation, template)?);
                }
            }
        }
        Ok(())
    }

    /// Convert ruff's `InterpolatedElement` into the values CPython emits for
    /// it: an optional debug-text `Constant` followed by a `FormattedValue` —
    /// or, inside a t-string (PEP 750), an `Interpolation` node that also
    /// carries the verbatim source between the braces.
    fn formatted_values(
        &self,
        interpolation: &rast::InterpolatedElement,
        template: bool,
    ) -> PyResult<Vec<RawValue>> {
        let mut values: Vec<RawValue> = vec![];
        if let Some(debug_text) = &interpolation.debug_text {
            // CPython emits the debug text as a leading Constant spanning from
            // just inside `{` to just before the conversion/spec/`}`.
            let start = interpolation.range().start().to_u32() + 1;
            let end = start + debug_text.as_str().len() as u32;
            values.push(RawValue::Constant {
                text: debug_text.as_str().to_string(),
                range: TextRange::new(TextSize::new(start), TextSize::new(end)),
                kind: None,
            });
        }
        let value = self.expr(&interpolation.expression)?;
        // Debug f-strings (`f"{b=}"`) imply a `!r` conversion in CPython
        // unless a format specification is present (`f"{b=:{w}}"`).
        let conversion = if interpolation.debug_text.is_some()
            && interpolation.format_spec.is_none()
            && interpolation.conversion == rast::ConversionFlag::None
        {
            i64::from(rast::ConversionFlag::Repr as i32)
        } else {
            i64::from(interpolation.conversion as i32)
        };
        let conversion = self.signed_int_obj(conversion)?;
        let format_spec = match &interpolation.format_spec {
            Some(spec) => self.format_spec(spec)?,
            None => self.none_obj(),
        };
        let formatted = if template {
            let str_text = self.interpolation_source_text(interpolation)?;
            let str_text = self.str_obj(&str_text);
            self.make(
                "Interpolation",
                vec![value, str_text, conversion, format_spec],
                Some(interpolation.range()),
            )?
        } else {
            self.make(
                "FormattedValue",
                vec![value, conversion, format_spec],
                Some(interpolation.range()),
            )?
        };
        values.push(RawValue::Formatted(formatted));
        Ok(values)
    }

    /// The verbatim source between the braces of an interpolation, as CPython
    /// keeps it in the t-string `Interpolation.str` field.
    fn interpolation_source_text(&self, interpolation: &rast::InterpolatedElement) -> PyResult<String> {
        let context = self.tokens.borrow();
        let Some(context) = context.as_ref() else {
            return self.unsupported("t-string interpolation without token context");
        };
        match context.interpolation_str(interpolation.range().start().to_u32()) {
            Some(text) => Ok(text.to_string()),
            None => self.unsupported("t-string interpolation source text not found"),
        }
    }

    /// Materialise ruff's `ExprTString` as a CPython `TemplateStr` (PEP 750).
    fn template_str(&self, expr: &rast::ExprTString) -> PyResult<PyObject> {
        let mut raw: Vec<RawValue> = vec![];
        for part in expr.value.iter() {
            self.append_fstring_elements(&part.elements, true, &mut raw)?;
        }
        let values = self.raw_values_to_list(raw)?;
        self.make("TemplateStr", vec![values], Some(expr.range()))
    }

    /// Materialise a nested format specification as a `JoinedStr`.
    ///
    /// CPython's specification `JoinedStr` starts at the `:` that opens the
    /// spec, so the range starts one byte before ruff's spec range.
    fn format_spec(&self, spec: &rast::InterpolatedStringFormatSpec) -> PyResult<PyObject> {
        let mut raw: Vec<RawValue> = vec![];
        for element in spec.elements.iter() {
            match element {
                rast::InterpolatedStringElement::Literal(literal) => {
                    raw.push(RawValue::Constant {
                        text: literal.value.to_string(),
                        range: literal.range(),
                        kind: None,
                    });
                }
                rast::InterpolatedStringElement::Interpolation(interpolation) => {
                    raw.extend(self.formatted_values(interpolation, false)?);
                }
            }
        }
        let values = self.raw_values_to_list(raw)?;
        let start = spec.range().start().to_u32().saturating_sub(1);
        let range = TextRange::new(TextSize::new(start), spec.range().end());
        self.make("JoinedStr", vec![values], Some(range))
    }
    fn raw_values_to_list(&self, raw: Vec<RawValue>) -> PyResult<PyObject> {
        let mut values: Vec<PyObject> = vec![];
        let mut index = 0;
        while index < raw.len() {
            match &raw[index] {
                RawValue::Formatted(node) => {
                    values.push(node.clone_ref(self.py));
                    index += 1;
                }
                RawValue::Constant { .. } => {
                    // Merge the run of adjacent constants the way CPython does
                    // for implicitly concatenated literal chunks.
                    let mut end = index;
                    while end + 1 < raw.len() && matches!(raw[end + 1], RawValue::Constant { .. }) {
                        end += 1;
                    }
                    let mut text = String::new();
                    let mut kind: Option<&'static str> = None;
                    let mut range = raw[index].constant_range();
                    for element in &raw[index..=end] {
                        let (element_text, element_range, element_kind) = match element {
                            RawValue::Constant { text, range, kind } => (text, *range, *kind),
                            RawValue::Formatted(_) => unreachable!(),
                        };
                        text.push_str(element_text);
                        if kind.is_none() {
                            kind = element_kind;
                        }
                        range = TextRange::new(range.start(), element_range.end());
                    }
                    let value = self.str_obj(&text);
                    let kind_obj = match kind {
                        Some(kind) => self.str_obj(kind),
                        None => self.none_obj(),
                    };
                    values.push(self.make("Constant", vec![value, kind_obj], Some(range))?);
                    index = end + 1;
                }
            }
        }
        self.py_list(values)
    }

    // -- helpers ------------------------------------------------------------

    fn expr_context(&self, ctx: &rast::ExprContext) -> PyResult<PyObject> {
        let class_name = match ctx {
            rast::ExprContext::Load => "Load",
            rast::ExprContext::Store => "Store",
            rast::ExprContext::Del => "Del",
            rast::ExprContext::Invalid => return self.unsupported("invalid expression context"),
        };
        self.cls(class_name)?.call0().map(|node| node.unbind())
    }

    fn operator(&self, op: &rast::Operator) -> PyResult<PyObject> {
        let class_name = match op {
            rast::Operator::Add => "Add",
            rast::Operator::Sub => "Sub",
            rast::Operator::Mult => "Mult",
            rast::Operator::MatMult => "MatMult",
            rast::Operator::Div => "Div",
            rast::Operator::Mod => "Mod",
            rast::Operator::Pow => "Pow",
            rast::Operator::LShift => "LShift",
            rast::Operator::RShift => "RShift",
            rast::Operator::BitOr => "BitOr",
            rast::Operator::BitXor => "BitXor",
            rast::Operator::BitAnd => "BitAnd",
            rast::Operator::FloorDiv => "FloorDiv",
        };
        self.cls(class_name)?.call0().map(|node| node.unbind())
    }

    fn unary_operator(&self, op: &rast::UnaryOp) -> PyResult<PyObject> {
        let class_name = match op {
            rast::UnaryOp::Invert => "Invert",
            rast::UnaryOp::Not => "Not",
            rast::UnaryOp::UAdd => "UAdd",
            rast::UnaryOp::USub => "USub",
        };
        self.cls(class_name)?.call0().map(|node| node.unbind())
    }

    fn bool_operator(&self, op: &rast::BoolOp) -> PyResult<PyObject> {
        let class_name = match op {
            rast::BoolOp::And => "And",
            rast::BoolOp::Or => "Or",
        };
        self.cls(class_name)?.call0().map(|node| node.unbind())
    }

    fn compare_operator(&self, op: &rast::CmpOp) -> PyResult<PyObject> {
        let class_name = match op {
            rast::CmpOp::Eq => "Eq",
            rast::CmpOp::NotEq => "NotEq",
            rast::CmpOp::Lt => "Lt",
            rast::CmpOp::LtE => "LtE",
            rast::CmpOp::Gt => "Gt",
            rast::CmpOp::GtE => "GtE",
            rast::CmpOp::Is => "Is",
            rast::CmpOp::IsNot => "IsNot",
            rast::CmpOp::In => "In",
            rast::CmpOp::NotIn => "NotIn",
        };
        self.cls(class_name)?.call0().map(|node| node.unbind())
    }

    fn alias(&self, alias: &rast::Alias) -> PyResult<PyObject> {
        let name = self.str_obj(alias.name.as_str());
        let asname = match &alias.asname {
            Some(asname) => self.str_obj(asname.as_str()),
            None => self.none_obj(),
        };
        self.make("alias", vec![name, asname], Some(alias.range()))
    }

    fn keyword(&self, keyword: &rast::Keyword) -> PyResult<PyObject> {
        let arg = match &keyword.arg {
            Some(arg) => self.str_obj(arg.as_str()),
            None => self.none_obj(),
        };
        let value = self.expr(&keyword.value)?;
        self.make("keyword", vec![arg, value], Some(keyword.range()))
    }

    fn with_item(&self, item: &rast::WithItem) -> PyResult<PyObject> {
        let context_expr = self.expr(&item.context_expr)?;
        let optional_vars = self.optional_expr(&item.optional_vars)?;
        self.make_nopositions("withitem", vec![context_expr, optional_vars])
    }

    fn except_handler(&self, handler: &rast::ExceptHandlerExceptHandler) -> PyResult<PyObject> {
        let type_ = self.optional_expr(&handler.type_)?;
        let name = match &handler.name {
            Some(name) => self.str_obj(name.as_str()),
            None => self.none_obj(),
        };
        let body = self.body(&handler.body)?;
        let node = self.make("ExceptHandler", vec![type_, name, body], Some(handler.range()))?;
        self.register_positioned_end(&node, handler.range().end());
        Ok(node)
    }

    fn comprehensions(&self, generators: &[rast::Comprehension]) -> PyResult<PyObject> {
        let converted = generators.iter().map(|generator| self.comprehension(generator)).collect::<PyResult<Vec<_>>>()?;
        self.py_list(converted)
    }

    fn comprehension(&self, generator: &rast::Comprehension) -> PyResult<PyObject> {
        let target = self.expr(&generator.target)?;
        let iter = self.expr(&generator.iter)?;
        let ifs = generator.ifs.iter().map(|condition| self.expr(condition)).collect::<PyResult<Vec<_>>>()?;
        let ifs = self.py_list(ifs)?;
        let is_async = self.int_obj(u64::from(generator.is_async))?;
        self.make_nopositions("comprehension", vec![target, iter, ifs, is_async])
    }

    /// Convert ruff's `MatchCase` into a CPython `match_case` helper node.
    fn match_case(&self, case: &rast::MatchCase) -> PyResult<PyObject> {
        let pattern = self.pattern(&case.pattern)?;
        let guard = self.optional_expr(&case.guard)?;
        let body = self.body(&case.body)?;
        self.make_nopositions("match_case", vec![pattern, guard, body])
    }

    fn pattern(&self, pattern: &rast::Pattern) -> PyResult<PyObject> {
        match pattern {
            rast::Pattern::MatchValue(pattern) => {
                let value = self.expr(&pattern.value)?;
                self.make("MatchValue", vec![value], Some(pattern.range()))
            }
            rast::Pattern::MatchSingleton(pattern) => {
                let value = match pattern.value {
                    rast::Singleton::None => self.none_obj(),
                    rast::Singleton::True => self.bool_obj(true),
                    rast::Singleton::False => self.bool_obj(false),
                };
                self.make("MatchSingleton", vec![value], Some(pattern.range()))
            }
            rast::Pattern::MatchSequence(pattern) => {
                let patterns = pattern
                    .patterns
                    .iter()
                    .map(|element| self.pattern(element))
                    .collect::<PyResult<Vec<_>>>()?;
                let patterns = self.py_list(patterns)?;
                self.make("MatchSequence", vec![patterns], Some(pattern.range()))
            }
            rast::Pattern::MatchMapping(pattern) => {
                let keys = pattern.keys.iter().map(|key| self.expr(key)).collect::<PyResult<Vec<_>>>()?;
                let keys = self.py_list(keys)?;
                let patterns = pattern
                    .patterns
                    .iter()
                    .map(|element| self.pattern(element))
                    .collect::<PyResult<Vec<_>>>()?;
                let patterns = self.py_list(patterns)?;
                let rest = match &pattern.rest {
                    Some(rest) => self.str_obj(rest.as_str()),
                    None => self.none_obj(),
                };
                self.make("MatchMapping", vec![keys, patterns, rest], Some(pattern.range()))
            }
            rast::Pattern::MatchClass(pattern) => {
                let cls = self.expr(&pattern.cls)?;
                let patterns = pattern
                    .arguments
                    .patterns
                    .iter()
                    .map(|element| self.pattern(element))
                    .collect::<PyResult<Vec<_>>>()?;
                let patterns = self.py_list(patterns)?;
                let kwd_attrs = pattern
                    .arguments
                    .keywords
                    .iter()
                    .map(|keyword| self.str_obj(keyword.attr.as_str()))
                    .collect::<Vec<_>>();
                let kwd_attrs = self.py_list(kwd_attrs)?;
                let kwd_patterns = pattern
                    .arguments
                    .keywords
                    .iter()
                    .map(|keyword| self.pattern(&keyword.pattern))
                    .collect::<PyResult<Vec<_>>>()?;
                let kwd_patterns = self.py_list(kwd_patterns)?;
                self.make(
                    "MatchClass",
                    vec![cls, patterns, kwd_attrs, kwd_patterns],
                    Some(pattern.range()),
                )
            }
            rast::Pattern::MatchStar(pattern) => {
                let name = match &pattern.name {
                    Some(name) => self.str_obj(name.as_str()),
                    None => self.none_obj(),
                };
                self.make("MatchStar", vec![name], Some(pattern.range()))
            }
            rast::Pattern::MatchAs(pattern) => {
                let inner = self.optional_pattern(&pattern.pattern)?;
                let name = match &pattern.name {
                    Some(name) => self.str_obj(name.as_str()),
                    None => self.none_obj(),
                };
                self.make("MatchAs", vec![inner, name], Some(pattern.range()))
            }
            rast::Pattern::MatchOr(pattern) => {
                let patterns = pattern
                    .patterns
                    .iter()
                    .map(|element| self.pattern(element))
                    .collect::<PyResult<Vec<_>>>()?;
                let patterns = self.py_list(patterns)?;
                self.make("MatchOr", vec![patterns], Some(pattern.range()))
            }
        }
    }

    fn optional_pattern(&self, pattern: &Option<Box<rast::Pattern>>) -> PyResult<PyObject> {
        match pattern {
            Some(pattern) => self.pattern(pattern),
            None => Ok(self.none_obj()),
        }
    }

    /// Convert ruff's `Parameters` into a CPython `arguments` node.
    ///
    /// `register` marks function-definition parameters (not lambda ones): a
    /// `# type:` comment inside a definition's parameter list attaches to the
    /// parameter it follows, so those `arg` nodes are keyed by their end
    /// offset for the type-comment pass.
    fn arguments(&self, parameters: &rast::Parameters, register: bool) -> PyResult<PyObject> {
        let posonlyargs = self.arg_list(&parameters.posonlyargs, register)?;
        let args = self.arg_list(&parameters.args, register)?;
        let vararg = match &parameters.vararg {
            Some(parameter) => self.arg_node(parameter, true, register, parameter.range().end())?,
            None => self.none_obj(),
        };
        let kwonlyargs = parameters
            .kwonlyargs
            .iter()
            .map(|parameter| self.arg_node(&parameter.parameter, false, register, parameter.range().end()))
            .collect::<PyResult<Vec<_>>>()?;
        let kwonlyargs = self.py_list(kwonlyargs)?;
        let kw_defaults = parameters
            .kwonlyargs
            .iter()
            .map(|parameter| self.optional_expr(&parameter.default))
            .collect::<PyResult<Vec<_>>>()?;
        let kw_defaults = self.py_list(kw_defaults)?;
        let kwarg = match &parameters.kwarg {
            Some(parameter) => self.arg_node(parameter, true, register, parameter.range().end())?,
            None => self.none_obj(),
        };
        let defaults = parameters
            .posonlyargs
            .iter()
            .chain(&parameters.args)
            .filter_map(|parameter| parameter.default.as_deref())
            .map(|default| self.expr(default))
            .collect::<PyResult<Vec<_>>>()?;
        let defaults = self.py_list(defaults)?;
        self.make_nopositions(
            "arguments",
            vec![posonlyargs, args, vararg, kwonlyargs, kw_defaults, kwarg, defaults],
        )
    }

    fn arg_list(&self, parameters: &[rast::ParameterWithDefault], register: bool) -> PyResult<PyObject> {
        let converted = parameters
            .iter()
            .map(|parameter| self.arg_node(&parameter.parameter, false, register, parameter.range().end()))
            .collect::<PyResult<Vec<_>>>()?;
        self.py_list(converted)
    }

    /// `registration_end` is the end of the parameter's own syntax (including
    /// a default value, excluding the following comma): a `# type:` comment
    /// inside the parameter list must directly follow that offset — after the
    /// parameter's own comma, or right before `)`.
    fn arg_node(
        &self,
        parameter: &rast::Parameter,
        variadic: bool,
        register: bool,
        registration_end: TextSize,
    ) -> PyResult<PyObject> {
        let arg = self.str_obj(parameter.name.as_str());
        let annotation = self.optional_expr(&parameter.annotation)?;
        let type_comment = self.none_obj();
        // Variadic parameters span `*name`/`**name` in ruff but CPython's arg
        // node starts at the name itself.
        let start = if variadic { parameter.name.range().start() } else { parameter.range().start() };
        let range = TextRange::new(start, parameter.range().end());
        let node = self.make("arg", vec![arg, annotation, type_comment], Some(range))?;
        if register {
            self.arg_ends
                .borrow_mut()
                .insert(registration_end.to_u32(), node.clone_ref(self.py));
        }
        Ok(node)
    }

    fn number_constant(&self, number: &rast::Number, range: TextRange) -> PyResult<PyObject> {
        let value = match number {
            rast::Number::Int(int) => match int.as_u64() {
                Some(value) => self.int_obj(value)?,
                None => {
                    // Big integers keep their source token; Python's int()
                    // handles radix prefixes and underscores.
                    let token = int.to_string();
                    let int_type = self.builtins.getattr("int")?.into_any();
                    int_type.call((self.str_obj(&token), self.int_obj(0)?), None)?.unbind()
                }
            },
            rast::Number::Float(value) => self.float_obj(*value)?,
            rast::Number::Complex { real, imag } => {
                let complex_type = self.builtins.getattr("complex")?.into_any();
                complex_type.call((self.float_obj(*real)?, self.float_obj(*imag)?), None)?.unbind()
            }
        };
        self.make("Constant", vec![value, self.none_obj()], Some(range))
    }

    /// Materialise a plain (non-f) string literal as a `Constant`.
    fn string_constant(&self, expr: &rast::ExprStringLiteral) -> PyResult<PyObject> {
        let kind = literal_kind(expr.value.first_literal_flags().prefix());
        let value = self.str_obj(expr.value.to_str());
        let kind_obj = match kind {
            Some(kind) => self.str_obj(kind),
            None => self.none_obj(),
        };
        self.make("Constant", vec![value, kind_obj], Some(expr.range()))
    }
}

impl RawValue {
    fn constant_range(&self) -> TextRange {
        match self {
            RawValue::Constant { range, .. } => *range,
            RawValue::Formatted(_) => unreachable!(),
        }
    }
}

/// `kind='u'` for `u`-prefixed strings, `None` otherwise.
fn literal_kind(prefix: StringLiteralPrefix) -> Option<&'static str> {
    match prefix {
        StringLiteralPrefix::Unicode => Some("u"),
        _ => None,
    }
}

/// Build the byte offsets of every line start (line 1 starts at offset 0).
pub(crate) fn build_line_index(source: &str) -> Vec<u32> {
    let mut line_starts = vec![0_u32];
    for (index, byte) in source.bytes().enumerate() {
        if byte == b'\n' {
            line_starts.push(index as u32 + 1);
        }
    }
    line_starts
}
