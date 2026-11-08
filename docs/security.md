# Security

`deadcode` audits its own pinned dependencies for known vulnerabilities: the runtime set from `requirements.txt` and the development set from
`requirements-dev.txt`. Dependency audit is the scope here; the analyser itself does not process untrusted input beyond the files it parses.

## What runs and when

The `Vulnerability audit` workflow lives in `.github/workflows/vulnerability-audit.yml` and runs:

- on every pull request targeting `main`,
- on every push to `main`,
- on a weekly schedule, `17 4 * * 1` (Monday 04:17 UTC),
- on manual dispatch through `workflow_dispatch`.

It has two jobs:

- `runtime-dependencies` runs on Python 3.10 and audits `requirements.txt` with `make audit-runtime`.
- `development-dependencies` runs a matrix of Python `["3.10", "3.15"]` and audits `requirements-dev.txt` with `make audit-development`.
  The Python 3.10 entry is `continue-on-error` because of the accepted exception described below.

## How to read a finding

`pip-audit` prints one row per advisory, with these columns:

- the distribution name,
- the installed or pinned version,
- the advisory ID and any alias (for example a `GHSA-…` or `CVE-…` identifier),
- the versions that fix the finding.

A non-zero exit status means at least one finding was reported. The affected dependency is pinned in `pyproject.toml` for development
installations and in `requirements-dev.txt` for the locked environment.

## How to fix a finding

Bump the constraint in `pyproject.toml`, then regenerate the locks and review the result:

```bash
make compile
git diff requirements.txt requirements-dev.txt
```

Alternatively merge the Dependabot pull request. Dependabot edits the lock files directly, so the lock-parity rule applies: if the pull
request edits only the lock files, confirm that `make compile` reproduces the same pins; otherwise regenerate the locks and commit those
instead of the Dependabot edit. Every Dependabot pull request must keep the `Test` workflow green before it is merged.

## Reproduce locally

From the repository root, with `.venv` created by `make .venv`:

```bash
make audit
make audit-runtime
make audit-development
```

The aggregate target runs the runtime audit first and only then the development audit, so a runtime finding stops the run. The same commands
can be called without `make`:

```bash
.venv/bin/pip-audit --no-deps --disable-pip -r requirements.txt
.venv/bin/pip-audit --no-deps --disable-pip -r requirements-dev.txt
```

To confirm that a finding makes the command fail, audit a known vulnerable pin in a temporary file. The expected result is
`Found 17 known vulnerabilities` and exit status `1`:

```bash
printf 'filelock==4.1.0\n' > /tmp/vulnerable-requirements.txt
.venv/bin/pip-audit --no-deps --disable-pip -r /tmp/vulnerable-requirements.txt
```

## Accepted exception: filelock on Python 3.10

`filelock==4.1.0` is pinned for `python_full_version < '3.11'`, and the fixed release `4.2.1` requires Python `>= 3.11`. On Python 3.10 the
development audit therefore reports 17 advisories, and the Python 3.10 matrix entry is marked `continue-on-error`. The exception is never
suppressed with `--ignore-vuln`. It ends when a Python 3.10-compatible fixed release exists or when Python 3.10 support is dropped.

## Repository settings for maintainers

Dependabot alerts, Dependabot security updates and secret scanning are repository settings, not files in the repository. These commands are
idempotent and need a maintainer with admin scope; each one is followed by the read-back that verifies it.

Enable Dependabot alerts:

```bash
gh api --method PUT repos/albertas/deadcode/vulnerability-alerts
gh api repos/albertas/deadcode/vulnerability-alerts
```

The read-back returns HTTP `204` when alerts are enabled.

Enable Dependabot security updates:

```bash
gh api --method PUT repos/albertas/deadcode -F 'security_and_analysis[dependabot_security_updates][status]=enabled'
gh api repos/albertas/deadcode --jq '.security_and_analysis.dependabot_security_updates.status'
```

The read-back prints `enabled`.

Enable secret scanning:

```bash
gh api --method PUT repos/albertas/deadcode -F 'security_and_analysis[secret_scanning][status]=enabled'
gh api repos/albertas/deadcode --jq '.security_and_analysis.secret_scanning.status'
```

The read-back prints `enabled`. Recent GitHub plans may enable secret scanning by default; the command still converges on the desired state.

## Rolling back

Each step is reversible without touching application code:

- revert the slice commits with `git revert`,
- delete `.github/dependabot.yml` to stop automatic update pull requests,
- disable each setting with the inverse command:

```bash
gh api --method DELETE repos/albertas/deadcode/vulnerability-alerts
gh api --method PUT repos/albertas/deadcode -F 'security_and_analysis[dependabot_security_updates][status]=disabled'
gh api --method PUT repos/albertas/deadcode -F 'security_and_analysis[secret_scanning][status]=disabled'
```

The read-backs from the previous section confirm the disabled state.
