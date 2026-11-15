"""Pure record logic for the deadcode benchmarks: parsing, aggregation, and comparison.

Everything in this module is unit-testable without network access or clones;
`benchmarks.run_benchmark` orchestrates the actual runs.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

TIMING_METRICS = ('wall_clock_seconds', 'user_cpu_seconds', 'sys_cpu_seconds', 'peak_rss_kb', 'findings')

USER_TIME_REGEXP = re.compile(r'^[ \t]*User time \(seconds\):\s*(\S+)', re.MULTILINE)
SYSTEM_TIME_REGEXP = re.compile(r'^[ \t]*System time \(seconds\):\s*(\S+)', re.MULTILINE)
ELAPSED_TIME_REGEXP = re.compile(r'^[ \t]*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)', re.MULTILINE)
MAX_RSS_REGEXP = re.compile(r'^[ \t]*Maximum resident set size \(kbytes\):\s*(\S+)', re.MULTILINE)
FINDINGS_REGEXP = re.compile(r'^(0|[1-9][0-9]*)$')


def parse_time_output(text: str) -> dict[str, float]:
    """Parse the metrics we record from `/usr/bin/time -v` output."""
    elapsed_match = ELAPSED_TIME_REGEXP.search(text)
    if elapsed_match is None:
        msg = '/usr/bin/time -v output is missing the "Elapsed (wall clock) time" line'
        raise ValueError(msg)

    wall_clock_seconds = _parse_elapsed(elapsed_match.group(1))

    user_match = USER_TIME_REGEXP.search(text)
    if user_match is None:
        msg = '/usr/bin/time -v output is missing the "User time (seconds)" line'
        raise ValueError(msg)

    system_match = SYSTEM_TIME_REGEXP.search(text)
    if system_match is None:
        msg = '/usr/bin/time -v output is missing the "System time (seconds)" line'
        raise ValueError(msg)

    rss_match = MAX_RSS_REGEXP.search(text)
    if rss_match is None:
        msg = '/usr/bin/time -v output is missing the "Maximum resident set size" line'
        raise ValueError(msg)

    return {
        'wall_clock_seconds': wall_clock_seconds,
        'user_cpu_seconds': float(user_match.group(1)),
        'sys_cpu_seconds': float(system_match.group(1)),
        'peak_rss_kb': int(rss_match.group(1)),
    }


def _parse_elapsed(value: str) -> float:
    """Parse an `h:mm:ss` or `m:ss` wall-clock value into seconds."""
    parts = value.split(':')
    if not 1 <= len(parts) <= 3:
        msg = f'Cannot parse elapsed time value {value!r}'
        raise ValueError(msg)
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def parse_findings(stdout: bytes) -> int:
    """Parse the findings count from the fixed command's stdout.

    The `--count` branch prints a single non-negative integer, and a clean run
    prints nothing; anything else is a harness error (D3).
    """
    if not stdout.strip():
        return 0
    text = stdout.decode().strip()
    if not FINDINGS_REGEXP.match(text):
        msg = f'Stdout is not a single non-negative integer findings count: {stdout!r}'
        raise ValueError(msg)
    return int(text)


def sha256(data: bytes) -> str:
    """Return the hex SHA-256 of `data`."""
    return hashlib.sha256(data).hexdigest()


def record_run(
    entry: str,
    label: str,
    run: int,
    metrics: dict[str, float],
    exit_status: int,
    stdout: bytes,
    stderr: bytes,
) -> dict[str, object]:
    """Build one benchmark record from a single timed run."""
    return {
        'entry': entry,
        'label': label,
        'run': run,
        'wall_clock_seconds': metrics['wall_clock_seconds'],
        'user_cpu_seconds': metrics['user_cpu_seconds'],
        'sys_cpu_seconds': metrics['sys_cpu_seconds'],
        'peak_rss_kb': metrics['peak_rss_kb'],
        'exit_status': exit_status,
        'findings': parse_findings(stdout),
        'stdout_sha256': sha256(stdout),
        'stderr_sha256': sha256(stderr),
    }


def median(values: list[float]) -> float:
    """Return the median of `values` (mean of the two middle values for even counts)."""
    if not values:
        msg = 'Cannot take the median of an empty sequence'
        raise ValueError(msg)
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def aggregate(records: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    """Group records per corpus entry and take the median of each timing metric."""
    by_entry: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        by_entry[str(record['entry'])].append(record)

    result: dict[str, dict[str, float]] = {}
    for entry, entry_records in sorted(by_entry.items()):
        result[entry] = {
            metric: median([float(record[metric]) for record in entry_records])  # type: ignore[arg-type]
            for metric in TIMING_METRICS
        }
    return result


def compare(
    base_records: list[dict[str, object]], candidate_records: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    """Compare two labelled record sets per corpus entry.

    Parity flags cover stdout/stderr hash equality, exit status equality, and
    findings-count equality; `wall_clock_speedup` is base/candidate median and
    `peak_memory_ratio` is candidate/base median peak RSS (the D7 gate inputs).
    """
    base_aggregate = aggregate(base_records)
    candidate_aggregate = aggregate(candidate_records)

    result: dict[str, dict[str, object]] = {}
    for entry in sorted(set(base_aggregate) & set(candidate_aggregate)):
        base_hashes = _hashes(base_records, entry)
        candidate_hashes = _hashes(candidate_records, entry)
        base_statuses = {int(record['exit_status']) for record in base_records if record['entry'] == entry}  # type: ignore[arg-type]
        candidate_statuses = {
            int(record['exit_status'])
            for record in candidate_records
            if record['entry'] == entry  # type: ignore[arg-type]
        }
        base_findings = {int(record['findings']) for record in base_records if record['entry'] == entry}  # type: ignore[arg-type]
        candidate_findings = {
            int(record['findings'])
            for record in candidate_records
            if record['entry'] == entry  # type: ignore[arg-type]
        }
        result[entry] = {
            'stdout_hash_match': base_hashes['stdout'] == candidate_hashes['stdout'],
            'stderr_hash_match': base_hashes['stderr'] == candidate_hashes['stderr'],
            'exit_status_match': base_statuses == candidate_statuses,
            'findings_match': base_findings == candidate_findings,
            'wall_clock_speedup': base_aggregate[entry]['wall_clock_seconds']
            / candidate_aggregate[entry]['wall_clock_seconds'],
            'peak_memory_ratio': candidate_aggregate[entry]['peak_rss_kb'] / base_aggregate[entry]['peak_rss_kb'],
        }
    return result


def _hashes(records: list[dict[str, object]], entry: str) -> dict[str, set[str]]:
    stdout = {str(record['stdout_sha256']) for record in records if record['entry'] == entry}
    stderr = {str(record['stderr_sha256']) for record in records if record['entry'] == entry}
    return {'stdout': stdout, 'stderr': stderr}
