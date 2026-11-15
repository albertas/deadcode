# Performance

## What this page covers

This page reviews the efficiency of deadcode's implementation and explains how the cost of the analysis grows with the size of the input. The review walks
through the analysis pipeline stage by stage, names the source files on the hot path the way the {doc}`features` page cites paths, and reports where the
cost stays linear and where it can grow faster. The primary quantity on this page is `n`, the total amount of source code processed, measured in lines of
code across the analysed files — the same framing the {doc}`open_source_experiment` page uses when it asks whether runtime grows roughly linearly with
lines of code. The Benchmark section reports measured end-to-end wall clock, the isolated read stage, the parse-stage share, and peak memory on two corpora.

## Efficiency review findings

The findings below come from reading the implementation of the analysis pipeline. Each finding names the concrete source file on the hot path.

**(a) The analysis reads each file once and parses each file once, in bounded asynchronous chunks.** `visit_abstract_syntax_trees` is an `async def` in
`deadcode/visitor/dead_code_visitor.py`. It splits the discovered files into chunks of `READ_CHUNK_FILES` (32) entries with `chunk_filenames` from
`deadcode/actions/read_python_files.py`, then processes up to `DEFAULT_WORKERS` (2) chunks concurrently with `asyncio.gather`: each chunk is handed to a
worker thread that reads its files with `read_file_chunk` and parses every file once with `ast.parse`. The parsed chunks are consumed in input order and
each chunk is released before the next wave is read, so a directory of any size is streamed through a fixed-size window instead of being loaded into
memory up front. That single tree per file feeds both module-export collection and the AST traversal. `find_unused_names` in
`deadcode/actions/find_unused_names.py` runs the coroutine with `asyncio.run` on one `DeadCodeVisitor` and visits every discovered file once, and the
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

Medians of five timed runs after one warmup, one paired run of the commands in `benchmarks/README.md`:

| Corpus | Files | Baseline median | Feature median | Change | Baseline peak RSS | Feature peak RSS |
|---|---|---|---|---|---|---|
| `deadcode/` | 32 | 219.2 ms | 214.4 ms | 1.02x faster (-4.8 ms) | 24.0 MB | 28.5 MB |
| `/tmp/django-src/django` | 909 | 7,755.7 ms | 7,346.4 ms | 1.06x faster (-409.3 ms) | 102.9 MB | 122.8 MB |

Interleaved baseline/feature pairs on the same machine ranged 7,339–7,793 ms for the baseline on Django and 7,289–7,684 ms for the feature branch; the
`deadcode/` pairs ranged 202.7–227.0 ms baseline and 214.4–240.4 ms feature. Absolute values move with machine load, but the ordering is stable: the
feature branch is about 1.06x faster on Django and about level on the 32-file corpus.

### Chunk window and memory

The pipeline holds at most `DEFAULT_WORKERS × READ_CHUNK_FILES` files in flight: two chunks of 32 files, so 64 file contents and their parsed trees. That
window is what makes the async stage bounded: a 1 GB directory is never read into memory at once, it passes through 64-file windows. The cost of the window
is visible in the peak RSS column above: the feature branch uses about 4.5 MB more on the 32-file corpus and about 20 MB more on Django, because a worker
thread pool and up to 64 parsed trees exist at the same time. A smaller window trades memory back for fewer concurrent reads.

### Parse-stage share

Instrumenting `ast.parse` in-process (timers wrapped around the call, so these runs exclude interpreter startup) gives a median parse share of 10.5% on
`deadcode/` (14.6 ms of 138.9 ms) and 19.9% on Django (1,383 ms of 6,951 ms) across three runs. A default run of the 32-file corpus issues a median of 60
`ast.parse` calls and the Django corpus a median of 4,536, because comment candidates and type comments add calls beyond the one per file; those calls sit
inside the measured share. On Django the share includes time a parsing thread waits for the GIL while another thread runs, so it measures wall clock under
concurrency rather than interpreter-only parse work.

### What the numbers mean (decision D9)

The async read-and-parse stage is primarily a memory-shape and responsiveness decision, not a parallel-speedup claim: `ast.parse` holds the GIL in
CPython, so the worker threads do not parse in parallel, and they add a small scheduling cost. The net gain still comes from removing the second parse pass.
On Django the removed pass is worth roughly 400 ms, comfortably more than the chunked stage costs, so the run is about 1.06x faster. On the 32-file corpus
the removed pass outweighs the read and threading overhead, and the run is about 5 ms faster rather than slower. The chunk window keeps memory bounded at
the price of roughly 20 MB of extra peak RSS on Django, which is the deliberate trade: directories far larger than this one stream through the same
64-file window instead of being loaded up front.

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
| Reading and parsing every discovered file once, in bounded chunks | `O(F)` | `deadcode/actions/read_python_files.py`, called from `deadcode/visitor/dead_code_visitor.py` |
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
