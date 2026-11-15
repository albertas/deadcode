# Benchmark harness

`benchmark_pipeline.py` measures deadcode end-to-end on one or more corpora. It reports the median wall clock of several child runs, the number of Python
files in each corpus, and the peak child RSS. The numbers on the `docs/performance.md` page come from the commands below.

The harness uses only the standard library, never imports `deadcode` in its own process, and runs one warmup plus three timed child runs per corpus by
default. Every child run is `deadcode <corpus> --count --no-color`, timed with `time.perf_counter()` around `subprocess.run`, with stdout and stderr
discarded. Exit status 0 is accepted, and so is exit status 1, because `deadcode` returns 1 when a corpus has findings; any other status aborts the
benchmark. Peak RSS is `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss` after the timed runs, so it is the largest child RSS seen so far and the
second corpus in a multi-corpus run reports the maximum over both.

## Environment

- CPython 3.10.22 from `.venv`, GIL build, Linux x86_64, 16 logical CPUs, 30 GiB RAM, warm page cache, otherwise idle machine.
- Baseline commit `889149c` (the pull-request base) in a detached worktree.
- Corpora: the repository's `deadcode/` package (32 Python files) and a Django source checkout at `/tmp/django-src/django` (909 Python files). The corpus
  path is whatever you pass with `--corpus`; keep it stable between baseline and feature runs.

## Usage

```bash
python benchmarks/benchmark_pipeline.py --corpus deadcode --corpus /tmp/django-src/django
```

Options:

- `--corpus PATH` — corpus path passed to deadcode; repeatable and required.
- `--runs N` — timed runs per corpus, default 3.
- `--warmup N` — untimed warmup runs per corpus, default 1.
- `--deadcode PATH` — executable for the child run, default this interpreter.
- `--module NAME` — module run with `-m`, default `deadcode.cli`; `--no-module` runs the executable directly.
- `--pythonpath PATH` — exported as `PYTHONPATH` in the child environment.
- `--cwd PATH` — child working directory, default the current directory. A `-m` child puts its working directory first on `sys.path`, so this selects
  which tree provides the `deadcode` package.
- `--format {table,json}` — output format, default `table`.

## Reproducing the documented numbers

Create the detached baseline worktree once and leave it read-only:

```bash
git worktree add --detach /tmp/deadcode-baseline 889149c
```

Baseline run, from the feature worktree. The child imports the baseline package from `--cwd` while the `.venv` provides the dependencies:

```bash
.venv/bin/python benchmarks/benchmark_pipeline.py \
  --deadcode "$(pwd)/.venv/bin/python" --module deadcode.cli \
  --cwd /tmp/deadcode-baseline \
  --corpus deadcode --corpus /tmp/django-src/django \
  --runs 3 --warmup 1 --format table
```

Feature run, from the feature worktree:

```bash
.venv/bin/python benchmarks/benchmark_pipeline.py \
  --corpus deadcode --corpus /tmp/django-src/django \
  --runs 3 --warmup 1 --format table
```

Run the baseline first and the feature branch second on the same idle machine with a warm page cache. Keep the raw output with the numbers you publish:
`--format json` prints `[{"corpus": ..., "files": ..., "median_ms": ..., "peak_rss_kib": ...}]`.

The read-stage microbenchmark and the `ast.parse` share quoted on the `docs/performance.md` page are separate in-process measurements; they are not
produced by this harness.
