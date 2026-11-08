.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test pre-commit hook-test

check: test lint mypy deadcode
fix: format fixlint

PYTHON_VERSION ?= 3.10
PYTEST_XDIST_WORKERS ?= $(shell .venv/bin/python -c 'import os; print(max(1, (os.cpu_count() or 2) - 1))')

.venv:
	@command -v uv >/dev/null || pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

VERSION := $(shell .venv/bin/hatch version)

publish: .venv
	rm -fr dist/*
	.venv/bin/hatch build
	.venv/bin/uv publish

	git tag -a $(VERSION) -m "deadcode $(VERSION)"
	git push origin tag $(VERSION)

test: .venv
	.venv/bin/pytest -vv -n $(PYTEST_XDIST_WORKERS) $(PYTEST_ME_PLEASE)

pre-commit: .venv
	.venv/bin/pre-commit run --all-files

hook-test: .venv
	.venv/bin/pre-commit try-repo . deadcode --all-files

lint: .venv
	.venv/bin/ruff check deadcode tests

fix: .venv
	.venv/bin/ruff check deadcode tests --fix

mypy: .venv
	.venv/bin/mypy deadcode

deadcode: .venv
	.venv/bin/deadcode deadcode tests -v

fixlint: .venv
	.venv/bin/ruff check --fix deadcode tests --unsafe-fixes
	.venv/bin/deadcode deadcode tests --fix

format: .venv
	.venv/bin/ruff format deadcode tests

audit: .venv
	.venv/bin/pip-audit --skip-editable

sync: .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

compile:
	uv pip compile -U -q pyproject.toml -o requirements.txt
	uv pip compile -U -q --universal --all-extras pyproject.toml -o requirements-dev.txt
