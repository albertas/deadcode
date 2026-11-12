# DEP 5 - Improving performance with a Rust implementation
**Status**: Proposed
**Type**: Process
**Created**: 2026-11-12

## Problem statement

Issue #67, "Improve performance by using Rust" (`https://github.com/albertas/deadcode/issues/67`), asks whether deadcode could be ported to Rust and
built for both Python and Rust, with a Python build provided in case a platform-specific Rust build is unavailable, using `maturin` for packaging.
deadcode is a pure-Python, CPU-bound static analyser: it reads every discovered `.py` file, parses it with `ast.parse(..., type_comments=True)`, walks
the resulting tree with a custom `ast.NodeVisitor`, tokenises comments and `noqa` directives, and optionally rewrites the files.
The analysis therefore costs CPU time proportional to the amount of source code, and it runs synchronously inside the pre-commit hook and the
`deadcode` console script.

The repository has no benchmark suite and no committed performance baseline, so the size of the opportunity is not currently known.
A one-off `cProfile` sample of the package on itself recorded 912,678 function calls in 0.327 seconds over 29 files, with `DeadCodeVisitor.visit`
taking 0.164 seconds, a duplicate module-export parse taking 0.058 seconds, and comment tokenisation taking 0.027 seconds.
That sample is a sample, not a baseline: it measured the package on its own source with one interpreter, and it must not be presented as the expected
speedup for larger projects.
The missing benchmark is itself part of the problem, because without a repeatable corpus any Rust port would be an expensive guess rather than a
measured decision.

The absence of a measurement matters most where deadcode is used as a pre-commit hook, because every commit pays the analysis latency, and on large
projects, where thousands of files multiply the per-file parse, tokenise, and traversal costs.
The same costs recur in editor integrations and CI jobs that run deadcode over a whole repository.

Any solution must respect the project's existing contract and distribution constraints:

- Identical CLI output and exit status for the same inputs, including the `--fix` and `--dry` file effects and the exact message formatting.
- The existing 100% line-coverage gate and strict mypy checks must keep passing.
- The project is licensed under AGPLv3, so any bundled Rust dependency must be licence-compatible.
- The project publishes one universal `py3-none-any` wheel today and claims `Operating System :: OS Independent`, so a change that breaks installation
  on platforms without a native wheel is not acceptable.
- There is no benchmark and no Rust toolchain in CI, so the first stage of any work must add measurement and a build path rather than assume either exists.

## Considered alternatives

1. **Status quo, pure Python.**
   Description: keep the current implementation and change nothing.
   Trade-off: zero toolchain cost and zero behavioural risk, but the analysis cost stays as it is.
   Rejected because it does not answer issue #67 and leaves the performance question unmeasured; the issue and the unchecked README benchmarking item
   remain open.

2. **Python-only optimisation.**
   Description: remove duplicate parsing, reuse one token stream, and cache parsed modules while staying entirely in Python.
   Trade-off: low risk and no packaging change, but the achievable speedup is bounded by the interpreter and it does not provide the Rust build the
   issue requests.
   Rejected as the whole answer because it cannot satisfy the issue's explicit Rust requirement, although it is retained as Phase 1 of the chosen solution.

3. **Full Rust rewrite now.**
   Description: reimplement the analyser in Rust and ship it as the product.
   Trade-off: the largest potential speedup, but it must reproduce `ast.parse(type_comments=True)`, `ast.walk`, `ast.iter_fields`, `ast.unparse`,
   quoted annotations, type comments, `noqa`, exact messages, and file edits.
   Rejected because it puts the entire analysis contract, the 100% coverage gate, and strict typing at risk before any baseline proves the win, and it
   would add Cargo auditing and cross-platform wheel builds immediately.

4. **Measured hybrid Rust accelerator with a pure-Python fallback (chosen).**
   Description: keep Python as the reference implementation and default install, move only benchmark-proven hot paths into a small Rust extension
   built with `maturin`, and always publish a universal Python wheel of the same version.
   Trade-off: two build paths and a native dependency to maintain, in exchange for a bounded, reversible performance experiment that preserves the CLI
   contract and installs everywhere.
   Selected because it answers the issue, produces the missing measurement, and can stop after any stage without breaking users.

5. **Separate Rust binary invoked as a subprocess, as Ruff ships.**
   Description: build a standalone `deadcode` binary in Rust and have the Python package delegate to it.
   Trade-off: packaging and distribution are simpler and independent of CPython, but the importable `deadcode.cli` tests, the in-process `--fix`
   handling, and an automatic Python fallback are lost.
   Rejected because it forks the CLI contract and cannot provide the fallback the issue requires.

6. **Adopting `ruff_python_parser` or `rustpython-parser` immediately.**
   Description: replace the Python parser with an existing Rust Python parser at the start of the work.
   Trade-off: both crates are mature enough to parse Python, but they produce their own AST types; `ruff_python_parser` documents an unstable internal
   API, and `rustpython-parser` is superseded and has not released since 2024.
   Rejected because it forces an AST boundary design before the performance case is proven; parser replacement is deferred to the full-rewrite decision.

## Chosen solution

The chosen solution is a measured, incremental Rust accelerator with a pure-Python fallback.
Python remains the reference implementation and the default install; Rust is limited to hot paths proven by a benchmark; `maturin` plus `pyo3` and the
`abi3-py310` stable ABI build the native wheels; and a universal `py3-none-any` fallback wheel of the same name and version is built from the same
source tree with the existing `hatchling` backend.
At runtime the Python package tries to import the native module and falls back to the Python implementation on `ImportError`, with no change to
stdout, stderr, or exit status.
A full Rust rewrite is not part of this proposal; it would become a separate DEP only if the measured gates justify it.

The work proceeds in four stages:

- **Phase 0, measure.** Add a benchmark corpus that includes deadcode itself plus at least two larger real projects, and record wall-clock time, CPU
  time, peak memory, and output parity for a fixed command on every corpus entry.
- **Phase 1, optimise Python first.** Remove the duplicate parsing in `_collect_module_exports`, reuse one token stream for comment and `noqa`
  scanning, and cache parsed modules per run.
  These changes need no toolchain and shrink the code that a Rust extension would later replace.
- **Phase 2, accelerate measured hot paths.** Move one hot path at a time into a small Rust extension built with `maturin` and `pyo3`, in the order
  shown by Phase 0: tokenisation and comment/`noqa` scanning first, then module export collection, then AST traversal only if it still dominates after
  the first two.
  Each step keeps the Python function as the fallback and must produce byte-identical output.
- **Phase 3, package and release.** Publish `abi3-py310` native wheels built by `maturin` for the platforms in the release matrix, plus the
  `py3-none-any` fallback wheel built from the same source tree with `hatchling`.
  Both carry the same project name, version, dependency metadata, console script, and Python floor, so pip prefers a compatible platform wheel and
  otherwise installs the universal wheel.

Native wheels ship only when both measurement criteria are met:

- On the benchmark corpus, median end-to-end wall-clock time falls by at least 25%, no measured case regresses by more than 5%, and peak memory stays
  within 1.2x of the Python baseline.
- All existing functional tests produce identical CLI output, exit status, and `--fix`/`--dry` file effects.

If the shipping gate is not met, native wheels are not shipped, the pure-Python wheel remains the only artifact, and issue #67 is closed as measured
and not justified.
A full rewrite is considered only if profiling after Phase 2 still shows at least 50% of analysis time in Python traversal and a throwaway prototype
reaches at least 2x end-to-end on the corpus; that rewrite would be its own DEP with its own fallback and migration plan.

The hybrid was selected over the status quo and Python-only optimisation because only it produces the Rust build the issue asks for while keeping a
measured exit condition.
It was selected over a full rewrite and over immediate parser replacement because it preserves the Python analysis contract, the 100% coverage gate,
and strict typing while the size of the win is still unknown.
It was selected over a separate Rust binary because keeping the Python package importable preserves the `deadcode.cli` tests, the in-process `--fix`
behaviour, and the automatic fallback.

## Scope

This DEP covers the proposal only, and the following items are explicitly out of scope:

- No Rust code, `Cargo.toml`, `maturin` configuration, benchmark harness, CI change, or packaging change is implemented in this change.
- No analyser behaviour changes: findings, messages, CLI options, output format, exit status, and `--fix`/`--dry` semantics stay as they are.
- No parser replacement: the Python `ast` pipeline remains in place, and adopting a Rust parser is deferred to a possible later DEP.
- No support promise for platforms outside the published wheel matrix.
- No PyPy native wheel.
- No free-threaded-specific wheel (`abi3t`).
- No new CLI options.

## Implementation notes

The functional contract to preserve is the `deadcode` console script, `python -m deadcode.cli`, the exact message formatting, exit status 0 or 1, the
`--fix`/`--dry` file effects, and the documented configuration behaviour.
Every accelerated path must be compared against the Python baseline on the benchmark corpus and on the existing functional suite, and any difference
in output or file effects fails the gate.

The release work must add a Cargo dependency and licence audit alongside the existing Python dependency audit, and every new crate must be AGPLv3-compatible.
CI needs a wheel matrix that builds `abi3-py310` wheels for the supported platforms and that publishes the `py3-none-any` fallback wheel for every
release, not only for releases where a native build succeeds.
The fallback wheel must be built from the same source tree and carry the same version, so that installing on an unsupported platform or without a Rust
toolchain never falls through to a source build.

The first measurable deliverable is the benchmark from Phase 0; no speedup may be claimed in release notes, documentation, or this DEP until that
benchmark exists and the shipping gate has been evaluated.

## References

- Issue #67, "Improve performance by using Rust": https://github.com/albertas/deadcode/issues/67
- DEP process page proposed in PR #109: `docs/dep.md`
- Maturin guide: https://www.maturin.rs/
- Maturin bindings and `abi3-py310`: https://www.maturin.rs/bindings
- Maturin project layout and `module-name`: https://www.maturin.rs/project_layout
- Ruff packaging as prior art: https://github.com/astral-sh/ruff/blob/main/pyproject.toml
- pydantic-core packaging as prior art: https://github.com/pydantic/pydantic-core/blob/main/pyproject.toml
- watchfiles packaging as prior art: https://github.com/samuelcolvin/watchfiles/blob/main/pyproject.toml
- Python `ast` documentation for fidelity constraints: https://docs.python.org/3/library/ast.html
- `ruff_python_parser` crate: https://crates.io/crates/ruff_python_parser
- `rustpython-parser` crate: https://crates.io/crates/rustpython-parser
