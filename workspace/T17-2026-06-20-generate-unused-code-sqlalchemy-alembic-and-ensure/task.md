# Task: SQLAlchemy + Alembic framework test cases

Add framework-specific scenario tests (under `tests/frameworks/`) that exercise
Deadcode against typical SQLAlchemy ORM and Alembic migration code, covering both
the false positives that framework conventions produce (e.g. ORM models, mapped
columns, dynamically-invoked migration functions and revision identifiers) and
the genuinely unused code that should still be reported.

Verify Deadcode correctly handles these patterns via its existing ignore options;
where the existing options or built-in rules are insufficient, extend the
implementation so the framework patterns can be suppressed while real dead code is
still detected. This mirrors the previously completed FastAPI work (T16).
