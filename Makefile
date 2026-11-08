.PHONY: compile publish readthedocs check fix lint fixlint format mypy deadcode audit test coverage-new pre-commit hook-test

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
	@test -n "$(READTHEDOCS_API_TOKEN)" || { \
		echo "publish: set READTHEDOCS_API_TOKEN to a Read the Docs API token with build permissions" >&2; \
		exit 1; \
	}
	rm -fr dist/*
	.venv/bin/hatch build
	.venv/bin/uv publish

	git tag -a $(VERSION) -m "deadcode $(VERSION)"
	git push origin tag $(VERSION)

	$(MAKE) readthedocs

# Rebuild the released version, stable and latest documentation on Read the Docs.
readthedocs:
	@test -n "$(READTHEDOCS_API_TOKEN)" || { \
		echo "readthedocs: set READTHEDOCS_API_TOKEN to a Read the Docs API token with build permissions" >&2; \
		exit 1; \
	}
	@set -e; \
	api="$(READTHEDOCS_API_URL)"; \
	auth="Authorization: Token $(READTHEDOCS_API_TOKEN)"; \
	request() { \
		curl --fail-with-body --silent --show-error --retry 5 --retry-delay 2 \
			--header "$$auth" "$$@"; \
		sleep 2; \
	}; \
	request --request POST "$$api/sync-versions/" >/dev/null; \
	delay=2; \
	for attempt in 1 2 3 4 5 6; do \
		if request "$$api/versions/$(VERSION)/" >/dev/null 2>&1; then break; fi; \
		if [ "$$attempt" -eq 6 ]; then \
			echo "readthedocs: version $(VERSION) did not appear; check the Read the Docs Git integration" >&2; \
			exit 1; \
		fi; \
		echo "readthedocs: waiting $${delay}s for version $(VERSION)" >&2; \
		sleep "$$delay"; \
		delay=$$((delay * 2)); \
	done; \
	if request "$$api/versions/$(VERSION)/" | grep -q '"active": true'; then \
		request --request POST "$$api/versions/$(VERSION)/builds/" >/dev/null; \
	else \
		request --request PATCH --header 'Content-Type: application/json' \
			--data '{"active": true}' "$$api/versions/$(VERSION)/" >/dev/null; \
	fi; \
	delay=2; \
	for attempt in 1 2 3 4 5 6; do \
		if request "$$api/versions/stable/" | grep -q "\"ref\": \"$(VERSION)\""; then break; fi; \
		if [ "$$attempt" -eq 6 ]; then \
			echo "readthedocs: stable does not point at $(VERSION)" >&2; \
			exit 1; \
		fi; \
		sleep "$$delay"; \
		delay=$$((delay * 2)); \
	done; \
	request --request POST "$$api/versions/stable/builds/" >/dev/null; \
	request --request POST "$$api/versions/latest/builds/" >/dev/null; \
	echo "readthedocs: triggered builds for $(VERSION), stable and latest"

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

audit: .venv
	.venv/bin/pip-audit --skip-editable

sync: .venv
	uv pip sync requirements-dev.txt
	uv pip install -e .[test]

compile:
	uv pip compile -U -q pyproject.toml -o requirements.txt
	uv pip compile -U -q --universal --all-extras pyproject.toml -o requirements-dev.txt
