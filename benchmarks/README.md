# Benchmark harness

`benchmark_pipeline.py` measures deadcode end-to-end on one or more corpora. It runs a child
`deadcode <corpus> --count --no-color` process, discards the child's stdout and stderr, and reports the Python file count, the median wall clock, and the
peak child RSS for each corpus. The numbers on the {doc}`../docs/performance` page come from this harness.

The harness uses only the standard library and never imports `deadcode` in its own process. It runs `--warmup` untimed child runs and then `--runs` timed
runs per corpus. Exit status 0 is accepted, and so is status 1 because `deadcode` returns 1 when a corpus has findings; any other status aborts with a
non-zero exit. Wall clock is `time.perf_counter()` around `subprocess.run`, and peak RSS is `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss` (KiB
on Linux). The RSS value is the largest child RSS seen so far in the harness process, so a multi-corpus run reports the maximum over the corpora measured
before that point. Measure one corpus per process when the per-corpus peak matters.

## Usage

```bash
python benchmarks/benchmark_pipeline.py --corpus deadcode --corpus /tmp/django-src/django
```

Flags and defaults:

- `--corpus PATH` — corpus path passed to the child; repeatable and required.
- `--runs N` — timed runs per corpus, default `3`.
- `--warmup N` — untimed warmup runs per corpus, default `1`.
- `--deadcode PATH` — executable used for the child run, default `deadcode`.
- `--module` — run `python -m deadcode.cli` instead of the executable. The interpreter is the one running the harness.
- `--pythonpath PATH` — value prepended to the child `PYTHONPATH`.
- `--cwd PATH` — child working directory, default the current directory. A `-m` child puts its working directory first on `sys.path`, so this selects
  which tree provides the `deadcode` package.
- `--format {table,json}` — output format, default `table`.

Table output has a `corpus`, `files`, `median_ms`, and `peak_rss_kib` column. JSON output is a list of objects with the same keys:

```json
[
  {"corpus": "deadcode", "files": 32, "median_ms": 218.4, "peak_rss_kib": 29308}
]
```

## Reproducing the documented numbers

Create the detached baseline worktree once and leave it read-only:

```bash
git worktree add --detach /tmp/deadcode-baseline 889149c
```

Feature run, from the feature worktree:

```bash
.venv/bin/python benchmarks/benchmark_pipeline.py \
  --corpus deadcode --corpus /tmp/django-src/django \
  --runs 3 --warmup 1 --format table
```

Baseline run, from the feature worktree. The child imports the baseline package from `--cwd` and `--pythonpath` while the `.venv` supplies the dependencies:

```bash
.venv/bin/python benchmarks/benchmark_pipeline.py \
  --corpus deadcode --corpus /tmp/django-src/django \
  --runs 3 --warmup 1 --module --pythonpath /tmp/deadcode-baseline --cwd /tmp/deadcode-baseline \
  --format table
```

The documented medians come from five interleaved single-run pairs per corpus after one warmup for each baseline and feature run. Use the same idle machine,
the same interpreter, and a warm page cache, and record:

- baseline commit `889149c` and the feature branch commit;
- corpus paths, Python file counts, and total bytes;
- the Django checkout version; this environment's `/tmp/django-src` is not a Git checkout, so no commit SHA is available;
- interpreter version, OS and kernel, logical CPU count, and total RAM;
- the raw harness output for every run, not only the final table.

Corpora used for the published numbers: `deadcode/` (32 Python files, 116,139 bytes) and `/tmp/django-src/django` (Django 6.2.0a0, 909 Python files,
5,958,239 bytes).

The read-stage microbenchmark and the `ast.parse` share quoted on the performance page are separate in-process measurements. They are not produced by this
harness.
