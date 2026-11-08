.PHONY: compile publish check fix lint fixlint format mypy deadcode audit test pre-commit hook-test coverage-report coverage-matrix

check: test lint mypy deadcode
fix: format fixlint

PYTHON_VERSION ?= 3.10
PYTEST_XDIST_WORKERS ?= $(shell .venv/bin/python -c 'import os; print(max(1, (os.cpu_count() or 2) - 1))')
COVERAGE_ENVIRONMENTS ?= .venv .venv3*

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

coverage-report: .venv
	.venv/bin/pytest -q -n $(PYTEST_XDIST_WORKERS) $(PYTEST_ME_PLEASE)
	@.venv/bin/python -m coverage report --format=total --precision=2
	@.venv/bin/python -m coverage report --include='deadcode/*' --format=total --precision=2
	@.venv/bin/python -m coverage report --include='deadcode/*'

coverage-matrix:
	@found=0; \
	for environment in $(COVERAGE_ENVIRONMENTS); do \
		if [ ! -x "$$environment/bin/python" ]; then \
			echo "skipping $$environment (no python executable)"; \
			continue; \
		fi; \
		found=1; \
		echo "=== $$environment ==="; \
		"$$environment/bin/python" -c 'import sys; print(sys.version.split()[0])'; \
		workers=; \
		if "$$environment/bin/python" -c 'import xdist' >/dev/null 2>&1; then \
			workers="-n $(PYTEST_XDIST_WORKERS)"; \
		fi; \
		"$$environment/bin/pytest" -q $$workers $(PYTEST_ME_PLEASE) || exit 1; \
		echo "$$environment full-suite:"; \
		"$$environment/bin/python" -m coverage report --format=total --precision=2 || exit 1; \
		echo "$$environment package-only:"; \
		"$$environment/bin/python" -m coverage report --include='deadcode/*' --format=total --precision=2 || exit 1; \
	done; \
	if [ "$$found" -eq 0 ]; then \
		echo "error: no usable coverage environment found" >&2; \
		exit 1; \
	fi

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
