.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test lock

PYTHON_VERSION ?= 3.11

check: test lint mypy audit deadcode
fix: format fixlint

.venv:
	pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv add --requirements requirements-dev.txt


publish: .venv
	rm -fr dist/*
	.venv/bin/hatch build
	.venv/bin/hatch -v publish

test: .venv
	.venv/bin/pytest -n "$(shell nproc --ignore=1)" -vv $(PYTEST_ME_PLEASE)

lint: .venv
	.venv/bin/ruff check deadcode tests

fix: .venv
	.venv/bin/ruff deadcode tests --fix

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
	.venv/bin/pip-audit

sync: .venv
	uv add --requirements requirements-dev.txt

lock:
	uv lock

compile:
	uv pip compile -U -q --python 3.11 --no-strip-markers pyproject.toml -o requirements.txt
	uv pip compile -U -q --all-extras --python 3.11 --no-strip-markers pyproject.toml -o requirements-dev.txt
