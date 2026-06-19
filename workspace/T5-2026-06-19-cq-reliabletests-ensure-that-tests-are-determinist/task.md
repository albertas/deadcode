# Task

Make the `deadcode` test suite deterministic and fast. Tests should run in
parallel via pytest-xdist using all-but-one available cores, and unit tests
should be mocked so they don't depend on real filesystem state, the current
working directory, or external services (only genuine end-to-end tests may use
real resources). The goal is reliable, low-latency test runs.
