# Research Questions

## Context
Focus on the `deadcode/` Python package: the AST-visitor classes under
`deadcode/visitor/`, the shared data structures in `deadcode/data_types.py`,
the analysis pipeline in `deadcode/actions/` (parsing, finding unused names,
fixing/showing results) and its entry point in `deadcode/cli.py`, plus the
helpers under `deadcode/utils/`. Also note the type-checking configuration in
`pyproject.toml` and the `Justfile`.

## Questions
1. How are the visitor classes in `deadcode/visitor/find_unused_code_visitor.py`
   and `deadcode/visitor/fix_unused_code_visitor.py` structured — what base
   class do they subclass, which `visit_*` methods do they define, and what
   node types do those methods actually operate on at runtime?
2. What data structures are defined in `deadcode/data_types.py` (e.g. `CodeItem`,
   `Part`, and related types), and how are their fields and collection types
   declared and used?
3. Trace the data flow from `parse_abstract_syntax_tree` through
   `find_unused_names`, `fix_or_show_unused_code`, and `cli.py`: what values
   are produced and consumed at each boundary, and what are the declared
   return-type and parameter-type annotations at those boundaries?
4. What helper functions live under `deadcode/utils/` (e.g. `remove_from_list`,
   `flatten_lists`, `print_ast`, `lines`) and `deadcode/actions/remove_file_parts_from_content.py`,
   and how are their parameters, return values, and any generics/containers
   annotated?
5. What type-annotation conventions are already established across the
   `deadcode/` package (use of `typing`/`collections.abc`, generics, dataclass
   field annotations, forward references), and how are uninferable locals and
   module-level constants annotated?
6. How is mypy configured for this project (the `[tool.mypy]` section in
   `pyproject.toml` and the `check-typecheck`/`typecheck` recipes in the
   `Justfile`), and which strictness flags are in effect?
