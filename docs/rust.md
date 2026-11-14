# Rust integration

## What this page covers

This page documents, ahead of any implementation work, how Rust will integrate into deadcode: the runtime integration model, where the Rust code will be
stored in this repository, how the package will be built for both native and pure-Python installs, and how a release reaches PyPI. Everything on this
page describes a plan recorded in {doc}`dep_6`, which is the design record for the whole Rust effort; nothing described here is implemented yet. No Rust
code, no `Cargo.toml`, and no build configuration exist in the repository at the time of writing, and this page adds none of them.

## Integration model

Python stays the reference implementation and the default install. The package will try to import a private native extension module inside the `deadcode`
package namespace and fall back to the Python implementation on `ImportError`, so a platform without a native wheel — or an install without a compiled
extension — behaves exactly as it does today. The exact extension module name is left to the future implementation task, which will pick it when the
first hot path moves into Rust. Whether the native extension or the Python fallback serves a request, stdout, stderr, the exit status, and the file
effects of `--fix` and `--dry` stay identical; DEP 6 makes this an explicit contract (see the [Contracts](#contracts) section below).

## Where the Rust code lives

The future Rust crate will live inside this repository as a maturin "mixed" project: `Cargo.toml` at the repository root and Rust sources under `src/`,
the default mixed layout that maturin documents (see the [project-layout reference](https://www.maturin.rs/project_layout) cited by {doc}`dep_6`). The
`src/` directory is unused today — the only code directories are `deadcode/`, `tests/`, `docs/`, and `enhancement_proposals/` — so the layout introduces
no collision. Hatchling's `include = ["**/*.py"]` setting in `pyproject.toml:56-58` keeps `Cargo.toml` and `src/` out of the fallback wheel, which
preserves the pure-Python fallback guarantee: the universal wheel remains Python-only no matter what lands in `src/`.

## Building the package

Two build paths will produce wheels from the same source tree and the same version. Native wheels are built with `maturin` and `pyo3` using the
`abi3-py310` stable ABI, which matches the project's Python 3.10 floor (`pyproject.toml:9`) and lets one native wheel serve every Python version from
3.10 up on a given platform. The universal `py3-none-any` fallback wheel continues to be built by the existing hatchling backend from the same source
tree and the same version, so pip always has an OS-independent artifact to install. A Rust toolchain is required only for native builds, never for
installing deadcode or for building the fallback wheel. The platform list of the release matrix — which platforms get native wheels — is fixed by the
future implementation task, not by this page; {doc}`dep_6` deliberately does not enumerate it and no existing repository file can derive it.

## Publishing to PyPI

Today the release path is manual: `make publish` (`Makefile:19-27`) clears `dist/`, runs `hatch build` and `uv publish`, creates the `v$(VERSION)` tag
after the upload, and triggers the Read the Docs builds for the new tag, `stable`, and `latest` via the Read the Docs API. The Phase 3 packaging change
described in {doc}`dep_6` extends this flow: build native wheels with maturin for the matrix platforms and the fallback wheel with hatchling from the
same tree and version, then upload both wheel families of the same version together so pip always finds an installable artifact — a native wheel where
one exists for the platform, the universal wheel otherwise. The fallback wheel is published for every release even when a native build fails, so an
unsupported platform can never fall through to a source build. The Cargo dependency and AGPLv3 licence audit is added alongside the existing Python
audit. The tag and Read the Docs steps stay as they are today; the tag is created after the upload today, and any reordering of those steps is a
decision for the Phase 3 packaging task, not for this documentation.

## Contracts

The contracts below constrain the Rust work. Each is stated with the file or section where it is fixed today.

- **Identical CLI output, exit status, and `--fix`/`--dry` file effects.** Fixed by {doc}`dep_6`'s contract bullets and implemented through the
  `deadcode` console script declared in `pyproject.toml:39-40`; any observable difference between the native and Python paths fails the gate.
- **AGPLv3-compatible crates with a Cargo audit alongside the Python audit.** Fixed by `LICENSE`, the AGPLv3 classifier in `pyproject.toml:13`, the
  implementation notes of {doc}`dep_6`, the audit targets in the `Makefile`, and `.github/workflows/vulnerability-audit.yml`.
- **Python 3.10 floor and `abi3-py310`.** Fixed by `requires-python` in `pyproject.toml:9`, the CI matrix of Python 3.10–3.15, and {doc}`dep_6`.
- **Universal-wheel fallback and the OS-independent claim.** Fixed by the `Operating System :: OS Independent` classifier in `pyproject.toml:14` and the
  scope of {doc}`dep_6`: a change that breaks installation on platforms without a native wheel is not acceptable.
- **The 100% changed-line coverage gate and strict mypy apply to Python code only.** Fixed by the `coverage-new` target (`Makefile:63-70`) and the
  strict mypy configuration (`pyproject.toml:167-176`), both of which scope to `deadcode/*.py`; they remain in force for the Python fallback and are not
  extended to Rust sources by this page.
- **The pre-commit hook stays installable everywhere via the fallback wheel.** Fixed by `.pre-commit-hooks.yaml` and verified by `make hook-test`, which
  installs the hook from the repository build.

## Relationship to DEP 6 and the staged plan

{doc}`dep_6` structures the Rust effort in four stages: Phase 0 adds the benchmark corpus and records the baseline, Phase 1 optimises the Python
implementation, Phase 2 moves measured hot paths into Rust one at a time, and Phase 3 changes packaging and release so both wheel families reach PyPI.
This page precedes all of them: it documents the integration, storage, build, and publishing decisions that Phase 3 will implement, so the future
implementation task can pick up {doc}`dep_6` plus this page without re-deriving the packaging plan.

## What is out of scope

This documentation adds no Rust code, no `Cargo.toml`, no maturin configuration, no benchmark harness, no CI change, and no packaging change — the same
boundary {doc}`dep_6`'s scope list draws for the proposal itself. The follow-up implementation task starts at the Phase 0 benchmark corpus, then
continues with Phase 1 Python optimisation, then Phase 2 acceleration and Phase 3 packaging using the flow this page documents. The page makes no
performance or speedup claim of any kind: {doc}`dep_6` prohibits claiming a speedup before the Phase 0 benchmark exists.

## References

- DEP 6, "Improving performance with a Rust implementation": {doc}`dep_6`
- Maturin guide: https://www.maturin.rs/
- Maturin bindings and `abi3-py310`: https://www.maturin.rs/bindings
- Maturin project layout: https://www.maturin.rs/project_layout
- pydantic-core packaging as prior art: https://github.com/pydantic/pydantic-core/blob/main/pyproject.toml
- watchfiles packaging as prior art: https://github.com/samuelcolvin/watchfiles/blob/main/pyproject.toml
