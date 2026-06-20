# Task

Audit the `deadcode` package's unused-code detection for correctness, focusing on
its ability to accurately identify unused Python definitions (variables, functions,
classes, imports, methods, attributes) across modern Python syntax (3.11+) and the
common frameworks it claims to support (Django, FastAPI, SQLAlchemy, Alembic).

The goal is to find correctness gaps — false positives (reporting used code as
unused) and false negatives (missing genuinely unused code) — in the detection
pipeline and its handling of modern language constructs, then back the findings
with test cases so they can be fixed and prevented from regressing.
