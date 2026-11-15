"""Measure deadcode end-to-end wall clock and peak RSS on one or more corpora.

The harness only uses the standard library and never imports ``deadcode`` in
its own process: every measurement is a child ``deadcode`` run whose timing is
taken with ``time.perf_counter`` around ``subprocess.run``. Exit status 1 is
accepted because ``deadcode`` returns it when the corpus has findings.
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


def count_python_files(corpus: Path) -> int:
    if corpus.is_file():
        return 1
    return sum(1 for _ in corpus.rglob('*.py'))


def build_command(deadcode: str, module: str | None, corpus: str) -> list[str]:
    command = [deadcode]
    if module:
        command.extend(['-m', module])
    command.extend([corpus, '--count', '--no-color'])
    return command


def run_child(command: list[str], *, cwd: str, env: dict[str, str]) -> None:
    completed = subprocess.run(command, cwd=cwd, env=env, capture_output=True, check=False)  # noqa: S603
    if completed.returncode not in (0, FINDINGS_EXIT_STATUS):
        stderr = completed.stderr.decode('utf-8', errors='replace').strip()
        message = f'benchmark child failed ({completed.returncode}): {" ".join(command)}\n{stderr}'
        raise SystemExit(message)


def measure_corpus(
    corpus: str,
    *,
    deadcode: str,
    module: str | None,
    runs: int,
    warmup: int,
    cwd: str,
    env: dict[str, str],
) -> dict[str, Any]:
    command = build_command(deadcode, module, corpus)
    for _ in range(warmup):
        run_child(command, cwd=cwd, env=env)

    durations: list[float] = []
    for _ in range(runs):
        started_at = time.perf_counter()
        run_child(command, cwd=cwd, env=env)
        durations.append(time.perf_counter() - started_at)

    peak_rss_kib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return {
        'corpus': corpus,
        'files': count_python_files(Path(corpus)),
        'median_ms': round(statistics.median(durations) * 1000, 1),
        'peak_rss_kib': peak_rss_kib,
    }


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ('corpus', 'files', 'median_ms', 'peak_rss_kib')
    table = [[str(row[header]) for header in headers] for row in rows]
    widths = [max(len(headers[index]), *(len(line[index]) for line in table)) for index in range(len(headers))]
    header_line = '  '.join(header.ljust(width) for header, width in zip(headers, widths, strict=True))
    print(header_line)
    print('  '.join('-' * width for width in widths))
    for line in table:
        print('  '.join(value.ljust(width) for value, width in zip(line, widths, strict=True)))


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', action='append', required=True, help='corpus path passed to deadcode; repeatable')
    parser.add_argument('--runs', type=int, default=3, help='number of timed runs per corpus (default: 3)')
    parser.add_argument('--warmup', type=int, default=1, help='number of untimed warmup runs per corpus (default: 1)')
    parser.add_argument(
        '--deadcode',
        default=sys.executable,
        help='executable used for the child run (default: this interpreter)',
    )
    parser.add_argument(
        '--module',
        default='deadcode.cli',
        help='module run as the child entry point (default: deadcode.cli)',
    )
    parser.add_argument('--no-module', action='store_true', help='run the executable directly instead of `-m MODULE`')
    parser.add_argument('--pythonpath', default=None, help='PYTHONPATH exported to the child environment')
    parser.add_argument('--cwd', default=None, help="child working directory (default: this process's directory)")
    parser.add_argument('--format', choices=('table', 'json'), default='table', help='output format (default: table)')
    arguments = parser.parse_args(argv)
    if arguments.runs < 1:
        parser.error('--runs must be at least 1')
    if arguments.warmup < 0:
        parser.error('--warmup must not be negative')
    return arguments


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    module = None if arguments.no_module else arguments.module

    env = dict(os.environ)
    if arguments.pythonpath is not None:
        env['PYTHONPATH'] = arguments.pythonpath
    cwd = arguments.cwd if arguments.cwd is not None else str(Path.cwd())

    rows = [
        measure_corpus(
            corpus,
            deadcode=arguments.deadcode,
            module=module,
            runs=arguments.runs,
            warmup=arguments.warmup,
            cwd=cwd,
            env=env,
        )
        for corpus in arguments.corpus
    ]

    if arguments.format == 'json':
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows)
    return 0


if __name__ == '__main__':
    sys.exit(main())
