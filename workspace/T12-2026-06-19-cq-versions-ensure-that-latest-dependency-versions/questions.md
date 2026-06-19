# Research Questions

## Context
Focus on how this Python project declares, resolves, locks, installs, and
audits its dependencies. Relevant artifacts include `pyproject.toml`, `uv.lock`,
`requirements.txt`, `requirements-dev.txt`, the `Justfile`, the `Makefile`, and
the GitHub Actions workflow under `.github/workflows/`.

## Questions
1. Where are runtime and development/test dependencies declared, and what
   version constraints (if any) are specified for each in `pyproject.toml`?
2. How are `requirements.txt` and `requirements-dev.txt` generated, and what
   commands or recipes (in the `Makefile`, `Justfile`, or elsewhere) regenerate
   or upgrade them? What role does the `-U`/upgrade flag play?
3. How is the dependency set locked and synced for development and CI — what is
   the relationship between `uv.lock`, the requirements files, and the
   `uv pip sync` / `uv pip install` steps in the `Justfile` and `Makefile`?
4. What custom or non-default package indexes are configured (e.g. the
   `[[tool.uv.index]]` entry), and how do they affect which package versions are
   resolved and from where?
5. How does the CI workflow install dependencies and run checks, and across
   which Python versions does it run? How could a dependency upgrade interact
   with that Python-version matrix and the project's `requires-python` setting?
6. What tooling exists for verifying dependency health and consistency (e.g.
   `pip-audit`, the `check` targets, `just check`), and how are these invoked?
