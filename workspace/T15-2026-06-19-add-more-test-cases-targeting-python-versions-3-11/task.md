# Task

Add test cases that exercise the `deadcode` tool against syntax and language
features specific to Python 3.11, 3.12, 3.13, 3.14 (and 3.15 if available), and
fix any implementation incompatibilities so the tool parses and analyzes code
correctly when run on each of those interpreter versions.

The goal is to guarantee that dead-code detection works across the full range of
supported Python versions (the project declares `requires-python = ">= 3.11"`
and a CI matrix of 3.11–3.14), catching version-dependent AST or runtime
breakage before release.
