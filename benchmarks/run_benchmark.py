"""Benchmark harness: run the fixed command on the corpus and record the results.

The fixed command (D3) is `deadcode <corpus-entry-root> --count`, executed as a
subprocess under `/usr/bin/time -v`. Per entry the harness performs one warmup
run and records `--runs` timed runs; `benchmarks/records.py` provides the pure
parsing, aggregation, and comparison logic. Results are written as JSON under
`benchmarks/results/` (gitignored); the baseline snapshot used for the
shipping-gate decision is copied into the artifacts repository.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from benchmarks.corpus import CorpusEntry, acquire, load_corpus
from benchmarks.records import aggregate, compare, parse_time_output, record_run

BENCHMARKS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARKS_DIR / 'results'
CACHE_DIR = BENCHMARKS_DIR / '.cache'
TIME_BINARY = Path('/usr/bin/time')


def main() -> None:
    args = _parse_args(sys.argv[1:])
    deadcode_binary = _find_deadcode_binary(args.deadcode)
    entries = load_corpus(BENCHMARKS_DIR / 'corpus.json')

    records: list[dict[str, object]] = []
    for entry in entries:
        records.extend(_run_entry(entry, deadcode_binary, args.label, args.runs))

    result: dict[str, Any] = {
        'label': args.label,
        'deadcode_binary': deadcode_binary,
        'records': records,
        'aggregate': aggregate(records),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / f'{args.label}.json'
    result_path.write_text(json.dumps(result, indent=4) + '\n')
    print(f'wrote {result_path}')

    for entry, metrics in sorted(result['aggregate'].items()):
        print(f'{entry}: median wall clock {metrics["wall_clock_seconds"]:.2f}s, findings {int(metrics["findings"])}')

    if args.compare_to is not None:
        _write_comparison(args.label, args.compare_to)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the deadcode benchmark corpus.')
    parser.add_argument('--label', default='baseline', help='label for the recorded run set')
    parser.add_argument('--compare-to', default=None, help='label of a previous run set to compare against')
    parser.add_argument('--deadcode', default=None, help='path to the deadcode console script to benchmark')
    parser.add_argument('--runs', type=int, default=3, help='number of recorded runs per entry')
    return parser.parse_args(argv)


def _find_deadcode_binary(override: str | None) -> str:
    candidates = [override] if override else [str(Path(sys.executable).with_name('deadcode')), shutil.which('deadcode')]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    print('run_benchmark: could not find the deadcode console script; pass --deadcode <path>', file=sys.stderr)
    raise SystemExit(1)


def _run_entry(entry: CorpusEntry, deadcode_binary: str, label: str, runs: int) -> list[dict[str, object]]:
    if not TIME_BINARY.exists():
        print(f'run_benchmark: {TIME_BINARY} is missing; wall-clock/CPU/RSS metrics require GNU time', file=sys.stderr)
        raise SystemExit(1)

    root = acquire(entry, CACHE_DIR)
    analysed_root = _analyse_root(entry, root)
    command = [deadcode_binary, str(analysed_root), '--count']
    print(f'{entry.name}: {" ".join(command)}')

    # One warmup run so the recorded runs measure warm caches (D3).
    _run_once(command, analysed_root)

    records: list[dict[str, object]] = []
    for run in range(runs):
        exit_status, stdout, stderr, metrics = _run_once(command, analysed_root)
        records.append(record_run(entry.name, label, run, metrics, exit_status, stdout, stderr))
    return records


def _analyse_root(entry: CorpusEntry, acquired_root: Path) -> Path:
    """Resolve the analysed root: the manifest's `path` inside the acquired tree.

    The subprocess runs with the analysed root as its working directory, so each
    corpus entry is analysed with its own configuration (or deadcode's defaults
    when the project has no `[tool.deadcode]` section), never with the
    benchmarking repository's own config.
    """
    if entry.url is None:
        return Path(entry.path).resolve()
    return (acquired_root / entry.path).resolve()


def _run_once(command: list[str], cwd: Path) -> tuple[int, bytes, bytes, dict[str, float]]:
    with tempfile.NamedTemporaryFile(mode='r', suffix='.time') as time_file:
        result = subprocess.run(  # noqa: S603
            [str(TIME_BINARY), '-v', '-o', time_file.name, *command],
            check=False,
            capture_output=True,
            cwd=cwd,
        )
        metrics = parse_time_output(time_file.read())
    return result.returncode, result.stdout, result.stderr, metrics


def _write_comparison(label: str, base_label: str) -> None:
    base_path = RESULTS_DIR / f'{base_label}.json'
    if not base_path.exists():
        print(f'run_benchmark: no recorded run set named {base_label!r} at {base_path}', file=sys.stderr)
        raise SystemExit(1)

    base_records = json.loads(base_path.read_text())['records']
    candidate_records = json.loads((RESULTS_DIR / f'{label}.json').read_text())['records']
    comparison = compare(base_records, candidate_records)

    comparison_path = RESULTS_DIR / f'{label}-vs-{base_label}.json'
    comparison_path.write_text(json.dumps(comparison, indent=4) + '\n')
    print(f'wrote {comparison_path}')

    for entry, verdict in sorted(comparison.items()):
        parity = (
            verdict['stdout_hash_match']
            and verdict['stderr_hash_match']
            and verdict['exit_status_match']
            and verdict['findings_match']
        )
        print(
            f'{entry}: parity {"ok" if parity else "FAILED"}'
            f' (speedup {verdict["wall_clock_speedup"]:.2f}x,'
            f' peak memory {verdict["peak_memory_ratio"]:.2f}x)'
        )


if __name__ == '__main__':
    main()
