"""Corpus manifest loading and repository acquisition for the deadcode benchmarks.

The manifest (`benchmarks/corpus.json`) lists the benchmark corpus: deadcode
itself (analysed in place) plus third-party projects fetched at run time and
pinned by commit SHA. Clones live in a gitignored cache directory
(`benchmarks/.cache/`) so reruns do not re-download.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

COMMIT_REGEXP = re.compile(r'^[0-9a-f]{40}$')


@dataclass(frozen=True)
class CorpusEntry:
    """One corpus entry: an analysed project pinned by commit SHA."""

    name: str
    url: str | None
    commit: str | None
    path: str


def load_corpus(path: Path) -> list[CorpusEntry]:
    """Load and validate the corpus manifest at `path`."""
    manifest = json.loads(path.read_text())
    return [_load_entry(raw) for raw in manifest['repos']]


def _load_entry(raw: dict[str, object]) -> CorpusEntry:
    name = raw.get('name')
    if not isinstance(name, str) or not name:
        msg = "Corpus entry is missing the required field 'name'"
        raise ValueError(msg)

    url = raw.get('url')
    if url is not None and not isinstance(url, str):
        msg = f'Corpus entry {name!r} has a non-string url field'
        raise ValueError(msg)

    path = raw.get('path')
    if not isinstance(path, str) or not path:
        msg = f"Corpus entry {name!r} is missing the required field 'path'"
        raise ValueError(msg)

    commit = raw.get('commit')
    if url is None:
        # Entries analysed in place carry no URL and no commit.
        if commit is not None:
            msg = f'Corpus entry {name!r} has no URL but specifies a commit'
            raise ValueError(msg)
        return CorpusEntry(name=name, url=None, commit=None, path=path)

    if not isinstance(commit, str) or not COMMIT_REGEXP.match(commit):
        msg = f'Corpus entry {name!r} must pin a 40-hex commit SHA, got {commit!r}'
        raise ValueError(msg)
    return CorpusEntry(name=name, url=url, commit=commit, path=path)


def cache_path(entry: CorpusEntry, cache_dir: Path) -> Path:
    """Return the deterministic per-entry clone directory under `cache_dir`."""
    return cache_dir / entry.name


def acquire(entry: CorpusEntry, cache_dir: Path) -> Path:
    """Return the analysed root for `entry`, cloning or reusing the cache as needed."""
    if entry.url is None:
        # Entries without a URL are analysed in place, at the repository root.
        return Path(entry.path)

    target = cache_path(entry, cache_dir)
    if (target / '.git').exists():
        # Reuse the cached clone and check out the pinned SHA.
        _run_git(['checkout', '--force', entry.commit], entry=entry, cwd=target)
        _run_git(['clean', '-fdx'], entry=entry, cwd=target)
    else:
        _run_git(['clone', entry.url, str(target)], entry=entry)
        _run_git(['checkout', '--force', entry.commit], entry=entry, cwd=target)
    return target


def _run_git(args: list[str], entry: CorpusEntry, cwd: Path | None = None) -> None:
    command = ['git', *args]
    result = subprocess.run(command, check=False, cwd=cwd, capture_output=True)  # noqa: S603
    if result.returncode != 0:
        detail = result.stderr.decode(errors='replace').strip()
        joined = ' '.join(command)
        print(
            f'benchmarks corpus: failed to acquire {entry.name!r} '
            f'(url={entry.url}, commit={entry.commit}): {joined}\n{detail}',
            file=sys.stderr,
        )
        raise SystemExit(1)


def main() -> None:
    """Acquire every corpus entry into the local cache."""
    benchmarks_dir = Path(__file__).resolve().parent
    entries = load_corpus(benchmarks_dir / 'corpus.json')
    cache_dir = benchmarks_dir / '.cache'
    for entry in entries:
        root = acquire(entry, cache_dir)
        print(f'{entry.name}: {root}')


if __name__ == '__main__':
    main()
