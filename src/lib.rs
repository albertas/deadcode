//! Native helpers for deadcode, built with maturin into `deadcode._native`.
//!
//! Python imports this module as `deadcode._native`; the Python side
//! (`deadcode/_native_loader.py`) loads it once at import time and falls back
//! to the pure-Python implementation when the module is absent.
//!
//! Error contract (D7/D9):
//! - `ParseError` — the source is rejected as unparseable; the Python seam
//!   maps it into the unchanged parse-failure contract (fixed message +
//!   empty module).
//! - Any other error — "give up"; the Python seam falls back to `ast.parse`.
//!   This covers undeterminable encodings (the Python fallback reproduces
//!   CPython's behaviour) and converter bugs that were not caught by the
//!   parity suite.

mod convert;

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError};
use pyo3::prelude::*;
use ruff_python_ast::token::{Token, TokenKind};
use ruff_python_parser::{Mode, ParseOptions};
use ruff_text_size::{Ranged, TextRange, TextSize};

create_exception!(deadcode_native, ParseError, PyException);

/// Decode raw source bytes the way CPython does (D9): UTF-8/UTF-16/UTF-32
/// BOMs, then a PEP 263 `coding` cookie from the first two lines.
///
/// Returns the newline-normalized decoded text. Unsupported or
/// undeterminable encodings give up (the Python fallback takes over), while
/// hard decode failures on supported encodings are parse rejections
/// (the D7 failure path).
fn decode_source(source: &[u8]) -> PyResult<String> {
    // Strip the BOM, giving up on the UTF-16/UTF-32 encodings: CPython
    // supports them natively, so the Python fallback keeps behaviour.
    let bytes = match source {
        [0xEF, 0xBB, 0xBF, rest @ ..] => rest,
        [0xFF, 0xFE, ..] | [0xFE, 0xFF, ..] => return Err(give_up("unsupported UTF-16/UTF-32 BOM")),
        _ => source,
    };

    match detect_coding_cookie(bytes) {
        Some(encoding) => match normalize_encoding(&encoding) {
            Some("utf-8") => decode_utf8(bytes),
            Some("ascii") => decode_utf8(bytes),
            Some("latin-1") => Ok(decode_latin1(bytes)),
            Some(_) => Err(give_up(&format!("unsupported encoding {encoding}"))),
            None => Err(give_up(&format!("unknown encoding {encoding}"))),
        },
        None => decode_utf8(bytes),
    }
}

fn decode_utf8(bytes: &[u8]) -> PyResult<String> {
    std::str::from_utf8(bytes)
        .map(normalize_newlines)
        .map_err(|_| PyErr::new::<ParseError, _>("source is not valid UTF-8"))
}

/// Latin-1 is a lossless byte-to-character map, so decoding is trivial.
fn decode_latin1(bytes: &[u8]) -> String {
    normalize_newlines(&bytes.iter().map(|byte| *byte as char).collect::<String>())
}

fn normalize_newlines(text: &str) -> String {
    if !text.contains('\r') {
        return text.to_string();
    }
    let mut normalized = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(char) = chars.next() {
        if char == '\r' {
            if chars.peek() == Some(&'\n') {
                chars.next();
            }
            normalized.push('\n');
        } else {
            normalized.push(char);
        }
    }
    normalized
}

/// Give-up signal: the Python seam falls back to `ast.parse` on this error.
fn give_up(reason: &str) -> PyErr {
    PyErr::new::<PyRuntimeError, _>(format!("native parser gave up: {reason}"))
}

/// PEP 263 cookie detection: the first of the first two lines that is a
/// comment matching `^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)` wins.
fn detect_coding_cookie(bytes: &[u8]) -> Option<String> {
    for line in bytes.split(|byte| *byte == b'\n').take(2) {
        let mut index = 0;
        while index < line.len() && matches!(line[index], b' ' | b'\t' | 0x0C) {
            index += 1;
        }
        if index >= line.len() || line[index] != b'#' {
            continue;
        }
        let comment = &line[index + 1..];
        let mut position = 0;
        while position + 6 <= comment.len() {
            if &comment[position..position + 6] == b"coding" {
                let mut cursor = position + 6;
                if cursor >= comment.len() || (comment[cursor] != b':' && comment[cursor] != b'=') {
                    position += 6;
                    continue;
                }
                cursor += 1;
                while cursor < comment.len() && (comment[cursor] == b' ' || comment[cursor] == b'\t') {
                    cursor += 1;
                }
                let start = cursor;
                while cursor < comment.len() && is_encoding_char(comment[cursor]) {
                    cursor += 1;
                }
                if cursor > start {
                    return Some(String::from_utf8_lossy(&comment[start..cursor]).into_owned());
                }
            }
            position += 1;
        }
    }
    None
}

fn is_encoding_char(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'-' || byte == b'_' || byte == b'.'
}

/// Normalize a cookie encoding name to one of the handled codecs.
fn normalize_encoding(encoding: &str) -> Option<&'static str> {
    let normalized = encoding.to_ascii_lowercase().replace('_', "-");
    match normalized.as_str() {
        "utf-8" | "utf8" => Some("utf-8"),
        "ascii" | "us-ascii" => Some("ascii"),
        "iso-8859-1" | "latin-1" | "latin1" | "iso8859-1" => Some("latin-1"),
        _ => None,
    }
}

/// Parse a Python module from raw `source` bytes and return an
/// `ast.Module` tree built from real CPython `ast` objects.
///
/// With `type_comments`, `# type:` comments attach to their owning nodes and
/// `# type: ignore` comments populate `Module.type_ignores`, exactly like
/// CPython's `ast.parse(..., type_comments=True)` (D8).
#[pyfunction]
#[pyo3(signature = (source, filename, type_comments))]
fn parse_module(py: Python<'_>, source: &[u8], filename: &str, type_comments: bool) -> PyResult<Py<PyAny>> {
    let text = decode_source(source)?;
    let parsed = ruff_python_parser::parse_module(&text).map_err(|error| {
        PyErr::new::<ParseError, _>(format!("failed to parse {filename}: {error}"))
    })?;
    let token_context = if type_comments {
        convert::TokenContext::collect(&text, parsed.tokens())
    } else {
        convert::TokenContext::without_type_comments(&text, parsed.tokens())
    };
    let tree = convert::Converter::new(py, &text)?.module(parsed.syntax(), &token_context)?;
    drop(text);
    Ok(tree)
}

/// The Python-side name for a parse failure that must surface as
/// `SyntaxError`: the string-mode call sites keep their existing
/// `except SyntaxError` contracts, so the native rejection is translated on
/// the Python side (the module seam maps `ParseError` into its own failure
/// contract instead).
fn parse_rejection(filename: &str, reason: impl std::fmt::Display) -> PyErr {
    PyErr::new::<ParseError, _>(format!("failed to parse {filename}: {reason}"))
}

/// CPython rejects a leading byte-order mark in `str` sources with
/// "invalid non-printable character U+FEFF"; ruff's lexer skips it instead,
/// so the string modes must reject it up front.
fn reject_bom(source: &str, filename: &str) -> PyResult<()> {
    if source.starts_with('\u{FEFF}') {
        return Err(parse_rejection(filename, "invalid non-printable character U+FEFF"));
    }
    Ok(())
}

/// Parse a string as a single expression (`ast.parse(source, mode='eval')`).
#[pyfunction]
#[pyo3(signature = (source, filename))]
fn parse_expression(py: Python<'_>, source: &str, filename: &str) -> PyResult<Py<PyAny>> {
    reject_bom(source, filename)?;
    let parsed = ruff_python_parser::parse_expression(source)
        .map_err(|error| parse_rejection(filename, error))?;
    let token_context = convert::TokenContext::without_type_comments(source, parsed.tokens());
    let converter = convert::Converter::new(py, source)?;
    let tree = converter.expression(parsed.syntax(), &token_context)?;
    Ok(tree)
}

/// Parse a string as a sequence of statements (`ast.parse(source)`, the
/// `exec` mode). Returns the `ast.Module` tree, without the type-comment
/// layer (the call sites parse with CPython's default flags).
#[pyfunction]
#[pyo3(signature = (source, filename))]
fn parse_statement(py: Python<'_>, source: &str, filename: &str) -> PyResult<Py<PyAny>> {
    reject_bom(source, filename)?;
    let parsed = ruff_python_parser::parse_module(source)
        .map_err(|error| parse_rejection(filename, error))?;
    let token_context = convert::TokenContext::without_type_comments(source, parsed.tokens());
    let converter = convert::Converter::new(py, source)?;
    let tree = converter.module(parsed.syntax(), &token_context)?;
    Ok(tree)
}

/// Parse a function type comment (`ast.parse(source, mode='func_type')`):
/// the `(...)` argument list followed by `->` and the return type.
///
/// The grammar is scanned over the token stream; every argument type and the
/// return type are parsed as expressions at their absolute offsets, so the
/// child nodes carry the same positions CPython produces. Multi-line sources
/// give up and the Python fallback reproduces CPython exactly.
#[pyfunction]
#[pyo3(signature = (source, filename))]
fn parse_func_type(py: Python<'_>, source: &str, filename: &str) -> PyResult<Py<PyAny>> {
    reject_bom(source, filename)?;
    if source.contains(['\n', '\r']) {
        return Err(give_up("multi-line function type"));
    }
    // The token stream is needed even when the module-mode parse of the
    // fragment fails: the grammar is validated token by token below.
    let parsed = ruff_python_parser::parse_unchecked(source, ParseOptions::from(Mode::Module));
    let token_context = convert::TokenContext::without_type_comments(source, parsed.tokens());
    let converter = convert::Converter::new(py, source)?;
    converter.set_tokens(&token_context);
    let (argtypes, returns) = func_type_parts(&converter, source, parsed.tokens(), filename)?;
    let tree = converter.function_type(argtypes, returns)?;
    Ok(tree)
}

/// One element of the function type's argument list: an optional `*`/`**`
/// prefix and the token span of the type expression itself.
struct FuncTypeElement {
    star: Option<TokenKind>,
    start: TextSize,
    end: TextSize,
}

/// CPython's tokenizer indent measure over the whitespace before `offset`:
/// spaces count one, tabs advance to the next multiple of eight, and a form
/// feed resets the count to zero. The first token of an expression parse
/// must sit at indent zero, or CPython rejects with "unexpected indent".
fn indent_width(source: &str, offset: TextSize) -> u32 {
    let mut indent = 0_u32;
    for byte in &source.as_bytes()[..offset.to_usize()] {
        match byte {
            b' ' => indent += 1,
            b'\t' => indent = (indent / 8 + 1) * 8,
            0x0C => indent = 0,
            _ => {}
        }
    }
    indent
}

fn func_type_parts<'py>(
    converter: &convert::Converter<'py>,
    source: &str,
    tokens: &[Token],
    filename: &str,
) -> PyResult<(Vec<PyObject>, PyObject)> {
    let reject = |reason: &str| Err(parse_rejection(filename, reason));

    // CPython's tokenizer does not report comments, blank-line newlines, or
    // the indent/dedent markers to the parser; logical-line newlines end the
    // line.
    let code: Vec<&Token> = tokens
        .iter()
        .filter(|token| {
            !matches!(
                token.kind(),
                TokenKind::Comment
                    | TokenKind::NonLogicalNewline
                    | TokenKind::Indent
                    | TokenKind::Dedent
                    | TokenKind::EndOfFile
            )
        })
        .collect();

    // Leading blank lines are fine; the first code token opens the argument
    // list and must sit at column zero.
    let mut index = 0;
    while matches!(code.get(index), Some(token) if token.kind() == TokenKind::Newline) {
        index += 1;
    }
    let Some(&opening) = code.get(index) else {
        return reject("the source contains no code");
    };
    if opening.kind() != TokenKind::Lpar {
        return reject("the function type must start with '('");
    }
    if indent_width(source, opening.range().start()) > 0 {
        return reject("unexpected indent");
    }

    // Scan the argument list: top-level commas separate the type elements.
    let mut index = index + 1;
    let mut depth = 0_u32;
    let mut star: Option<TokenKind> = None;
    let mut element_start: Option<TextSize> = None;
    let mut element_end = opening.range().end();
    let mut elements: Vec<FuncTypeElement> = vec![];
    let mut closed = false;
    let mut after_comma = false;
    while let Some(&token) = code.get(index) {
        index += 1;
        let record = |element_start: &mut Option<TextSize>, element_end: &mut TextSize| {
            element_start.get_or_insert(token.range().start());
            *element_end = token.range().end();
        };
        match token.kind() {
            TokenKind::Comma if depth == 0 => {
                let Some(start) = element_start else {
                    return reject("an argument list entry is empty");
                };
                elements.push(FuncTypeElement { star, start, end: element_end });
                star = None;
                element_start = None;
                after_comma = true;
            }
            TokenKind::Rpar if depth == 0 => {
                if after_comma {
                    return reject("trailing comma in the argument list");
                }
                if let Some(start) = element_start {
                    elements.push(FuncTypeElement { star, start, end: element_end });
                } else if star.is_some() {
                    return reject("a starred argument has no type");
                }
                closed = true;
                break;
            }
            TokenKind::Rpar | TokenKind::Rsqb | TokenKind::Rbrace => {
                depth = depth.saturating_sub(1);
                record(&mut element_start, &mut element_end);
                after_comma = false;
            }
            TokenKind::Lpar | TokenKind::Lsqb | TokenKind::Lbrace => {
                depth += 1;
                record(&mut element_start, &mut element_end);
                after_comma = false;
            }
            TokenKind::Star | TokenKind::DoubleStar
                if depth == 0 && element_start.is_none() && star.is_none() =>
            {
                star = Some(token.kind());
                after_comma = false;
            }
            _ => {
                record(&mut element_start, &mut element_end);
                after_comma = false;
            }
        }
    }
    if !closed {
        return reject("the argument list is not closed");
    }

    // CPython's rule for the star prefixes: at most one `*` and one `**`,
    // `**` only in the last position, `*` in the last position or directly
    // before the final `**kwargs` element.
    let last = elements.len().saturating_sub(1);
    let stars: Vec<(usize, TokenKind)> = elements
        .iter()
        .enumerate()
        .filter_map(|(position, element)| element.star.map(|kind| (position, kind)))
        .collect();
    let single_stars = stars.iter().filter(|(_, kind)| *kind == TokenKind::Star).count();
    let double_stars = stars.iter().filter(|(_, kind)| *kind == TokenKind::DoubleStar).count();
    if single_stars > 1 || double_stars > 1 {
        return reject("too many star prefixes");
    }
    for (position, kind) in stars {
        let allowed = match kind {
            TokenKind::DoubleStar => position == last,
            TokenKind::Star => {
                position == last || (double_stars == 1 && position + 1 == last)
            }
            _ => false,
        };
        if !allowed {
            return reject("the star prefix is in a position CPython rejects");
        }
    }

    // Each argument type is an expression at its absolute offset.
    let mut argtypes: Vec<PyObject> = vec![];
    for element in &elements {
        let range = TextRange::new(element.start, element.end);
        let parsed = ruff_python_parser::parse_expression_range(source, range)
            .map_err(|error| parse_rejection(filename, error))?;
        argtypes.push(converter.expr(&parsed.syntax().body)?);
    }

    // `->` must follow the closing paren directly, and the return type
    // occupies the rest of the line (comments after it are not part of it).
    let Some(&arrow) = code.get(index) else {
        return reject("the return type is missing");
    };
    if arrow.kind() != TokenKind::Rarrow {
        return reject("expected '->' after the argument list");
    }
    // The return type is a single expression: a top-level comma (a bare
    // tuple) is CPython's "invalid syntax" — only bracketed tuples are
    // atoms.
    let mut index = index + 1;
    let mut depth = 0_u32;
    let mut return_start: Option<TextSize> = None;
    let mut return_end = arrow.range().end();
    while let Some(&token) = code.get(index) {
        index += 1;
        match token.kind() {
            TokenKind::Comma if depth == 0 => return reject("a bare tuple cannot be the return type"),
            TokenKind::Lpar | TokenKind::Lsqb | TokenKind::Lbrace => depth += 1,
            TokenKind::Rpar | TokenKind::Rsqb | TokenKind::Rbrace => depth = depth.saturating_sub(1),
            _ => {}
        }
        return_start.get_or_insert(token.range().start());
        return_end = token.range().end();
    }
    let Some(return_start) = return_start else {
        return reject("the return type is missing");
    };
    let parsed = ruff_python_parser::parse_expression_range(source, TextRange::new(return_start, return_end))
        .map_err(|error| parse_rejection(filename, error))?;
    let returns = converter.expr(&parsed.syntax().body)?;
    Ok((argtypes, returns))
}

#[pymodule(name = "_native")]
fn deadcode_native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("ParseError", py.get_type::<ParseError>())?;
    m.add_function(wrap_pyfunction!(parse_module, m)?)?;
    m.add_function(wrap_pyfunction!(parse_expression, m)?)?;
    m.add_function(wrap_pyfunction!(parse_statement, m)?)?;
    m.add_function(wrap_pyfunction!(parse_func_type, m)?)?;
    Ok(())
}
