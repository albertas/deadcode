.PHONY: compile publish readthedocs check fix lint fixlint format mypy deadcode audit audit-runtime audit-development test coverage-new pre-commit hook-test

check: test lint mypy deadcode
fix: format fixlint

PYTHON_VERSION ?= 3.10
BASE_BRANCH ?= origin/main
PYTEST_XDIST_WORKERS ?= $(shell .venv/bin/python -c 'import os; print(max(1, (os.cpu_count() or 2) - 1))')

.venv:
	@command -v uv >/dev/null || pip install uv
	uv venv -p $(PYTHON_VERSION) .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

VERSION := $(shell .venv/bin/hatch version)
READTHEDOCS_API_URL ?= https://app.readthedocs.org/api/v3/projects/deadcode

publish: .venv
	rm -fr dist/*
	.venv/bin/hatch build
	.venv/bin/uv publish

	git tag -a v$(VERSION) -m "deadcode $(VERSION)"
	git push origin tag v$(VERSION)

	$(MAKE) readthedocs

# Rebuild the released version, stable and latest documentation on Read the Docs.
# Read the Docs registers a new tag asynchronously: right after the tag push the
# version may not exist yet, and its builds endpoint answers 404. Sync the
# versions and wait for each one to appear before triggering its build. The
# documentation is not part of the published package, so an unreachable version
# only prints a warning; rerun `make readthedocs` once Read the Docs has synced.
readthedocs: .venv
	@if [ -z "$(READTHEDOCS_API_TOKEN)" ]; then \
		echo "readthedocs: set READTHEDOCS_API_TOKEN to a Read the Docs API token with build permissions; skipping" >&2; \
		exit 0; \
	fi; \
	api="$(READTHEDOCS_API_URL)"; \
	auth="Authorization: Token $(READTHEDOCS_API_TOKEN)"; \
	request() { \
		http_status=0; \
		http_code=$$(curl --fail-with-body --silent --show-error --retry 5 --retry-delay 2 --retry-connrefused \
			--header "$$auth" --header 'Accept: application/json' \
			--write-out '%{http_code}' --output /dev/null "$$@") || http_status=$$?; \
		sleep 2; \
		return "$$http_status"; \
	}; \
	trigger() { \
		version="$$1"; \
		delay=2; \
		attempt=1; \
		while [ "$$attempt" -le 7 ]; do \
			if request --request GET "$$api/versions/$$version/" \
				&& request --request POST "$$api/versions/$$version/builds/"; then \
				echo "readthedocs: triggered the '$$version' build"; \
				return 0; \
			fi; \
			if [ "$$http_code" = "401" ] || [ "$$http_code" = "403" ]; then \
				echo "readthedocs: Read the Docs rejected READTHEDOCS_API_TOKEN (HTTP $$http_code); skipping" >&2; \
				return 2; \
			fi; \
			if [ "$$attempt" -eq 7 ]; then \
				echo "readthedocs: could not trigger the '$$version' build" >&2; \
				return 1; \
			fi; \
			echo "readthedocs: waiting $${delay}s for version '$$version'" >&2; \
			sleep "$$delay"; \
			if [ "$$delay" -lt 30 ]; then delay=$$((delay * 2)); fi; \
			attempt=$$((attempt + 1)); \
		done; \
	}; \
	request --request POST "$$api/sync-versions/" || { \
		if [ "$$http_code" = "401" ] || [ "$$http_code" = "403" ]; then \
			echo "readthedocs: Read the Docs rejected READTHEDOCS_API_TOKEN (HTTP $$http_code); skipping" >&2; \
			exit 0; \
		fi; \
		echo "readthedocs: could not sync versions; waiting for new tags anyway" >&2; \
	}; \
	failed=0; \
	for version in "v$(VERSION)" stable latest; do \
		trigger "$$version"; \
		trigger_status=$$?; \
		if [ "$$trigger_status" -eq 2 ]; then failed=1; break; fi; \
		if [ "$$trigger_status" -ne 0 ]; then failed=1; fi; \
	done; \
	if [ "$$failed" -ne 0 ]; then \
		echo "readthedocs: some documentation builds were not triggered; rerun 'make readthedocs' once Read the Docs has synced the versions" >&2; \
	fi

test: .venv
	.venv/bin/pytest -vv -n $(PYTEST_XDIST_WORKERS) $(PYTEST_ME_PLEASE)

# Require 100% coverage for every line added or changed against the base branch.
coverage-new: test
	set -e; \
	merge_base=$$(git merge-base "$(BASE_BRANCH)" HEAD) || { \
		echo "coverage-new: $(BASE_BRANCH) is not available; fetch it first" >&2; \
		exit 1; \
	}; \
	git ls-files -z --others --exclude-standard -- deadcode | xargs -0 -r git add -N --; \
	diff_file=$$(mktemp); \
	trap 'rm -f "$$diff_file"' EXIT; \
	git diff "$$merge_base" > "$$diff_file"; \
	.venv/bin/python -m coverage xml --include='deadcode/*' -o coverage-new.xml; \
	.venv/bin/diff-cover coverage-new.xml --diff-file "$$diff_file" --fail-under=100

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

audit: audit-runtime audit-development

audit-runtime: .venv
	.venv/bin/pip-audit --no-deps --disable-pip -r requirements.txt

audit-development: .venv
	.venv/bin/pip-audit --no-deps --disable-pip -r requirements-dev.txt

sync: .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

# Resolve the dependencies to the newest versions allowed by pyproject.toml.
compile:
	uv pip compile -U -q pyproject.toml -o requirements.txt
	uv pip compile -U -q --universal --all-extras pyproject.toml -o requirements-dev.txt
