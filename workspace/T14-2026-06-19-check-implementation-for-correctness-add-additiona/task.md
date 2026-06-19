# Task

Audit the `deadcode` package implementation for correctness — focusing on
unused-name detection, the fix/removal pipeline, and ignore/noqa handling — to
find places where it produces wrong results (false positives, false negatives,
or incorrect edits). Add unit test cases that pin down the correct expected
behavior for these scenarios, then update the implementation so all the new and
existing tests pass.
