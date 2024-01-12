ifndef VERBOSE
  MAKEFLAGS += --no-print-directory
endif

check: venv
	cd deadcode && make check

venv:
	python3.8 -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements-dev.txt --use-pep517
	venv/bin/pip install -e .

publish: venv
	rm -fr dist/*
	venv/bin/hatch build
	venv/bin/hatch publish
