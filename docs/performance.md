# Performance

## What this page covers

This page reviews the efficiency of deadcode's implementation and explains how the cost of the analysis grows with the size of the input. The review walks
through the analysis pipeline stage by stage, names the source files on the hot path the way the {doc}`features` page cites paths, and reports where the
cost stays linear and where it can grow faster. The primary quantity on this page is `n`, the total amount of source code processed, measured in lines of
code across the analysed files — the same framing the {doc}`open_source_experiment` page uses when it asks whether runtime grows roughly linearly with
lines of code. The Benchmark section reports measured end-to-end wall clock, the isolated read stage, the measured parse-stage share, and peak memory on two
corpora.

## Efficiency review findings

The findings below come from reading the implementation of the analysis pipeline. Each finding names the concrete source file on the hot path.

**(a) The analysis reads each file once and parses each file once, in bounded asynchronous chunks.** `visit_abstract_syntax_trees` in
`deadcode/visitor/dead_code_visitor.py` is an `async def`. It splits the discovered files into chunks of `READ_CHUNK_FILES` (32) entries with
`chunk_filenames` from `deadcode/actions/read_python_files.py`, then processes up to `DEFAULT_WORKERS` chunks concurrently with `asyncio.gather`. Each
chunk is handed to a worker thread that calls `_read_and_parse_chunk`: it reads every file once with `read_file_chunk` and parses each file once with
`ast.parse`. The parsed chunks are consumed in input order and released before the next wave is read, so a directory of any size is streamed through a
fixed-size window instead of being loaded into memory up front. The single tree per file feeds both module-export registration and the AST traversal.
`find_unused_names` in `deadcode/actions/find_unused_names.py` runs the coroutine with `asyncio.run` on one `DeadCodeVisitor` and visits every discovered
file once; the `# noqa` comments are parsed from the same bytes returned by the read stage.

**(b) There is no second module-export read or parse pass.** Module exports are registered from the tree that the main pass already produced
(`_register_module_exports`), so the pipeline no longer opens or parses a file for export collection before the traversal starts. A file whose
`type_comments=True` parse fails is retried once with a plain `ast.parse` (`_register_module_exports_from_plain_parse`) so export collection still mirrors
the historical behaviour, but that retry only happens for files that fail to parse.

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
29 files, with the visitor traversal taking 0.164 seconds, the since-removed module-export parse taking 0.058 seconds, and comment tokenisation taking 0.027
seconds. This is a one-off sample of a different codebase state, not a baseline: it measured one codebase with one interpreter and the since-removed second
parse pass. The Benchmark section below is the reproducible measurement for the current pipeline.

## Benchmark

### Environment and corpora

- CPython 3.10.22, GIL build, Linux 7.0.0-38-generic x86_64, 16 logical CPUs, 30.5 GiB RAM, warm page cache, otherwise idle machine.
- Baseline: commit `889149c` (the pull-request base) in a detached worktree at `/tmp/deadcode-baseline`.
- Feature: the branch that reads and parses files through `deadcode/actions/read_python_files.py` and registers exports from the main parse tree.
- `deadcode/` — the repository's own package, 32 Python files, 116,139 bytes.
- `/tmp/django-src/django` — a Django 6.2.0a0 source checkout with 909 Python files, 5,958,239 bytes. This checkout has no Git metadata, so no Django
  commit SHA is available; the version string comes from `django/__init__.py`.

The harness is `benchmarks/benchmark_pipeline.py`. It uses only the standard library, never imports `deadcode` in its own process, runs one warmup and
three timed child runs per corpus by default, and reports the median wall clock with `time.perf_counter` plus the peak child RSS from
`resource.getrusage`. The baseline run points the child at the baseline worktree with `--cwd`, `--pythonpath`, and `-m deadcode.cli`, so the baseline
package is imported while the `.venv` supplies the dependencies. `benchmarks/README.md` records the flags, output shapes, and exact commands.

### End-to-end results

The table below reports the median of five interleaved single-run pairs per corpus after one warmup for each baseline and feature run, plus the median
peak child RSS. Interleaving the pairs keeps both branches under the same machine load.

| Corpus | Files | Baseline median | Feature median | Change | Baseline peak RSS | Feature peak RSS |
|---|---|---|---|---|---|---|
| `deadcode/` | 32 | 206.9 ms | 218.4 ms | 0.95x (5.6% slower) | 24.0 MB | 28.3 MB |
| `/tmp/django-src/django` | 909 | 7,752.2 ms | 7,587.0 ms | 1.02x faster (-165.2 ms) | 102.7 MB | 112.6 MB |

The 1.05x success target was not met, so the D10 fallback was applied: `DEFAULT_WORKERS` is `1`, so the `asyncio` stage awaits one chunk task at a time
instead of running several parse workers. The fallback keeps the chunked read-and-parse shape and the bounded memory window, but it removes the extra
worker-thread scheduling. The remaining measurements are recorded honestly rather than tuned to the target.

### Isolated read stage

Medians of seven in-process repetitions of reading the same file lists, comparing a plain sequential `read_file_chunk` loop with the async chunked wave
loop that calls `asyncio.to_thread(read_file_chunk, chunk)` over `chunk_filenames(...)` slices with `DEFAULT_WORKERS`:

| Corpus | Bytes | Sequential loop | Async chunked wave | Read-stage cost |
|---|---|---|---|---|
| `deadcode/` (32 files) | 116,139 | 0.40 ms | 1.81 ms | +1.41 ms |
| `/tmp/django-src/django` (909 files) | 5,958,239 | 9.07 ms | 19.13 ms | +10.06 ms |

Reading is already fast from a warm page cache, and the `asyncio` event loop plus worker-thread handoffs cost more than the reads they overlap. The
chunked stage is therefore a memory-shape decision, not a read-speed decision.

### Parse-stage share

Instrumenting `ast.parse` in-process with timers wrapped around the call (these runs exclude interpreter startup) gives a median parse share of 8.8% on
`deadcode/` (12.0–21.2 ms of 144.2–154.7 ms) and 14.1% on Django (960.1–1,033.9 ms of 7,079.4–7,160.0 ms) across three runs. A default run of the
32-file corpus issues 60 `ast.parse` calls and the Django corpus 4,536, because comment candidates and type comments add calls beyond the one per file;
those calls sit inside the measured share. A `cProfile` + `pstats` sample of the same Django run attributes only 0.27% to `ast.parse`, because the
profiler does not charge the built-in `compile` work it invokes to that Python-level frame; the in-process timer is the figure used here because it
measures the full call. A default run of the Django corpus printed zero `Error: Failed to parse` lines, as did the `deadcode/` corpus.

### What the numbers mean (decision D10)

The gain comes from removing the second parse pass, not from parallel parsing. `ast.parse` holds the GIL in CPython, so worker threads do not parse in
parallel, and with `DEFAULT_WORKERS = 1` the async stage only bounds memory and file descriptors. On Django the pipeline is about 1.02x faster, which is
real but below the 1.05x target; on the 32-file corpus it is about 5.6% slower, because the fixed `asyncio` cost is not amortised by a large read set.
The extra peak RSS on Django (about 10 MB) is the reserved chunk window and worker-thread bookkeeping. These are the measured results of the selected
configuration; the page makes no claim of a larger speedup.

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
| Per-file reading, `noqa` scan, parsing, and comment scanning | `O(n)` | `deadcode/actions/read_python_files.py`, `deadcode/visitor/noqa.py`, `deadcode/visitor/dead_code_visitor.py` |
| AST traversal with per-node and per-`definition` ignore matching | `O(N × P)` | `deadcode/visitor/dead_code_visitor.py`, `deadcode/visitor/ignore.py` |
| Unused-item pass with cross-module bare-name resolution | `O(D)`, worst case `O(D × M)` | `deadcode/visitor/dead_code_visitor.py` |
| Report assembly | `O(U log U)` for the final sort | `deadcode/visitor/dead_code_visitor.py` |
| `--fix` and `--dry` overlap merge | `O(p²)` per file, with `p` the number of removal parts of that file | `deadcode/actions/merge_overlaping_file_parts.py` |

### What stays linear in practice

In practice, a default run behaves linearly with constant factors: each file is read and parsed once in the chunked main traversal pass (finding (a)), the
`definition` lists stay flat, and the usage checks are set-membership lookups rather than scans. The exceptions are the super-linear paths reported in the
[efficiency review findings](#efficiency-review-findings): the worst-case `O(D × M)` cross-module bare-name resolution (finding (c)), the quadratic
`--fix` overlap merge (finding (d)), the per-item pattern matching that grows with the number of configured ignore patterns (finding (e)), and the
per-candidate `ast.parse` attempts in comment handling (finding (f)).

The Benchmark section measures these costs at corpus scale: the current pipeline is about 1.02x faster than the baseline on the 909-file Django corpus
and about 5.6% slower on the 32-file `deadcode/` corpus, and the read stage and parse share are reported separately so the net figure is not mistaken for
an I/O speedup.
