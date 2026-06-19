# Task: Add test-coverage measurement and reach >= 95% coverage

Establish reliable test-coverage measurement for the `deadcode` package and
raise coverage to at least 95%, writing whatever additional tests are needed to
exercise currently-uncovered code paths. Coverage tooling (`pytest-cov`) is
already partly wired through `pyproject.toml`, so this work tightens the
configuration/threshold and closes coverage gaps rather than introducing the
capability from scratch.
