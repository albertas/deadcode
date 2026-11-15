"""Measure deadcode end-to-end wall clock and peak RSS on one or more corpora.

Every measurement is a child run of ``deadcode <corpus> --count --no-color``
timed with ``time.perf_counter``. The harness only uses the standard library
and never imports ``deadcode`` in its own process. Exit status 1 is accepted
because ``deadcode`` returns it when the corpus has findings.
"""

import argparse
import json
import os
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

FINDINGS_EXIT_STATUS = 1


def count_python_files(corpus: str) -> int:
    path = Path(corpus)
    if path.is_dir():
        return sum(1 for _ in path.rglob('*.py'))
    return 1


def child_command(args: argparse.Namespace, corpus: str) -> list[str]:
    command = [sys.executable, '-m', 'deadcode.cli'] if args.module else [args.deadcode]
    return [*command, corpus, '--count', '--no-color']


def child_environment(args: argparse.Namespace) -> dict[str, str]:
    environment = os.environ.copy()
    if args.pythonpath:
        existing = environment.get('PYTHONPATH')
        environment['PYTHONPATH'] = args.pythonpath if not existing else os.pathsep.join((args.pythonpath, existing))
    return environment


def run_once(args: argparse.Namespace, corpus: str) -> float:
    started = time.perf_counter()
    completed = subprocess.run(  # noqa: S603
        child_command(args, corpus),
        cwd=args.cwd,
        env=child_environment(args),
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode not in (0, FINDINGS_EXIT_STATUS):
        stderr = completed.stderr.decode('utf-8', errors='replace').strip()
        message = f'benchmark child failed ({completed.returncode}): {" ".join(completed.args)}\n{stderr}'
        raise SystemExit(message)
    return elapsed


def measure(args: argparse.Namespace, corpus: str) -> dict[str, Any]:
    for _ in range(args.warmup):
        run_once(args, corpus)
    samples = [run_once(args, corpus) for _ in range(args.runs)]
    return {
        'corpus': corpus,
        'files': count_python_files(corpus),
        'median_ms': round(statistics.median(samples) * 1000, 1),
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }


def render_table(rows: list[dict[str, Any]]) -> str:
    headers = ('corpus', 'files', 'median_ms', 'peak_rss_kib')
    cells = [tuple(str(row[header]) for header in headers) for row in rows]
    widths = [max(len(header), *(len(cell[index]) for cell in cells)) for index, header in enumerate(headers)]
    lines = ['  '.join(header.ljust(width) for header, width in zip(headers, widths, strict=True))]
    lines.append('  '.join('-' * width for width in widths))
    lines.extend('  '.join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)) for row in cells)
    return '\n'.join(lines)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', action='append', required=True, help='corpus path passed to deadcode; repeatable')
    parser.add_argument('--runs', type=int, default=3, help='timed runs per corpus (default: 3)')
    parser.add_argument('--warmup', type=int, default=1, help='untimed warmup runs per corpus (default: 1)')
    parser.add_argument('--deadcode', default='deadcode', help='executable used for the child run (default: deadcode)')
    parser.add_argument('--module', action='store_true', help='run python -m deadcode.cli instead of the executable')
    parser.add_argument('--pythonpath', default=None, help='PYTHONPATH prepended to the child environment')
    parser.add_argument('--cwd', default=None, help="child working directory (default: this process's directory)")
    parser.add_argument('--format', choices=('table', 'json'), default='table', help='output format (default: table)')
    arguments = parser.parse_args(argv)
    if arguments.runs < 1:
        parser.error('--runs must be at least 1')
    if arguments.warmup < 0:
        parser.error('--warmup must not be negative')
    return arguments


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    rows = [measure(args, corpus) for corpus in args.corpus]
    if args.format == 'json':
        print(json.dumps(rows, indent=2))
    else:
        print(render_table(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
