import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks.corpus import CorpusEntry, acquire, cache_path, load_corpus

FLASK_SHA = 'a' * 40
CLONE_URL = 'https://github.com/pallets/flask.git'


def write_manifest(tmp_path: Path, repos: list[dict[str, Any]]) -> Path:
    manifest_path = tmp_path / 'corpus.json'
    manifest_path.write_text(json.dumps({'repos': repos}))
    return manifest_path


def clone_entry(**overrides: Any) -> CorpusEntry:
    fields: dict[str, Any] = {'name': 'flask', 'url': CLONE_URL, 'commit': FLASK_SHA, 'path': 'src'}
    fields.update(overrides)
    return CorpusEntry(**fields)


def patch_git(monkeypatch: pytest.MonkeyPatch, returncode: int = 0) -> list[tuple[tuple[str, ...], Path | None]]:
    """Replace subprocess.run in benchmarks.corpus; return the list of recorded git calls."""
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    def fake_run(command: list[str], cwd: Path | None = None, capture_output: bool = True, check: bool = False) -> Any:
        calls.append((tuple(command), cwd))
        return type('Result', (), {'returncode': returncode, 'stderr': b'boom'})()

    monkeypatch.setattr('benchmarks.corpus.subprocess.run', fake_run)
    return calls


class TestLoadCorpus:
    def test_loads_valid_manifest(self, tmp_path: Path) -> None:
        manifest_path = write_manifest(
            tmp_path,
            [
                {'name': 'deadcode', 'url': None, 'commit': None, 'path': '.'},
                {'name': 'flask', 'url': CLONE_URL, 'commit': FLASK_SHA, 'path': 'src'},
            ],
        )

        entries = load_corpus(manifest_path)

        assert entries == [
            CorpusEntry(name='deadcode', url=None, commit=None, path='.'),
            CorpusEntry(name='flask', url=CLONE_URL, commit=FLASK_SHA, path='src'),
        ]

    def test_missing_required_field(self, tmp_path: Path) -> None:
        manifest_path = write_manifest(tmp_path, [{'name': 'flask', 'url': CLONE_URL, 'commit': FLASK_SHA}])

        with pytest.raises(ValueError, match="missing the required field 'path'"):
            load_corpus(manifest_path)

    def test_missing_name_field(self, tmp_path: Path) -> None:
        manifest_path = write_manifest(tmp_path, [{'url': CLONE_URL, 'commit': FLASK_SHA, 'path': 'src'}])

        with pytest.raises(ValueError, match="missing the required field 'name'"):
            load_corpus(manifest_path)

    def test_bad_commit_sha(self, tmp_path: Path) -> None:
        manifest_path = write_manifest(
            tmp_path,
            [
                {'name': 'flask', 'url': CLONE_URL, 'commit': 'deadbeef', 'path': 'src'},
            ],
        )

        with pytest.raises(ValueError, match='40-hex commit SHA'):
            load_corpus(manifest_path)

    def test_in_place_entry_with_commit(self, tmp_path: Path) -> None:
        manifest_path = write_manifest(
            tmp_path,
            [
                {'name': 'deadcode', 'url': None, 'commit': FLASK_SHA, 'path': '.'},
            ],
        )

        with pytest.raises(ValueError, match='no URL but specifies a commit'):
            load_corpus(manifest_path)


class TestCachePath:
    def test_is_deterministic_per_entry(self, tmp_path: Path) -> None:
        entry = clone_entry()

        assert cache_path(entry, tmp_path / 'cache') == cache_path(entry, tmp_path / 'cache')
        assert cache_path(entry, tmp_path / 'cache') == tmp_path / 'cache' / 'flask'
        assert cache_path(clone_entry(name='django'), tmp_path / 'cache') == tmp_path / 'cache' / 'django'


class TestAcquire:
    def test_in_place_entry_returns_path_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = patch_git(monkeypatch)
        entry = CorpusEntry(name='deadcode', url=None, commit=None, path='.')

        assert acquire(entry, tmp_path) == Path()
        assert calls == []

    def test_fresh_clone_then_checkout(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = patch_git(monkeypatch)
        entry = clone_entry()

        result = acquire(entry, tmp_path)

        assert result == tmp_path / 'flask'
        assert calls == [
            (('git', 'clone', CLONE_URL, str(tmp_path / 'flask')), None),
            (('git', 'checkout', '--force', FLASK_SHA), tmp_path / 'flask'),
        ]

    def test_reuses_cached_clone(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = patch_git(monkeypatch)
        target = tmp_path / 'flask'
        (target / '.git').mkdir(parents=True)
        entry = clone_entry()

        result = acquire(entry, tmp_path)

        assert result == target
        assert calls == [
            (('git', 'checkout', '--force', FLASK_SHA), target),
            (('git', 'clean', '-fdx'), target),
        ]

    def test_clone_failure_exits_visibly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
        patch_git(monkeypatch, returncode=1)
        entry = clone_entry()

        with pytest.raises(SystemExit):
            acquire(entry, tmp_path)

        captured = capsys.readouterr()
        assert 'flask' in captured.err
        assert CLONE_URL in captured.err
        assert FLASK_SHA in captured.err

    def test_checkout_failure_exits_visibly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
        patch_git(monkeypatch, returncode=1)
        target = tmp_path / 'flask'
        (target / '.git').mkdir(parents=True)
        entry = clone_entry()

        with pytest.raises(SystemExit):
            acquire(entry, tmp_path)

        captured = capsys.readouterr()
        assert 'flask' in captured.err
        assert FLASK_SHA in captured.err
