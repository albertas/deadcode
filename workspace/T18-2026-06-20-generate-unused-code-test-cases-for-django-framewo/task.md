# Task

Generate framework-specific test cases that exercise Deadcode against common Django
code patterns (models, views, URL configs, admin, signals, management commands,
settings, app configs, etc.), following the existing `tests/frameworks/` precedent
set by the FastAPI, SQLAlchemy, and Alembic scenario tests. The goal is to confirm
Deadcode correctly distinguishes genuinely unused code from Django constructs that
are used implicitly/dynamically, and to extend or adjust Deadcode's detection or
suppression behaviour where it currently mishandles Django patterns.
