# Rust integration

## What this page covers

This page documents how Rust integrates into deadcode: the runtime integration model, where the Rust code is stored in this repository, how the package is
built for both native and pure-Python installs, and how a release reaches PyPI. The plan was recorded in {doc}`dep_6`, which is the design record for the
whole Rust effort. The implementation now lives in the repository: the crate sits at the repository root (`Cargo.toml` plus Rust sources under `src/`),
the native extension module is `deadcode._native`, and the packaging, CI, and audit wiring described below is in place.

## Integration model

Python stays the reference implementation and the default install. The package tries to import a private native extension module inside the `deadcode`
package namespace — `deadcode._native` — and falls back to the Python implementation when the import fails, so a platform without a native wheel — or an
install without a compiled extension — behaves exactly as it does today. Whether the native extension or the Python fallback serves a request, stdout,
stderr, the exit status, and the file effects of `--fix` and `--dry` stay identical; DEP 6 makes this an explicit contract (see the
[Contracts](#contracts) section below).

## Where the Rust code lives

The Rust crate lives inside this repository as a maturin "mixed" project: `Cargo.toml` at the repository root and Rust sources under `src/`,
the default mixed layout that maturin documents (see the [project-layout reference](https://www.maturin.rs/project_layout) cited by {doc}`dep_6`). The
layout introduced no collision: the only pre-existing code directories are `deadcode/`, `tests/`, `docs/`, and `enhancement_proposals/`. Hatchling's
`include = ["**/*.py"]` setting in `pyproject.toml` keeps `Cargo.toml` and `src/` out of the fallback wheel, which preserves the pure-Python fallback
guarantee: the universal wheel remains Python-only no matter what lands in `src/`.

## Building the package

Two build paths produce wheels from the same source tree and the same version. Native wheels are built with `maturin` and `pyo3` using the
`abi3-py310` stable ABI, which matches the project's Python 3.10 floor (`pyproject.toml`) and lets one native wheel serve every Python version from
3.10 up on a given platform. The universal `py3-none-any` fallback wheel continues to be built by the existing hatchling backend from the same source
tree and the same version, so pip always has an OS-independent artifact to install. A Rust toolchain is required only for native builds, never for
installing deadcode or for building the fallback wheel. The release matrix is `manylinux` x86_64, `macosx` arm64, and `windows` x86_64; CI builds one
wheel per platform in a dedicated wheel-matrix job, while `make publish` builds the host platform's wheel locally via the scratch maturin toolchain.

## Publishing to PyPI

Today the release path is manual: `make publish` clears `dist/`, runs `hatch build` for the universal wheel and `maturin build` for the host platform's
native wheel via the scratch toolchain, then `uv publish`, creates the `v$(VERSION)` tag after the upload, and triggers the Read the Docs builds for the
new tag, `stable`, and `latest` via the Read the Docs API. Both wheel families carry the same name, version, console script, and Python floor, so pip
always finds an installable artifact — a native wheel where one exists for the platform, the universal wheel otherwise. The fallback wheel is published
for every release even when a native build fails, so an unsupported platform can never fall through to a source build. The Cargo dependency and AGPLv3
licence audit (`cargo deny check`, configured by the checked-in `deny.toml`) runs alongside the existing Python audits in the
vulnerability-audit workflow and is available locally as `make audit-cargo`. The tag is created after the upload and the Read the Docs steps keep their
order.

## Contracts

The contracts below constrain the Rust work. Each is stated with the file or section where it is fixed today.

- **Identical CLI output, exit status, and `--fix`/`--dry` file effects.** Fixed by {doc}`dep_6`'s contract bullets and implemented through the
  `deadcode` console script declared in `pyproject.toml:39-40`; any observable difference between the native and Python paths fails the gate.
- **AGPLv3-compatible crates with a Cargo audit alongside the Python audit.** Fixed by `LICENSE`, the AGPLv3 classifier in `pyproject.toml`, the
  implementation notes of {doc}`dep_6`, the `audit-cargo` target in the `Makefile`, the checked-in `deny.toml`, and
  `.github/workflows/vulnerability-audit.yml`.
- **Python 3.10 floor and `abi3-py310`.** Fixed by `requires-python` in `pyproject.toml:9`, the CI matrix of Python 3.10–3.15, and {doc}`dep_6`.
- **Universal-wheel fallback and the OS-independent claim.** Fixed by the `Operating System :: OS Independent` classifier in `pyproject.toml:14` and the
  scope of {doc}`dep_6`: a change that breaks installation on platforms without a native wheel is not acceptable.
- **The 100% changed-line coverage gate and strict mypy apply to Python code only.** Fixed by the `coverage-new` target in the `Makefile` and the
  strict mypy configuration in `pyproject.toml`, both of which scope to `deadcode/*.py`; they remain in force for the Python fallback and are not
  extended to Rust sources by this page.
- **The pre-commit hook stays installable everywhere via the fallback wheel.** Fixed by `.pre-commit-hooks.yaml` and verified by `make hook-test`, which
  installs the hook from the repository build.

## Relationship to DEP 6 and the staged plan

{doc}`dep_6` structures the Rust effort in four stages: Phase 0 adds the benchmark corpus and records the baseline, Phase 1 optimises the Python
implementation, Phase 2 moves measured hot paths into Rust one at a time, and Phase 3 changes packaging and release so both wheel families reach PyPI.
This page documents the integration, storage, build, and publishing decisions that those phases implement, so an implementation task can pick up
{doc}`dep_6` plus this page without re-deriving the packaging plan. Phases 0–3 are implemented: the benchmark harness records baseline and gate
measurements under `benchmarks/`, the comment/noqa scan and module export collection run natively when the extension is available, and Phase 3's
packaging, CI, and audit wiring is in place.

## What is out of scope

This page documents the Rust integration; it adds no code of its own and no packaging or CI change beyond what the phases implement. The page makes no
performance or speedup claim of its own: {doc}`dep_6` requires measured evidence, which lives in the benchmark records and gate records rather than in
this documentation.

## References

- DEP 6, "Improving performance with a Rust implementation": {doc}`dep_6`
- Maturin guide: https://www.maturin.rs/
- Maturin bindings and `abi3-py310`: https://www.maturin.rs/bindings
- Maturin project layout: https://www.maturin.rs/project_layout
- pydantic-core packaging as prior art: https://github.com/pydantic/pydantic-core/blob/main/pyproject.toml
- watchfiles packaging as prior art: https://github.com/samuelcolvin/watchfiles/blob/main/pyproject.toml
