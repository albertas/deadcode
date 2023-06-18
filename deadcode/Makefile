check: test ruff mypy black deadcode

../venv:
	cd .. && make venv

publish: ../venv
	cd .. && make publish

test: ../venv
	../venv/bin/pytest $(PYTEST_ME_PLEASE)

ruff: ../venv
	../venv/bin/ruff .

fix: ../venv
	../venv/bin/ruff . --fix

mypy: ../venv
	../venv/bin/mypy .

black: ../venv
	../venv/bin/black .

deadcode: ../venv
	../venv/bin/deadcode . --exclude=tests
