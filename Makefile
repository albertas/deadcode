.PHONY: check publish test ruff fix mypy black deadcode

ifndef VERBOSE
  MAKEFLAGS += --no-print-directory
endif

check: test ruff mypy black deadcode

venv:
	python3.8 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements-dev.txt --use-pep517
	venv/bin/pip install -e .

publish: venv
	rm -fr dist/*
	venv/bin/hatch build
	venv/bin/hatch publish

test: venv
	venv/bin/pytest -vv $(PYTEST_ME_PLEASE)

ruff: venv
	venv/bin/ruff check deadcode tests

fix: venv
	venv/bin/ruff deadcode tests --fix

mypy: venv
	venv/bin/mypy deadcode

black: venv
	venv/bin/black deadcode tests

deadcode: venv
	venv/bin/deadcode deadcode tests -v
