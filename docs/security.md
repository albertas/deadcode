# Security

`deadcode` audits its pinned runtime (`requirements.txt`) and development (`requirements-dev.txt`) dependencies for known vulnerabilities with
`pip-audit`. The analyser itself does not process untrusted input beyond the files it parses.

## What runs and when

The `Vulnerability audit` workflow in `.github/workflows/vulnerability-audit.yml` runs:

- on every pull request targeting `main`,
- on every push to `main`,
- weekly on Sunday at 15:00 UTC,
- on manual dispatch through `workflow_dispatch`.

It has two jobs:

- `runtime-dependencies` runs on Python 3.10 and audits `requirements.txt` with `make audit-runtime`.
- `development-dependencies` runs on Python 3.10 and 3.15 and audits `requirements-dev.txt` with `make audit-development`. The Python 3.10
  audit step is `continue-on-error` because of the accepted exception below, so the job stays green while the advisories remain in the step log.

## How to read and fix a finding

`pip-audit` prints one row per advisory: the distribution name, its version, the advisory ID and any alias (for example a `GHSA-…` or
`CVE-…` identifier), and the versions that fix it. A non-zero exit status means at least one finding was reported. The affected dependency
is pinned in `pyproject.toml` for development installations and in `requirements-dev.txt` for the locked environment.

Bump the constraint in `pyproject.toml`, then regenerate the locks and review the result:

```bash
make compile
git diff requirements.txt requirements-dev.txt
```

Alternatively, merge the Dependabot pull request. If it edits only the lock files, confirm that `make compile` reproduces the same pins;
otherwise regenerate the locks. Every Dependabot pull request must keep the `Test` workflow green before it is merged.

## Reproduce locally

```bash
make audit
make audit-runtime
make audit-development
```

The same commands can be called without `make`:

```bash
.venv/bin/pip-audit --no-deps --disable-pip -r requirements.txt
.venv/bin/pip-audit --no-deps --disable-pip -r requirements-dev.txt
```

## Accepted exception: filelock on Python 3.10

`filelock==4.1.0` is pinned for `python_full_version < '3.11'`, while the fixed release `4.2.1` requires Python `>= 3.11`. On Python 3.10
the development audit therefore reports those advisories, and its step is marked `continue-on-error`. The exception is never suppressed with
`--ignore-vuln`. It ends when a Python 3.10-compatible fixed release exists or when Python 3.10 support is dropped.
