# Rust integration

## What this page covers

This page documents how Rust integrates into deadcode: the runtime integration model, the native API, where the Rust code is stored in this repository, how
the package is built for both native and pure-Python installs, how a release reaches PyPI, and the measured effect of the combined extension. The plan was
recorded in {doc}`dep_6`, which is the design record for the whole Rust effort. The implementation lives in the repository: one crate at the repository root
(`Cargo.toml` plus Rust sources under `src/`), one native extension module `deadcode._native`, and the packaging, CI, and audit wiring described below.

## Integration model

Python stays the reference implementation and the default install. The package tries once, at import time, to load the private native extension module
`deadcode._native` through `deadcode/_native_loader.py` and falls back to the Python implementation when the import fails, so a platform without a native
wheel — or an install without a compiled extension — behaves exactly as it does today. Whether the native extension or the Python fallback serves a
request, stdout, stderr, the exit status, and the file effects of `--fix` and `--dry` stay identical; DEP 6 makes this an explicit contract (see the
[Contracts](#contracts) section below).

Each accelerated call site owns its own fallback. The parser seam in `deadcode/actions/parse_abstract_syntax_tree.py` calls `parse_module` first and uses
`ast.parse` when the extension is absent or raises an unexpected exception; a native `ParseError` keeps the existing parse-failure message. String-mode
parsing goes through `_native_parse`, which uses `parse_expression`, `parse_statement`, or `parse_func_type` and raises `SyntaxError` on `ParseError` so
the existing call-site handling keeps working. The comment/`noqa` scanner and the module-export collector in `deadcode/visitor/` fall back to their
unchanged Python implementations on any native absence or exception.

## Native API

The single extension module exposes one parser, one scanner, and one export collector:

- `parse_module(source: bytes, filename: str, type_comments: bool) -> ast.Module` parses a module from raw bytes, honouring the source encoding and type
  comments, and converts the Rust AST into the Python `ast` object graph.
- `parse_expression(source: str, filename: str)`, `parse_statement(source: str, filename: str)`, and `parse_func_type(source: str, filename: str)` parse
  the string modes used by annotation strings, type comments, function-type comments, and commented-out-code probes.
- `scan_comments(source: bytes)` returns the comment tokens and their line numbers from one scanner pass, so comment and `noqa` handling consumes a single
  token stream instead of re-tokenising each file.
- `collect_module_exports(tree)` walks an already-parsed Python `ast.Module` and returns the module's export set, or `None` when the exports cannot be
  determined statically.
- `crate_version()` and the `ParseError` exception type complete the module surface.

The analysis pipeline parses each discovered file once through the parser seam and keeps the resulting tree in the per-run `_parsed_modules` cache. The
same tree serves module-export collection and the visitor traversal, and the scanned comment tokens serve the commented-out-code check, so a default run
performs one read, one parse, and one comment scan per file. The visitor, reachability analysis, import-part fixing, and the CLI stay in Python.

## Where the Rust code lives

The Rust crate lives inside this repository as a maturin "mixed" project: `Cargo.toml` at the repository root and Rust sources under `src/`, the default
mixed layout that maturin documents (see the [project-layout reference](https://www.maturin.rs/project_layout) cited by {doc}`dep_6`). `src/lib.rs` holds
the module registration, the comment/`noqa` scanner, the module-export collector, and the parser entry points; `src/convert.rs` holds the Rust-AST to
Python-`ast` converter. Hatchling's `include = ["**/*.py"]` setting in `pyproject.toml` keeps `Cargo.toml` and `src/` out of the fallback wheel, which
preserves the pure-Python fallback guarantee: the universal wheel remains Python-only no matter what lands in `src/`.

## Building the package

Two build paths produce wheels from the same source tree and the same version. Native wheels are built with `maturin` and `pyo3` using the `abi3-py310`
stable ABI, which matches the project's Python 3.10 floor (`pyproject.toml`) and lets one native wheel serve every Python version from 3.10 up on a given
platform. The universal `py3-none-any` fallback wheel continues to be built by the existing hatchling backend from the same source tree and the same
version, so pip always has an OS-independent artifact to install. A Rust toolchain is required only for native builds, never for installing deadcode or
for building the fallback wheel.

The release matrix is `manylinux` x86_64, `macosx` arm64, and `windows` x86_64; CI builds one wheel per platform in a dedicated wheel-matrix job, runs a
`native-parity` job that builds the extension and runs the full suite against it, and keeps the default test matrix native-free. Locally, `make
build-native` builds and installs the extension into the scratch `.venv-maturin` environment, `make test-native` runs the suite against it and removes the
source-tree extension afterwards so later fallback runs stay native-free, and `make publish` builds the host platform's wheel via the same scratch
toolchain.

## Publishing to PyPI

Today the release path is manual: `make publish` clears `dist/`, runs `hatch build` for the universal wheel and `maturin build` for the host platform's
native wheel via the scratch toolchain, then `uv publish`, creates the `v$(VERSION)` tag after the upload, and triggers the Read the Docs builds for the
new tag, `stable`, and `latest` via the Read the Docs API. Both wheel families carry the same name, version, console script, and Python floor, so pip
always finds an installable artifact — a native wheel where one exists for the platform, the universal wheel otherwise. The fallback wheel is published
for every release even when a native build fails, so an unsupported platform can never fall through to a source build. The Cargo dependency and AGPLv3
licence audit (`cargo deny check`, configured by the checked-in `deny.toml`) runs alongside the existing Python audits in the vulnerability-audit workflow
and is available locally as `make audit-cargo`. The tag is created after the upload and the Read the Docs steps keep their order.

## Measured performance

The benchmark corpus (`benchmarks/corpus.json`) contains deadcode itself plus two larger real projects, flask and django, pinned by commit; the harness
(`benchmarks/run_benchmark.py`, wired as `make benchmark`) runs the fixed command `deadcode <entry-root> --count` under `/usr/bin/time -v`, performs one
warmup plus three timed runs per entry, and records wall-clock time, CPU time, peak RSS, exit status, findings count, and stdout/stderr SHA-256 hashes per
run. `benchmarks/records.py` aggregates one record set and compares a second record set against it via the harness's `--compare-to` option.

This combined tree was measured once in each install mode on the same sources: a fallback-only install (`.venv`, native module absent) and a native install
(`make build-native`, combined parser-plus-accelerator wheel in `.venv-maturin`). The per-entry median wall-clock times from that run are:

| Corpus entry | Fallback baseline | Native | Wall-clock speedup |
|---|---|---|---|
| deadcode | 0.20 s | 0.15 s | 1.33x |
| flask | 0.32 s | 0.23 s | 1.39x |
| django | 31.91 s | 22.40 s | 1.42x |

The aggregate geometric-mean wall-clock speedup is 1.38x (38% faster end-to-end), which clears the DEP 6 threshold of a 25% median wall-clock reduction; no
corpus entry regresses (the threshold allows up to a 5% regression); and peak RSS stays within 1.00x–1.08x of the Python baseline (threshold: 1.2x). Every
recorded run of both record sets is identical on all parity surfaces: stdout and stderr SHA-256 hashes, exit status, and the findings count (42 for
deadcode, 104 for flask, 3801 for django). The combined tree therefore meets the DEP 6 gate on this run.

The gains come from both hot paths now in Rust: the parser, which replaces the Python `ast.parse` call for every module, and the comment/`noqa` scan plus
module-export collection, which reuse one token stream and the already-parsed tree. The AST traversal itself stays in Python, so the native speedup is
bounded by the share of the run those paths cover; the measured end-to-end effect is a consistent speedup of roughly 1.4x on every corpus entry rather than
an order-of-magnitude change. The raw records — the fallback and native record sets, the per-run wall clocks, and the record-set comparison — are archived
with the task artifacts; the numbers can be reproduced from the same tree by building both installs and running the harness with `--compare-to` (see
`benchmarks/run_benchmark.py`). Pass an absolute `--deadcode` path: the harness runs each corpus entry with that entry as its working directory.

## Contracts

The contracts below constrain the Rust work. Each is stated with the file or section where it is fixed today.

- **Identical CLI output, exit status, and `--fix`/`--dry` file effects.** Fixed by {doc}`dep_6`'s contract bullets and implemented through the `deadcode`
  console script declared in `pyproject.toml`; any observable difference between the native and Python paths fails the gate.
- **AGPLv3-compatible crates with a Cargo audit alongside the Python audit.** Fixed by `LICENSE`, the AGPLv3 classifier in `pyproject.toml`, the
  implementation notes of {doc}`dep_6`, the `audit-cargo` target in the `Makefile`, the checked-in `deny.toml`, and
  `.github/workflows/vulnerability-audit.yml`.
- **Python 3.10 floor and `abi3-py310`.** Fixed by `requires-python` in `pyproject.toml`, the CI matrix of Python 3.10–3.15, and {doc}`dep_6`.
- **Universal-wheel fallback and the OS-independent claim.** Fixed by the `Operating System :: OS Independent` classifier in `pyproject.toml` and the scope
  of {doc}`dep_6`: a change that breaks installation on platforms without a native wheel is not acceptable.
- **The 100% changed-line coverage gate and strict mypy apply to Python code only.** Fixed by the `coverage-new` target in the `Makefile` and the strict
  mypy configuration in `pyproject.toml`, both of which scope to `deadcode/*.py`; they remain in force for the Python fallback and are not extended to Rust
  sources by this page.
- **The pre-commit hook stays installable everywhere via the fallback wheel.** Fixed by `.pre-commit-hooks.yaml` and verified by `make hook-test`, which
  installs the hook from the repository build.

## Relationship to DEP 6 and the staged plan

{doc}`dep_6` structures the Rust effort in four stages: Phase 0 adds the benchmark corpus and records the baseline, Phase 1 optimises the Python
implementation, Phase 2 moves measured hot paths into Rust one at a time, and Phase 3 changes packaging and release so both wheel families reach PyPI.
Phases 0–3 are implemented: the benchmark harness records baseline and combined gate measurements under `benchmarks/`, the native parser serves module
and string parsing, the comment/`noqa` scan and module export collection run natively when the extension is available, and Phase 3's packaging, CI, and
audit wiring is in place.

## What is out of scope

This page documents the Rust integration; it adds no code of its own and no packaging or CI change beyond what the phases implement. The performance section
above states only the measured gate results: {doc}`dep_6` requires measured evidence before any speedup claim, and the records referenced there are the
source of the numbers on this page. Moving the visitor, reachability analysis, or `--fix` into Rust is outside this integration.

## References

- DEP 6, "Improving performance with a Rust implementation": {doc}`dep_6`
- Maturin guide: https://www.maturin.rs/
- Maturin bindings and `abi3-py310`: https://www.maturin.rs/bindings
- Maturin project layout: https://www.maturin.rs/project_layout
- pydantic-core packaging as prior art: https://github.com/pydantic/pydantic-core/blob/main/pyproject.toml
- watchfiles packaging as prior art: https://github.com/samuelcolvin/watchfiles/blob/main/pyproject.toml
