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

## Dependabot

Dependabot version updates are enabled for the repository and are configured in `.github/dependabot.yml`. They cover:

- the `pip` ecosystem, for the pinned runtime and development dependencies in `requirements.txt` and `requirements-dev.txt`;
- the `github-actions` ecosystem, for the actions pinned in `.github/workflows/`.

Both ecosystems check for updates weekly on Monday, timezone `UTC`. Minor and patch updates arrive as one grouped pull request per ecosystem
(`python-dependencies` for `pip`, `github-actions` for the actions), while major updates arrive as separate pull requests.

Dependabot alerts and Dependabot security updates are not enabled, so a fixed release is picked up either by the weekly version update or by the
`Vulnerability audit` workflow described above, not by an automatic security fix. The dependency graph is enabled and is the data source for these
checks.

A maintainer changes these three GitHub-side settings on the repository's Settings → Code security and analysis page.

## How to read and fix a finding

`pip-audit` prints one row per advisory: the distribution name, its version, the advisory ID and any alias (for example a `GHSA-…` or
`CVE-…` identifier), and the versions that fix it. A non-zero exit status means at least one finding was reported. The affected dependency
is pinned in `requirements-dev.txt` for the locked environment, while `pyproject.toml` declares it without a version constraint.

Regenerate the locks, which upgrades every dependency to its latest release, and review the result:

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
