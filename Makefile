.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test

check: test lint mypy audit deadcode
fix: format fixlint

.venv:
	pip install uv
	uv venv -p 3.10 .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

VERSION := $(shell .venv/bin/deadcode --version);

publish: .venv
	rm -fr dist/*
	.venv/bin/hatch build
	.venv/bin/hatch -v publish

	git tag $(VERSION)
	git push $(VERSION)

test: .venv
	.venv/bin/pytest -vv $(PYTEST_ME_PLEASE)

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
	uv pip compile -U -q --all-extras pyproject.toml -o requirements-dev.txt
