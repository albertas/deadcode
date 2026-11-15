# Performance

## What this page covers

This page reviews the efficiency of deadcode's implementation and explains how the cost of the analysis grows with the size of the input. The review walks
through the analysis pipeline stage by stage, names the source files on the hot path the way the {doc}`features` page cites paths, and reports where the
cost stays linear and where it can grow faster. The primary quantity on this page is `n`, the total amount of source code processed, measured in lines of
code across the analysed files — the same framing the {doc}`open_source_experiment` page uses when it asks whether runtime grows roughly linearly with
lines of code. The Benchmark section reports measured end-to-end wall clock, the isolated read stage, the parse-stage share, and peak memory on two corpora.

## Efficiency review findings

The findings below come from reading the implementation of the analysis pipeline. Each finding names the concrete source file on the hot path.

**(a) The analysis reads each file once and parses each file once.** `visit_abstract_syntax_trees` in `deadcode/visitor/dead_code_visitor.py` calls
`read_python_files_sync` from `deadcode/actions/read_python_files.py`, which reads every discovered file exactly once: small corpora are read as one
synchronous batch, and larger corpora go through the `asyncio` chunked read stage. The main loop then calls `ast.parse` once per successfully parsed file,
and that single tree feeds both module-export collection and the AST
traversal. `find_unused_names` in `deadcode/actions/find_unused_names.py` builds one `DeadCodeVisitor` and visits every discovered file once, and the
`# noqa` comments are parsed from the same bytes returned by the read stage.

**(b) There is no second module-export read or parse pass.** Module exports are registered from the tree that the main pass already produced, so the
pipeline no longer opens or parses a file for export collection before the traversal starts. A file whose `type_comments=True` parse fails is retried once
with a plain `ast.parse` so that export collection still mirrors the historical behaviour, but that retry only happens for files that fail to parse.

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

DEP 6 (`enhancement_proposals/dep_6.md`) records a one-off `cProfile` sample of an older deadcode pipeline run on its own source: 912,678 function calls in
0.327 seconds over 29 files, with the visitor traversal taking 0.164 seconds, the since-removed second parse pass taking 0.058 seconds, and comment
tokenisation taking 0.027 seconds. This is a one-off sample of a different codebase state, not a baseline: it measured one codebase with one interpreter.
The Benchmark section below is the reproducible measurement for the current pipeline.

## Benchmark

### Environment and corpora

- CPython 3.10.22, GIL build, Linux 7.0.0 x86_64, 16 logical CPUs, 30 GiB RAM, warm page cache, otherwise idle machine.
- Baseline: commit `889149c` (the pull-request base) in a detached worktree at `/tmp/deadcode-baseline`.
- Feature: the branch that removes the second parse pass and reads files through `deadcode/actions/read_python_files.py`.
- `deadcode/` — the repository's own package, 32 Python files, 116,349 bytes.
- `/tmp/django-src/django` — a Django source checkout with 909 Python files, 5,958,239 bytes, outside version control in this environment.

The harness is `benchmarks/benchmark_pipeline.py`; it uses only the standard library, never imports `deadcode` in its own process, runs one warmup and
three timed child runs per corpus, and reports the median wall clock with `time.perf_counter` plus the peak child RSS from `resource.getrusage`. Baseline
and feature runs use the same interpreter and dependencies; the baseline run points the child at the baseline worktree with `--cwd` and `-m deadcode.cli`,
so the baseline package is imported while the `.venv` supplies the dependencies. See `benchmarks/README.md` for the exact commands.

### End-to-end results

Medians of three timed runs after one warmup, one paired run of the commands in `benchmarks/README.md`:

| Corpus | Files | Baseline median | Feature median | Change | Baseline peak RSS | Feature peak RSS |
|---|---|---|---|---|---|---|
| `deadcode/` | 32 | 206.1 ms | 197.2 ms | 1.05x faster (-8.9 ms) | 24.1 MB | 24.4 MB |
| `/tmp/django-src/django` | 909 | 7,710.4 ms | 7,318.7 ms | 1.05x faster (-391.7 ms) | 102.9 MB | 111.1 MB |

Three interleaved baseline/feature pairs on the same machine gave 7,265–7,721 ms for the baseline on Django and 7,289–7,331 ms for the feature branch; the
`deadcode/` pairs ranged 204.2–207.2 ms baseline and 194.9–199.6 ms feature. Absolute values move with machine load, but the ordering is stable: the feature
branch is about 1.05x faster on both corpora.

### Isolated read stage

Medians of seven in-process repetitions of reading the same file lists, comparing a plain sequential loop with `read_python_files_sync` (a synchronous batch
below the file threshold, the `asyncio` chunked reader with eight workers above it):

| Corpus | Bytes | Sequential loop | `read_python_files_sync` | Read-stage cost |
|---|---|---|---|---|
| `deadcode/` (32 files) | 116,349 | 0.10 ms | 0.10 ms | +0.00 ms |
| `/tmp/django-src/django` (909 files) | 5,958,239 | 8.78 ms | 38.81 ms | +30.03 ms |

The small corpus stays on the sequential path, so the event loop and worker threads add nothing. On Django the chunked reader costs about 30 ms — 0.4% of
the run — because the operating system serves a warm page cache quickly and the worker threads add scheduling overhead. The measured read cost is small but
real; it does not become a parallel speedup because reading is already fast relative to parsing.

### Parse-stage share

Instrumenting `ast.parse` in-process (timers wrapped around the call, so these runs exclude interpreter startup) gives a median parse share of 8.4% on
`deadcode/` (12.4 ms of 147.2 ms) and 9.8% on Django (670.4 ms of 6,811.3 ms) across three runs. A default run of the 32-file corpus issues a median of 60
`ast.parse` calls and the Django corpus a median of 4,536, because comment candidates and type comments add calls beyond the one per file; those calls sit
inside the measured share.

### What the numbers mean (decision D9)

Async reads contribute at most noise or a small cost: the chunked read stage saves no wall clock and adds about 30 ms on Django, while the 32-file corpus
stays below `ASYNC_READ_MIN_FILES` and is read as one sequential batch, so it pays no event-loop or worker-thread cost. The net gain comes from removing the
second parse pass, not from parallel parsing. On Django the removed pass is worth roughly 390–490 ms, comfortably more than the read overhead, so the
end-to-end result is about 1.05x faster. On the 32-file corpus the removed pass outweighs the read stage, and the run is about 9 ms faster rather than
slower. `ast.parse` holds the GIL in CPython, so parsing is not offloaded to threads and no parallel parse gain is claimed.

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
| Reading every discovered file once | `O(F)` | `deadcode/actions/read_python_files.py`, called from `deadcode/visitor/dead_code_visitor.py` |
| Per-file `noqa` scan, parsing, and comment scanning | `O(n)` | `deadcode/actions/find_unused_names.py`, `deadcode/visitor/noqa.py`, `deadcode/visitor/dead_code_visitor.py` |
| AST traversal with per-node and per-`definition` ignore matching | `O(N × P)` | `deadcode/visitor/dead_code_visitor.py`, `deadcode/visitor/ignore.py` |
| Unused-item pass with cross-module bare-name resolution | `O(D)`, worst case `O(D × M)` | `deadcode/visitor/dead_code_visitor.py` |
| Report assembly | `O(U log U)` for the final sort | `deadcode/visitor/dead_code_visitor.py` |
| `--fix` and `--dry` overlap merge | `O(p²)` per file, with `p` the number of removal parts of that file | `deadcode/actions/merge_overlaping_file_parts.py` |

### What stays linear in practice

In practice, a default run behaves linearly with constant factors: each file is read once by the read stage and parsed once in the main traversal pass
(finding (a)), the `definition` lists stay flat, and the usage checks are set-membership lookups rather than scans. The exceptions are the super-linear
paths reported in the [efficiency review findings](#efficiency-review-findings): the worst-case `O(D × M)` cross-module bare-name resolution (finding (c)),
the quadratic `--fix` overlap merge (finding (d)), the per-item pattern matching that grows with the number of configured ignore patterns (finding (e)), and
the per-candidate `ast.parse` attempts in comment handling (finding (f)).

The Benchmark section is the reproducible baseline for future optimisation work. [DEP 6](dep_6.md) (an include of `enhancement_proposals/dep_6.md`) records
the optimisation plan and its one-off profiling sample.
