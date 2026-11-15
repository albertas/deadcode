//! Rust extension module for the `deadcode` CLI: Python parsing plus native accelerators.
//!
//! Built with maturin into the private `deadcode._native` extension module
//! (`abi3-py310`). The pure-Python implementation in the `deadcode` package
//! stays the automatic fallback whenever this module is not installed.
//!
//! The module exposes the parser helpers from the Rust-parser work
//! (`parse_module`, `parse_expression`, `parse_statement`, `parse_func_type`
//! and `ParseError`) together with the accelerators from the native work
//! (`scan_comments`, `collect_module_exports` and `crate_version`).
//!
//! `scan_comments` is a byte-level tokenizer over file bytes that extracts the
//! COMMENT tokens and the `# noqa` suppression map in one pass. It replicates
//! the semantics of CPython 3.10's `tokenize.tokenize` for comment extraction
//! purposes, including the tokenisation-failure behaviour: when tokenisation
//! fails the comment list is empty and the `noqa` map falls back to raw-line
//! matching, exactly like `deadcode.visitor.noqa.parse_noqa(code, None)`. When
//! the encoding cannot be guaranteed (unsupported codec, invalid bytes) the
//! function returns `None` and the caller falls back to the Python scanner.

mod convert;

use std::collections::{HashMap, HashSet, VecDeque};

use pyo3::create_exception;
use pyo3::exceptions::{PyAttributeError, PyException, PyRuntimeError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyAnyMethods, PyList, PyModule, PyString, PyType};
use ruff_python_ast::token::{Token, TokenKind};
use ruff_python_parser::{Mode, ParseOptions};
use ruff_text_size::{Ranged, TextRange, TextSize};

create_exception!(deadcode_native, ParseError, PyException);

/// Returns the version of the `deadcode` Rust crate. A trivially testable
/// probe that proves the extension module loads and dispatches calls.
#[pyfunction]
fn crate_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Scans `code` (the raw file bytes) and returns `(comments, noqa_lines)`.
///
/// `comments` is a list of `(lineno, column, text)` tuples with 1-based
/// `lineno`, 0-based character `column`, and the decoded comment text
/// (including the leading `#`), matching `tokenize.TokenInfo` for
/// `tokenize.COMMENT` tokens. `noqa_lines` maps error codes to sets of line
/// numbers, with `NOQA_CODE_MAP` applied and bare `# noqa` mapped to `all`,
/// exactly like `deadcode.visitor.noqa.parse_noqa`.
///
/// Returns `None` when parity with the Python tokenizer cannot be guaranteed
/// (unknown encoding codec, or bytes that fail to decode); the Python
/// fallback then reproduces the exact tokenizer behaviour, including raising.
type CommentScan = (
    Vec<(usize, usize, String)>,
    HashMap<Vec<u8>, HashSet<usize>>,
);

#[pyfunction]
fn scan_comments(code: Vec<u8>) -> Option<CommentScan> {
    scan(&code)
}


// ---------------------------------------------------------------------------
// Encoding detection (mirrors tokenize.detect_encoding / PEP 263)
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq)]
enum Codec {
    Utf8,
    Latin1,
}

const BOM: [u8; 3] = [0xEF, 0xBB, 0xBF];

fn split_lines_keep(code: &[u8]) -> Vec<&[u8]> {
    let mut lines = Vec::new();
    let mut start = 0;
    for (index, byte) in code.iter().enumerate() {
        if *byte == b'\n' {
            lines.push(&code[start..=index]);
            start = index + 1;
        }
    }
    if start < code.len() {
        lines.push(&code[start..]);
    }
    lines
}

/// `tokenize.blank_re`: `^[ \t\f]*(?:[#\r\n]|$)`.
fn blank_line(line: &[u8]) -> bool {
    let mut index = 0;
    while index < line.len() && matches!(line[index], b' ' | b'\t' | 0x0C) {
        index += 1;
    }
    index >= line.len() || matches!(line[index], b'#' | b'\r' | b'\n')
}

fn is_cookie_name_char(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'-' || byte == b'.'
}

/// `tokenize.cookie_re`: `^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)` (ASCII).
/// Returns the captured codec name, or `None` when the line has no cookie.
fn cookie_name(line: &[u8]) -> Option<Vec<u8>> {
    let mut index = 0;
    while index < line.len() && matches!(line[index], b' ' | b'\t' | 0x0C) {
        index += 1;
    }
    if line.get(index) != Some(&b'#') {
        return None;
    }
    let mut cursor = index + 1;
    while cursor + 6 <= line.len() {
        if &line[cursor..cursor + 6] == b"coding"
            && matches!(line.get(cursor + 6), Some(b':') | Some(b'='))
        {
            let mut name = cursor + 7;
            while name < line.len() && matches!(line[name], b' ' | b'\t') {
                name += 1;
            }
            let start = name;
            while name < line.len() && is_cookie_name_char(line[name]) {
                name += 1;
            }
            if name > start {
                return Some(line[start..name].to_vec());
            }
        }
        cursor += 1;
    }
    None
}

/// `tokenize._get_normal_name`: lower-case, `_` -> `-`, first 12 characters,
/// then the recognised families collapse to their canonical names.
fn normalize_cookie_encoding(name: &[u8]) -> Vec<u8> {
    let mut normalized: Vec<u8> = name.iter().map(|byte| byte.to_ascii_lowercase()).collect();
    for byte in normalized.iter_mut() {
        if *byte == b'_' {
            *byte = b'-';
        }
    }
    normalized.truncate(12);
    if normalized == b"utf-8" || normalized.starts_with(b"utf-8-") {
        return b"utf-8".to_vec();
    }
    if normalized == b"latin-1"
        || normalized == b"iso-8859-1"
        || normalized == b"iso-latin-1"
        || normalized.starts_with(b"latin-1-")
        || normalized.starts_with(b"iso-8859-1-")
        || normalized.starts_with(b"iso-latin-1-")
    {
        return b"iso-8859-1".to_vec();
    }
    name.to_vec()
}

/// Returns `Ok(None)` when no cookie is present, `Ok(Some(codec))` for a
/// supported codec, and `Err(())` when Python would raise a `SyntaxError`
/// (unsupported codec, invalid bytes) — the caller then punts to the Python
/// fallback so the error surfaces exactly as before.
fn find_cookie(line: &[u8], bom_found: bool) -> Result<Option<Codec>, ()> {
    let text = std::str::from_utf8(line).map_err(|_| ())?;
    let Some(name) = cookie_name(line) else {
        return Ok(None);
    };
    let _ = text;
    let normalized = normalize_cookie_encoding(&name);
    let codec = match normalized.as_slice() {
        b"utf-8" | b"utf8" | b"u8" | b"utf" => Codec::Utf8,
        b"iso-8859-1" => Codec::Latin1,
        // Python's codecs.lookup succeeds for many other aliases; parity cannot
        // be guaranteed, so let the Python fallback handle the whole file.
        _ => return Err(()),
    };
    if bom_found && codec != Codec::Utf8 {
        // Python raises SyntaxError('encoding problem: utf-8') here.
        return Err(());
    }
    Ok(Some(codec))
}

/// Mirror of `tokenize.detect_encoding`. `Err(())` punts to the Python fallback.
fn detect_encoding(code: &[u8]) -> Result<Codec, ()> {
    let (bom_found, body) = if code.starts_with(&BOM) {
        (true, &code[3..])
    } else {
        (false, code)
    };
    let mut lines = split_lines_keep(body);
    let Some(first) = (!lines.is_empty()).then(|| lines.remove(0)) else {
        return Ok(Codec::Utf8);
    };
    if first.is_empty() {
        return Ok(Codec::Utf8);
    }
    // The first physical line: BOM already stripped, decoded per line below.
    let first_decodable = first;
    if let Some(codec) = find_cookie(first_decodable, bom_found)? {
        return Ok(codec);
    }
    if !blank_line(first_decodable) {
        return Ok(Codec::Utf8);
    }
    let Some(second) = (!lines.is_empty()).then(|| lines.remove(0)) else {
        return Ok(Codec::Utf8);
    };
    if second.is_empty() {
        return Ok(Codec::Utf8);
    }
    if let Some(codec) = find_cookie(second, bom_found)? {
        return Ok(codec);
    }
    Ok(Codec::Utf8)
}

// ---------------------------------------------------------------------------
// Byte-level tokenizer (comment/noqa extraction subset of tokenize._tokenize)
// ---------------------------------------------------------------------------

#[derive(Clone, Copy)]
enum StringKind {
    Single(char),
    Triple(char),
}

#[derive(Clone, Copy)]
struct ContinuedString {
    kind: StringKind,
    needcont: bool,
}

fn decode_line(line: &[u8], codec: Codec, strip_bom: bool) -> Option<Vec<char>> {
    let line = if strip_bom && line.starts_with(&BOM) {
        &line[3..]
    } else {
        line
    };
    match codec {
        Codec::Utf8 => std::str::from_utf8(line).ok().map(|s| s.chars().collect()),
        Codec::Latin1 => Some(line.iter().map(|byte| *byte as char).collect()),
    }
}

/// End of a string body on one line, mirroring `endpats`:
/// `Single  = [^'\\]*(?:\\.[^'\\]*)*'`
/// `Single3 = [^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''` (same scan rule).
fn find_string_end(chars: &[char], kind: StringKind, from: usize) -> Option<usize> {
    let max = chars.len();
    let mut pos = from;
    while pos < max {
        let c = chars[pos];
        if c == '\\' {
            // `\\.` consumes the escape pair; a trailing lone backslash cannot
            // complete an escape, so the string does not end on this line.
            if pos + 1 >= max {
                return None;
            }
            pos += 2;
            continue;
        }
        match kind {
            StringKind::Single(quote) => {
                if c == quote {
                    return Some(pos + 1);
                }
                // The regex character classes exclude `\n`.
                if c == '\n' {
                    return None;
                }
            }
            StringKind::Triple(quote) => {
                if c == quote && pos + 2 < max && chars[pos + 1] == quote && chars[pos + 2] == quote
                {
                    return Some(pos + 3);
                }
            }
        }
        pos += 1;
    }
    None
}

enum SingleOutcome {
    /// The string closed; scanning resumes after the closing quote.
    Closed(usize),
    /// The string continues on the next line (`\` + newline at the end).
    Continued,
    /// The `ContStr` regex failed: the opening quote becomes ERRORTOKEN and
    /// scanning resumes right after it (the content is re-scanned normally).
    Unterminated,
}

/// Mirrors `ContStr` for a single-quoted string opened at `open`.
fn scan_single_string(chars: &[char], open: usize, quote: char) -> SingleOutcome {
    let max = chars.len();
    let mut pos = open + 1;
    while pos < max {
        let c = chars[pos];
        if c == quote {
            return SingleOutcome::Closed(pos + 1);
        }
        if c == '\\' {
            match chars.get(pos + 1) {
                None => break,
                Some('\n') => return SingleOutcome::Continued,
                Some('\r') if chars.get(pos + 2) == Some(&'\n') => {
                    return SingleOutcome::Continued;
                }
                // `\\.`: the escaped character may be anything but a newline.
                Some(_) => pos += 2,
            }
            continue;
        }
        if c == '\n' {
            break;
        }
        pos += 1;
    }
    SingleOutcome::Unterminated
}

fn ends_with_backslash_newline(chars: &[char]) -> bool {
    let n = chars.len();
    (n >= 2 && chars[n - 2] == '\\' && chars[n - 1] == '\n')
        || (n >= 3 && chars[n - 3] == '\\' && chars[n - 2] == '\r' && chars[n - 1] == '\n')
}

/// Index of the first `\r` or `\n` at or after `from`, or the line length.
fn first_cr_or_newline(chars: &[char], from: usize) -> usize {
    let mut end = from;
    while end < chars.len() && chars[end] != '\r' && chars[end] != '\n' {
        end += 1;
    }
    end
}

fn scan(code: &[u8]) -> Option<CommentScan> {
    let codec = detect_encoding(code).ok()?;
    let strip_bom = code.starts_with(&BOM);
    let raw_lines = split_lines_keep(code);

    let mut comments: Vec<(usize, usize, String)> = Vec::new();
    let mut continued_string: Option<ContinuedString> = None;
    let mut parenlev: i32 = 0;
    let mut continued = false;
    let mut indents: Vec<usize> = vec![0];

    for (index, raw_line) in raw_lines.iter().enumerate() {
        // `_tokenize` decodes each line right before processing it, so a
        // tokenization failure on an earlier line happens before a later
        // line's decode failure would matter.
        let Some(chars) = decode_line(raw_line, codec, strip_bom) else {
            // Python raises UnicodeDecodeError here; punt to the fallback.
            return None;
        };
        let lnum = index + 1;
        let max = chars.len();
        let mut pos = 0usize;

        if let Some(pending) = continued_string {
            if max == 0 {
                // `tokenize` raises TokenError("EOF in multi-line string").
                return Some(assignment_failure(code));
            }
            if let Some(end) = find_string_end(&chars, pending.kind, 0) {
                pos = end;
                continued_string = None;
                // Fall through: the rest of the line is scanned normally.
            } else if pending.needcont && !ends_with_backslash_newline(&chars) {
                // ERRORTOKEN consumes the rest of the line whole.
                continued_string = None;
                continue;
            } else {
                continue;
            }
        } else if parenlev == 0 && !continued {
            if max == 0 {
                break;
            }
            let mut column = 0usize;
            while pos < max {
                match chars[pos] {
                    ' ' => column += 1,
                    '\t' => column = (column / 8 + 1) * 8,
                    '\u{c}' => column = 0,
                    _ => break,
                }
                pos += 1;
            }
            if pos == max {
                break;
            }
            match chars[pos] {
                '#' => {
                    // Comment-only line: `line[pos:].rstrip('\r\n')`.
                    let mut end = max;
                    while end > pos && (chars[end - 1] == '\r' || chars[end - 1] == '\n') {
                        end -= 1;
                    }
                    comments.push((lnum, pos, chars[pos..end].iter().collect()));
                    continue;
                }
                '\r' | '\n' => continue,
                _ => {}
            }
            if column > *indents.last().unwrap() {
                indents.push(column);
            }
            while column < *indents.last().unwrap() {
                if !indents.contains(&column) {
                    // IndentationError("unindent does not match any outer
                    // indentation level").
                    return Some(assignment_failure(code));
                }
                indents.pop();
            }
        } else {
            if max == 0 {
                // TokenError("EOF in multi-line statement").
                return Some(assignment_failure(code));
            }
            continued = false;
        }

        while pos < max {
            // `Whitespace = [ \f\t]*`
            while pos < max && matches!(chars[pos], ' ' | '\t' | '\u{c}') {
                pos += 1;
            }
            if pos >= max {
                break;
            }
            let c = chars[pos];
            if c == '\\' {
                // `PseudoExtras = \\\r?\n | \Z | Comment | Triple`: a backslash
                // directly before the line terminator is a line continuation.
                if chars.get(pos + 1) == Some(&'\n')
                    || (chars.get(pos + 1) == Some(&'\r') && chars.get(pos + 2) == Some(&'\n'))
                {
                    continued = true;
                    break;
                }
                // Any other backslash is ERRORTOKEN (one character).
                pos += 1;
                continue;
            }
            if c == '#' {
                // `Comment = #[^\r\n]*`
                let end = first_cr_or_newline(&chars, pos);
                comments.push((lnum, pos, chars[pos..end].iter().collect()));
                pos = end;
                continue;
            }
            if c == '\'' || c == '"' {
                if pos + 2 < max && chars[pos + 1] == c && chars[pos + 2] == c {
                    if let Some(end) = find_string_end(&chars, StringKind::Triple(c), pos + 3) {
                        pos = end;
                    } else {
                        continued_string = Some(ContinuedString {
                            kind: StringKind::Triple(c),
                            needcont: false,
                        });
                        break;
                    }
                    continue;
                }
                match scan_single_string(&chars, pos, c) {
                    SingleOutcome::Closed(end) => pos = end,
                    SingleOutcome::Continued => {
                        continued_string = Some(ContinuedString {
                            kind: StringKind::Single(c),
                            needcont: true,
                        });
                        break;
                    }
                    SingleOutcome::Unterminated => pos += 1,
                }
                continue;
            }
            match c {
                '(' | '[' | '{' => parenlev += 1,
                ')' | ']' | '}' => parenlev -= 1,
                _ => {}
            }
            pos += 1;
        }
    }

    if continued_string.is_some() || parenlev != 0 || continued {
        return Some(assignment_failure(code));
    }

    let noqa_lines = derive_noqa(code, &comments, codec);
    Some((comments, noqa_lines))
}

/// The result `tokenize` failure produces in `deadcode` today: no COMMENT
/// tokens and the raw-line `noqa` map of `parse_noqa(code, None)`.
fn assignment_failure(code: &[u8]) -> CommentScan {
    let mut noqa_lines = HashMap::new();
    for (index, line) in code.split(|byte| *byte == b'\n').enumerate() {
        match_noqa_line(&mut noqa_lines, index + 1, line);
    }
    (Vec::new(), noqa_lines)
}

// ---------------------------------------------------------------------------
// `# noqa` matching (mirrors deadcode.visitor.noqa.NOQA_REGEXP)
// ---------------------------------------------------------------------------

const NOQA_CODE_MAP: &[(&[u8], &[u8])] = &[
    (b"F401", b"DC07"),
    (b"F841", b"DC01"),
    (b"DC01", b"DC01"),
    (b"DC02", b"DC02"),
    (b"DC03", b"DC03"),
    (b"DC04", b"DC04"),
    (b"DC05", b"DC05"),
    (b"DC06", b"DC06"),
    (b"DC07", b"DC07"),
    (b"DC08", b"DC08"),
    (b"DC09", b"DC09"),
    (b"DC11", b"DC11"),
    (b"DC12", b"DC12"),
    (b"DC13", b"DC13"),
    (b"DC001", b"DC01"),
    (b"DC002", b"DC02"),
    (b"DC003", b"DC03"),
    (b"DC004", b"DC04"),
    (b"DC005", b"DC05"),
    (b"DC006", b"DC06"),
    (b"DC007", b"DC07"),
    (b"DC008", b"DC08"),
    (b"DC009", b"DC09"),
    (b"DC011", b"DC11"),
    (b"DC012", b"DC12"),
    (b"DC013", b"DC13"),
];

fn is_noqa_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0C | 0x0B)
}

/// `NOQA_REGEXP.search`:
/// `# noqa(?::[\s]?(?P<codes>([A-Z]+[0-9]+(?:[,\s]+)?)+))?` with IGNORECASE.
/// Returns `Some(None)` for a bare `# noqa` (mapped to `all`) and
/// `Some(Some(codes))` for `# noqa: <codes>`; `None` when nothing matches.
fn find_noqa(text: &[u8]) -> Option<Option<Vec<u8>>> {
    let n = text.len();
    if n < 6 {
        return None;
    }
    for index in 0..=n - 6 {
        if text[index] == b'#'
            && text[index + 1] == b' '
            && text[index + 2].eq_ignore_ascii_case(&b'n')
            && text[index + 3].eq_ignore_ascii_case(&b'o')
            && text[index + 4].eq_ignore_ascii_case(&b'q')
            && text[index + 5].eq_ignore_ascii_case(&b'a')
        {
            let mut codes: Option<Vec<u8>> = None;
            if text.get(index + 6) == Some(&b':') {
                let mut pos = index + 7;
                if text.get(pos).copied().is_some_and(is_noqa_whitespace) {
                    pos += 1;
                }
                let mut segments = 0;
                let mut codes_end = pos;
                let mut cursor = pos;
                loop {
                    let letters = cursor;
                    while cursor < n && text[cursor].is_ascii_alphabetic() {
                        cursor += 1;
                    }
                    if cursor == letters {
                        break;
                    }
                    let digits = cursor;
                    while cursor < n && text[cursor].is_ascii_digit() {
                        cursor += 1;
                    }
                    if cursor == digits {
                        break;
                    }
                    segments += 1;
                    // `(?:[,\s]+)?` sits inside the repeated unit, so a unit may
                    // end with separators when the next segment never starts;
                    // the capture keeps them (Python's map then gains the inert
                    // empty-code key from splitting on the comma).
                    while cursor < n && (text[cursor] == b',' || is_noqa_whitespace(text[cursor])) {
                        cursor += 1;
                    }
                    codes_end = cursor;
                }
                if segments > 0 {
                    codes = Some(text[pos..codes_end].to_vec());
                }
            }
            return Some(codes);
        }
    }
    None
}

/// `_match_noqa_line`: apply `NOQA_REGEXP` to one line and record its lineno.
fn match_noqa_line(noqa_lines: &mut HashMap<Vec<u8>, HashSet<usize>>, lineno: usize, line: &[u8]) {
    let Some(codes) = find_noqa(line) else {
        return;
    };
    match codes {
        None => {
            noqa_lines
                .entry(b"all".to_vec())
                .or_default()
                .insert(lineno);
        }
        Some(codes) => {
            for code in codes.split(|byte| *byte == b',') {
                let mut start = 0;
                let mut end = code.len();
                while start < end && is_noqa_whitespace(code[start]) {
                    start += 1;
                }
                while end > start && is_noqa_whitespace(code[end - 1]) {
                    end -= 1;
                }
                let stripped = &code[start..end];
                let mapped = NOQA_CODE_MAP
                    .iter()
                    .find(|(key, _)| *key == stripped)
                    .map(|(_, value)| value.to_vec())
                    .unwrap_or_else(|| stripped.to_vec());
                noqa_lines.entry(mapped).or_default().insert(lineno);
            }
        }
    }
}

fn encode_comment(text: &str, codec: Codec) -> Vec<u8> {
    match codec {
        Codec::Utf8 => text.as_bytes().to_vec(),
        Codec::Latin1 => text
            .chars()
            .map(|c| u8::try_from(c as u32).unwrap_or(b'?'))
            .collect(),
    }
}

/// The `noqa` map of `parse_noqa`: raw-line matching for lines without a
/// COMMENT token, comment-text matching for the lines that have one.
fn derive_noqa(
    code: &[u8],
    comments: &[(usize, usize, String)],
    codec: Codec,
) -> HashMap<Vec<u8>, HashSet<usize>> {
    let mut noqa_lines = HashMap::new();
    let commented: HashSet<usize> = comments.iter().map(|(lineno, _, _)| *lineno).collect();
    for (index, line) in code.split(|byte| *byte == b'\n').enumerate() {
        let lineno = index + 1;
        if !commented.contains(&lineno) {
            match_noqa_line(&mut noqa_lines, lineno, line);
        }
    }
    for (lineno, _, text) in comments {
        let bytes = encode_comment(text, codec);
        match_noqa_line(&mut noqa_lines, *lineno, &bytes);
    }
    noqa_lines
}

// ---------------------------------------------------------------------------
// Module export collection (Phase 2 second candidate, D6)
// ---------------------------------------------------------------------------

/// Collects the statically known module exports from an already-parsed
/// `ast.Module` tree, replicating
/// `deadcode.visitor.module_exports.collect_module_exports` exactly.
///
/// No Rust-side parsing: the Python `ast.parse` result is traversed via pyo3
/// (the prototype measurement favoured traversal over a Python-built
/// serialised representation, whose walk would reproduce the very cost being
/// optimised away).
///
/// The traversal visits statement containers only: `Assign`/`AnnAssign`/
/// `AugAssign` nodes are statements, so expression subtrees cannot contain a
/// binding, and `tree.body` order (which decides which static `__all__`
/// binding wins) is preserved by the breadth-first statement descent. Node
/// classes produced by `ast.parse` are classified once per call and cached by
/// type; classes outside the known statement grammar fall back to the full
/// `ast.walk`-equivalent generic traversal with `isinstance` checks, so the
/// semantics match the Python implementation for any tree.
///
/// Returns `None` when `__all__` is bound anywhere in the module without a
/// module-level all-string list/tuple value (exports unknown), the exported
/// name set otherwise — the same contract as the Python implementation. Any
/// traversal error propagates so the caller can fall back to Python.
#[pyfunction]
fn collect_module_exports(py: Python<'_>, tree: &Bound<'_, PyAny>) -> PyResult<Option<Py<PyAny>>> {
    let ast_module = py.import("ast")?;
    let classes = AstClasses::load(&ast_module)?;
    let mut cache: HashMap<usize, TypeInfo> = HashMap::new();

    let mut has_binding = false;
    let mut has_unknown_binding = false;
    let mut static_exports: HashSet<String> = HashSet::new();

    // Breadth-first walk over statement containers, preserving the
    // module-level (tree.body) order of ast.walk.
    let mut queue: VecDeque<Py<PyAny>> = VecDeque::new();
    queue.push_back(tree.clone().unbind());
    while let Some(node_owned) = queue.pop_front() {
        let node = node_owned.bind(py);
        let info = classify(node, &classes, &mut cache)?;
        match info.binding {
            BindingKind::NotBinding => {}
            BindingKind::Assign => {
                let mut binds = false;
                for target in node.getattr("targets")?.try_iter()? {
                    if is_name__all__(&target?)? {
                        binds = true;
                        break;
                    }
                }
                if binds {
                    record_binding(
                        tree,
                        node,
                        &classes,
                        true,
                        &mut has_binding,
                        &mut has_unknown_binding,
                        &mut static_exports,
                    )?;
                }
            }
            BindingKind::AnnAssign => {
                if is_name__all__(&node.getattr("target")?)? {
                    record_binding(
                        tree,
                        node,
                        &classes,
                        true,
                        &mut has_binding,
                        &mut has_unknown_binding,
                        &mut static_exports,
                    )?;
                }
            }
            BindingKind::AugAssign => {
                if is_name__all__(&node.getattr("target")?)? {
                    record_binding(
                        tree,
                        node,
                        &classes,
                        false,
                        &mut has_binding,
                        &mut has_unknown_binding,
                        &mut static_exports,
                    )?;
                }
            }
        }
        match &info.container_fields {
            Some(fields) => {
                for field in fields {
                    for child in node.getattr(field)?.try_iter()? {
                        queue.push_back(child?.unbind());
                    }
                }
            }
            None => {
                for child in generic_children(node, &classes)? {
                    queue.push_back(child);
                }
            }
        }
    }

    if has_unknown_binding {
        return Ok(None);
    }
    if !has_binding {
        let names = public_module_level_names(tree, &classes)?;
        return Ok(Some(set_from_strings(py, &names)?));
    }
    Ok(Some(set_from_strings(py, &static_exports)?))
}

/// The `ast` classes the traversal dispatches on, loaded once per call.
struct AstClasses {
    ast_cls: Py<PyAny>,
    assign_cls: Py<PyAny>,
    ann_assign_cls: Py<PyAny>,
    aug_assign_cls: Py<PyAny>,
    list_cls: Py<PyAny>,
    tuple_cls: Py<PyAny>,
    constant_cls: Py<PyAny>,
    name_cls: Py<PyAny>,
    function_def_cls: Py<PyAny>,
    async_function_def_cls: Py<PyAny>,
    class_def_cls: Py<PyAny>,
    import_cls: Py<PyAny>,
    import_from_cls: Py<PyAny>,
}

impl AstClasses {
    fn load(ast_module: &Bound<'_, PyModule>) -> PyResult<Self> {
        Ok(Self {
            ast_cls: ast_module.getattr("AST")?.unbind(),
            assign_cls: ast_module.getattr("Assign")?.unbind(),
            ann_assign_cls: ast_module.getattr("AnnAssign")?.unbind(),
            aug_assign_cls: ast_module.getattr("AugAssign")?.unbind(),
            list_cls: ast_module.getattr("List")?.unbind(),
            tuple_cls: ast_module.getattr("Tuple")?.unbind(),
            constant_cls: ast_module.getattr("Constant")?.unbind(),
            name_cls: ast_module.getattr("Name")?.unbind(),
            function_def_cls: ast_module.getattr("FunctionDef")?.unbind(),
            async_function_def_cls: ast_module.getattr("AsyncFunctionDef")?.unbind(),
            class_def_cls: ast_module.getattr("ClassDef")?.unbind(),
            import_cls: ast_module.getattr("Import")?.unbind(),
            import_from_cls: ast_module.getattr("ImportFrom")?.unbind(),
        })
    }
}

/// `isinstance(object, cls)` on the object's class: exact type matches are a
/// pointer compare, subclasses fall through to `is_subtype_of`.
fn is_class_of<'py>(
    py: Python<'py>,
    object: &Bound<'py, PyAny>,
    class: &Py<PyAny>,
) -> PyResult<bool> {
    let type_obj = object.get_type();
    if type_obj.as_ptr() == class.bind(py).as_ptr() {
        return Ok(true);
    }
    type_obj.is_subclass(class.bind(py))
}

#[derive(Clone, Copy, PartialEq)]
enum BindingKind {
    /// Not an assignment node, or an assignment to a different name.
    NotBinding,
    /// `ast.Assign`: `targets` is a list.
    Assign,
    /// `ast.AnnAssign`: a single `target`, eligible for a static export.
    AnnAssign,
    /// `ast.AugAssign`: a single `target`, never a static export.
    AugAssign,
}

/// Per-node-class facts, cached by type pointer for the duration of a call.
#[derive(Clone)]
struct TypeInfo {
    /// Statement-container field names whose items are enqueued in the
    /// pruned traversal; `None` marks an unknown class, whose every field is
    /// walked generically like `ast.iter_child_nodes` does.
    container_fields: Option<Vec<String>>,
    binding: BindingKind,
}

/// Classifies a node's class: known statement classes take the fast
/// name-based path; anything else is derived from its `_fields` and
/// `isinstance` checks, matching Python semantics exactly.
fn classify<'py>(
    node: &Bound<'py, PyAny>,
    classes: &AstClasses,
    cache: &mut HashMap<usize, TypeInfo>,
) -> PyResult<TypeInfo> {
    let type_obj = node.get_type();
    let type_ptr = type_obj.as_ptr() as usize;
    if let Some(info) = cache.get(&type_ptr) {
        return Ok(info.clone());
    }
    let info = build_type_info(&type_obj, classes)?;
    cache.insert(type_ptr, info.clone());
    Ok(info)
}

fn build_type_info(type_obj: &Bound<'_, PyType>, classes: &AstClasses) -> PyResult<TypeInfo> {
    let name = type_obj.name()?.to_string();
    let known: Option<(&[&str], BindingKind)> = match name.as_str() {
        "Module" | "FunctionDef" | "AsyncFunctionDef" | "ClassDef" | "ExceptHandler"
        | "match_case" => Some((&["body"], BindingKind::NotBinding)),
        "For" | "AsyncFor" | "While" | "If" => Some((&["body", "orelse"], BindingKind::NotBinding)),
        "With" | "AsyncWith" => Some((&["body"], BindingKind::NotBinding)),
        "Try" | "TryStar" => Some((
            &["body", "handlers", "orelse", "finalbody"],
            BindingKind::NotBinding,
        )),
        "Assign" => Some((&[], BindingKind::Assign)),
        "AnnAssign" => Some((&[], BindingKind::AnnAssign)),
        "AugAssign" => Some((&[], BindingKind::AugAssign)),
        _ => None,
    };
    if let Some((container_fields, binding)) = known {
        return Ok(TypeInfo {
            container_fields: Some(
                container_fields
                    .iter()
                    .map(|name| (*name).to_string())
                    .collect(),
            ),
            binding,
        });
    }
    // Unknown class: derive everything from the instance itself, exactly like
    // the Python implementation's isinstance-based semantics.
    let py = type_obj.py();
    let binding = if type_obj.is_subclass(classes.assign_cls.bind(py))? {
        BindingKind::Assign
    } else if type_obj.is_subclass(classes.ann_assign_cls.bind(py))? {
        BindingKind::AnnAssign
    } else if type_obj.is_subclass(classes.aug_assign_cls.bind(py))? {
        BindingKind::AugAssign
    } else {
        BindingKind::NotBinding
    };
    Ok(TypeInfo {
        container_fields: None,
        binding,
    })
}

/// A node that binds `__all__` was found: record the binding state.
///
/// `static_eligible` mirrors the Python `isinstance(node, (ast.Assign,
/// ast.AnnAssign))` condition; an `ast.AugAssign` always leaves the exports
/// unknown.
#[allow(clippy::too_many_arguments)]
fn record_binding(
    tree: &Bound<'_, PyAny>,
    node: &Bound<'_, PyAny>,
    classes: &AstClasses,
    static_eligible: bool,
    has_binding: &mut bool,
    has_unknown_binding: &mut bool,
    static_exports: &mut HashSet<String>,
) -> PyResult<()> {
    *has_binding = true;
    if static_eligible && is_module_level_statement(tree, node)? {
        let value = node.getattr("value")?;
        if is_class_of(node.py(), &value, &classes.list_cls)?
            || is_class_of(node.py(), &value, &classes.tuple_cls)?
        {
            if let Some(exports) = static_exports_from(&value, classes)? {
                *static_exports = exports;
                return Ok(());
            }
        }
    }
    *has_unknown_binding = true;
    Ok(())
}

/// `_is_module_level_statement`: object identity with a `tree.body` element.
fn is_module_level_statement(tree: &Bound<'_, PyAny>, node: &Bound<'_, PyAny>) -> PyResult<bool> {
    for statement in tree.getattr("body")?.try_iter()? {
        if statement?.as_ptr() == node.as_ptr() {
            return Ok(true);
        }
    }
    Ok(false)
}

/// `_is_special_variable__all__` target test without an isinstance call:
/// among assignment targets only `ast.Name` nodes carry an `id` attribute.
#[allow(non_snake_case)]
fn is_name__all__(target: &Bound<'_, PyAny>) -> PyResult<bool> {
    match target.getattr("id") {
        Ok(id) => {
            let id: Bound<'_, PyString> = id.downcast_into()?;
            Ok(id == "__all__")
        }
        Err(err) => {
            if err.is_instance_of::<PyAttributeError>(target.py()) {
                Ok(false)
            } else {
                Err(err)
            }
        }
    }
}

/// `_collect_static_exports`: all elements string constants, or `None`.
fn static_exports_from<'py>(
    value: &Bound<'py, PyAny>,
    classes: &AstClasses,
) -> PyResult<Option<HashSet<String>>> {
    let mut exports = HashSet::new();
    for element in value.getattr("elts")?.try_iter()? {
        let element = element?;
        if !is_class_of(element.py(), &element, &classes.constant_cls)? {
            return Ok(None);
        }
        let constant_value = element.getattr("value")?;
        if !constant_value.is_instance_of::<PyString>() {
            return Ok(None);
        }
        exports.insert(constant_value.extract::<String>()?);
    }
    Ok(Some(exports))
}

/// `_collect_public_module_level_names`: public names bound at module level.
fn public_module_level_names(
    tree: &Bound<'_, PyAny>,
    classes: &AstClasses,
) -> PyResult<HashSet<String>> {
    let py = tree.py();
    let mut names: HashSet<String> = HashSet::new();
    for statement in tree.getattr("body")?.try_iter()? {
        let statement = statement?;
        if is_class_of(py, &statement, &classes.assign_cls)? {
            for target in statement.getattr("targets")?.try_iter()? {
                add_target_name(&target?, classes, &mut names)?;
            }
        } else if is_class_of(py, &statement, &classes.ann_assign_cls)?
            || is_class_of(py, &statement, &classes.aug_assign_cls)?
        {
            add_target_name(&statement.getattr("target")?, classes, &mut names)?;
        } else if is_class_of(py, &statement, &classes.function_def_cls)?
            || is_class_of(py, &statement, &classes.async_function_def_cls)?
            || is_class_of(py, &statement, &classes.class_def_cls)?
        {
            names.insert(statement.getattr("name")?.extract::<String>()?);
        } else if is_class_of(py, &statement, &classes.import_cls)? {
            for alias in statement.getattr("names")?.try_iter()? {
                add_alias_name(&alias?, &mut names, true)?;
            }
        } else if is_class_of(py, &statement, &classes.import_from_cls)? {
            for alias in statement.getattr("names")?.try_iter()? {
                let alias = alias?;
                let name = alias.getattr("name")?.extract::<String>()?;
                if name != "*" {
                    add_alias_name(&alias, &mut names, false)?;
                }
            }
        }
    }
    names.retain(|name| !name.starts_with('_'));
    Ok(names)
}

/// `_collect_target_names`: only bare `Name` targets bind a single name.
fn add_target_name(
    target: &Bound<'_, PyAny>,
    classes: &AstClasses,
    names: &mut HashSet<String>,
) -> PyResult<()> {
    if is_class_of(target.py(), target, &classes.name_cls)? {
        names.insert(target.getattr("id")?.extract::<String>()?);
    }
    Ok(())
}

/// `alias.asname or alias.name.partition('.')[0]`; `dotted` marks the `Import`
/// alias case, which keeps only the root package of a dotted module name.
fn add_alias_name(
    alias: &Bound<'_, PyAny>,
    names: &mut HashSet<String>,
    dotted: bool,
) -> PyResult<()> {
    let asname = alias.getattr("asname")?;
    if asname.is_truthy()? {
        names.insert(asname.extract::<String>()?);
        return Ok(());
    }
    let name = alias.getattr("name")?.extract::<String>()?;
    let chosen = if dotted {
        name.split('.').next().unwrap_or_default().to_string()
    } else {
        name
    };
    names.insert(chosen);
    Ok(())
}

/// The children of a node of an unknown class, in `ast.iter_child_nodes`
/// order: every `_fields` entry that is an `ast.AST` node, with list fields
/// flattened and missing attributes skipped like `ast.iter_fields` does.
fn generic_children<'py>(
    node: &Bound<'py, PyAny>,
    classes: &AstClasses,
) -> PyResult<Vec<Py<PyAny>>> {
    let py = node.py();
    let mut children = Vec::new();
    let fields = match node.getattr("_fields") {
        Ok(fields) => fields,
        Err(err) => {
            if err.is_instance_of::<PyAttributeError>(py) {
                return Ok(children);
            }
            return Err(err);
        }
    };
    let ast_cls = classes.ast_cls.bind(py);
    for field in fields.try_iter()? {
        let field_name: String = field?.extract()?;
        let value = match node.getattr(&field_name) {
            Ok(value) => value,
            Err(err) => {
                if err.is_instance_of::<PyAttributeError>(py) {
                    continue;
                }
                return Err(err);
            }
        };
        if value.is_instance(ast_cls)? {
            children.push(value.unbind());
        } else if value.is_instance_of::<PyList>() {
            for item in value.try_iter()? {
                let item = item?;
                if item.is_instance(ast_cls)? {
                    children.push(item.unbind());
                }
            }
        }
    }
    Ok(children)
}

fn set_from_strings(py: Python<'_>, strings: &HashSet<String>) -> PyResult<Py<PyAny>> {
    let set = pyo3::types::PySet::empty(py)?;
    for name in strings {
        set.add(name)?;
    }
    Ok(set.into_any().unbind())
}

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
    m.add_function(wrap_pyfunction!(crate_version, m)?)?;
    m.add_function(wrap_pyfunction!(scan_comments, m)?)?;
    m.add_function(wrap_pyfunction!(collect_module_exports, m)?)?;
    Ok(())
}
