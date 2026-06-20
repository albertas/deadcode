lifecycle:
  @uv add --requirements requirements-dev.txt
  @count=0; while uv run lifecycle --max-tasks 1 --prior-tasks "$count"; do count=$((count + 1)); done

sync:
  @uv add --requirements requirements-dev.txt

lock:
  uv lock

test *args: sync
  uv run pytest -n "$(nproc --ignore=1)" {{args}}

format: sync
  uv run ruff format deadcode/ tests/

lint: sync
  uv run ruff check deadcode/ tests/

typecheck: sync
  uv run mypy deadcode/

check-format: sync
  uv run ruff format --check deadcode/ tests/

check-lint: sync
  uv run ruff check deadcode/ tests/

check-complexity: sync
  uv run ruff check --select C901 deadcode/ tests/

check-typecheck: sync
  uv run mypy deadcode/

check: check-format check-lint check-complexity check-typecheck test

audit: sync
  uv run pip-audit

deadcode: sync
  uv run deadcode deadcode/ tests/ -v

fixlint: sync
  uv run ruff check --fix deadcode/ tests/ --unsafe-fixes
  uv run deadcode deadcode/ tests/ --fix

fix: format fixlint

publish: sync
  rm -fr dist/*
  uv run hatch build
  uv run hatch -v publish

compile:
  uv pip compile -U -q --python 3.11 --no-strip-markers pyproject.toml -o requirements.txt
  uv pip compile -U -q --all-extras --python 3.11 --no-strip-markers pyproject.toml -o requirements-dev.txt
