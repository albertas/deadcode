# Task

Make `just check-typecheck` (which runs `mypy deadcode/` in strict mode) pass
without errors. mypy currently reports 42 errors across 10 files; resolve them
by adding or correcting type hints in the source where possible, without
changing runtime behavior. The dominant clusters are AST-visitor method
signatures in `deadcode/visitor/` and a return-/argument-type contract mismatch
spanning `find_unused_names`, `fix_or_show_unused_code`, and `cli`.
