lifecycle:
  @uv pip sync requirements-dev.txt
  @uv pip install -e .[test]
  @count=0; while uv run lifecycle --max-tasks 1 --prior-tasks "$count"; do count=$((count + 1)); done

sync:
  @uv pip sync requirements-dev.txt
  @uv pip install -e .[test]

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
