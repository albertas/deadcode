# Performance

## What this page covers

This page reviews the efficiency of deadcode's implementation and explains how the cost of the analysis grows with the size of the input. The review walks
through the analysis pipeline stage by stage, names the source files on the hot path the way the {doc}`features` page cites paths, and reports where the
cost stays linear and where it can grow faster. The primary quantity on this page is `n`, the total amount of source code processed, measured in lines of
code across the analysed files — the same framing the {doc}`open_source_experiment` page uses when it asks whether runtime grows roughly linearly with
lines of code. No benchmark results exist yet: the {doc}`open_source_experiment` page defines the measurement procedure for a future experiment, and the
efficiency review below reports the structure of the cost, not measured timings at scale.

## Efficiency review findings

The findings below come from reading the implementation of the analysis pipeline. Each finding names the concrete source file on the hot path.

**(a) The analysis is a single pass over the discovered files.** `find_unused_names` in `deadcode/actions/find_unused_names.py` builds one `DeadCodeVisitor`
and visits every discovered file once. Per file, the visitor reads the content, parses the `# noqa` comments with `deadcode/visitor/noqa.py`, calls
`ast.parse` once, and traverses the resulting tree, so a default run reads and parses each file a single time.

**(b) The module-export collection parses every file a second time.** `_collect_module_exports` in `deadcode/visitor/dead_code_visitor.py` re-reads and
re-parses every discovered file with a second `ast.parse` call before the main traversal starts, so the pipeline performs two full parse passes over the
input where one would do.

**(c) Cross-module bare-name usage resolution can cost O(D × M) in the worst case.** When a `name` is used as a bare name in another module,
`is_name_used_in_module` in `deadcode/visitor/dead_code_visitor.py` iterates every module's bare usages, and `_resolve_bare_usage` follows import re-export
chains with a cycle-guarded frontier search over the `import_edges` graph. Here `D` is the number of detected definitions and `M` the number of modules
(both are defined below), so the worst case grows with the product of the two rather than with `n` alone.

**(d) The `--fix` and `--dry` path merges overlapping code parts quadratically per file.** `merge_overlaping_file_parts` in
`deadcode/actions/merge_overlaping_file_parts.py` compares every removal part with every other part of a file to merge overlapping ranges — the function's
own comment declares the algorithm O(n^2) — so the fix path scales with the square of the number of parts per file.

**(e) Pattern matching scales with the number of configured ignore patterns.** `deadcode/visitor/ignore.py` matches names and paths with `fnmatch`, and the
visitor in `deadcode/visitor/dead_code_visitor.py` applies the configured ignore patterns per node and per definition, so every additional `--ignore-*`
pattern multiplies the per-item matching work.

**(f) Comment handling tokenises the file once and parses commented-out code candidates.** `_collect_commented_out_code` in
`deadcode/visitor/dead_code_visitor.py` runs the `tokenize` module over each file once, and for every comment candidate that looks like code it attempts up
to two `ast.parse` calls (one in expression mode, one in statement mode) to decide whether the comment is commented-out code.

### A one-off profiling sample

DEP 6 (`enhancement_proposals/dep_6.md`) records a one-off `cProfile` sample of deadcode run on its own source: 912,678 function calls in 0.327 seconds over
29 files, with the visitor traversal taking 0.164 seconds, the duplicate module-export parse taking 0.058 seconds, and comment tokenisation taking 0.027
seconds. This is a one-off sample, not a baseline: it measured one codebase with one interpreter, and no benchmark suite or baseline exists yet (see
{doc}`open_source_experiment` and `enhancement_proposals/dep_6.md`). No speedup numbers can be derived from it.

## Algorithm complexity

This section expresses the cost of each pipeline stage in O notation. Every claim is tied to the stage and the source file named in the
[efficiency review findings](#efficiency-review-findings) section. The primary quantity is `n`, the total amount of source code processed, measured in lines
of code across the analysed files. Some stages are driven by other quantities, which are named once and used per stage:

- `F` — the number of Python files discovered.
- `N` — the number of AST nodes across the parsed files.
- `D` — the number of detected `definition`s.
- `U` — the number of usages reported as findings.
- `M` — the number of modules in the analysed codebase.
- `P` — the number of configured ignore patterns.

| Stage | Cost | Source files |
|---|---|---|
| File discovery | `O(F)` | `deadcode/actions/find_python_filenames.py`, called from `deadcode/cli.py` |
| Per-file reading, `noqa` scan, parsing, and comment scanning | `O(n)` | `deadcode/actions/find_unused_names.py`, `deadcode/visitor/noqa.py`, `deadcode/visitor/dead_code_visitor.py` |
| AST traversal with per-node and per-`definition` ignore matching | `O(N × P)` | `deadcode/visitor/dead_code_visitor.py`, `deadcode/visitor/ignore.py` |
| Unused-item pass with cross-module bare-name resolution | `O(D)`, worst case `O(D × M)` | `deadcode/visitor/dead_code_visitor.py` |
| Report assembly | `O(U log U)` for the final sort | `deadcode/visitor/dead_code_visitor.py` |
| `--fix` and `--dry` overlap merge | `O(p²)` per file, with `p` the number of removal parts of that file | `deadcode/actions/merge_overlaping_file_parts.py` |

### What stays linear in practice

In practice, a default run behaves linearly with constant factors: each file is read and parsed once in the main traversal pass (finding (a)), the
`definition` lists stay flat, and the usage checks are set-membership lookups rather than scans. The exceptions are the super-linear paths reported in the
[efficiency review findings](#efficiency-review-findings): the duplicate module-export parse (finding (b)), the worst-case `O(D × M)` cross-module bare-name
resolution (finding (c)), the quadratic `--fix` overlap merge (finding (d)), the per-item pattern matching that grows with the number of configured ignore
patterns (finding (e)), and the per-candidate `ast.parse` attempts in comment handling (finding (f)).

No benchmark baseline exists yet, so none of these costs has been measured at scale: the {doc}`open_source_experiment` page defines the measurement
procedure for a future experiment, and [DEP 6](dep_6.md) (an include of `enhancement_proposals/dep_6.md`) records the optimisation plan and its one-off
profiling sample. This page
makes no performance claims.
