import ast
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from deadcode.data_types import Args
from deadcode.utils.fix_indent import fix_indent


def assert_valid_python(content: bytes) -> None:
    """Fail the test when the given file content is not valid Python source."""
    try:
        ast.parse(content)
    except SyntaxError as error:
        message = f'Fixed file is not valid Python: {error}'
        raise AssertionError(message) from error


class VirtualFileSystem:
    """In-memory replacement for the file system calls deadcode makes while running a command."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.monkeypatch = monkeypatch
        self.files: dict[str, bytes] = {}
        self.updated_files: dict[str, bytes] = {}
        self.removed_files: list[str] = []
        self._install()

    def _get_filenames(self, *args: Any, **kwargs: Any) -> list[str]:
        return list(self.files.keys())

    def _read_file_side_effect(self, filename: str | Path, *args: Any, **kwargs: Any) -> MagicMock:
        mock = MagicMock()
        mock.filename = str(filename)

        def cache_file_content(file_content: bytes) -> int:
            self.updated_files[mock.filename] = file_content
            return len(file_content)

        if file_content := fix_indent(self.files[mock.filename]):
            mock.__enter__().read.return_value = file_content
            mock.__enter__().readlines.return_value = [line + b'\n' for line in file_content.split(b'\n')]
            mock.__enter__().write.side_effect = cache_file_content
        return mock

    def _install(self) -> None:
        self.monkeypatch.setattr('deadcode.cli.find_python_filenames', MagicMock(side_effect=self._get_filenames))
        self.monkeypatch.setattr(
            'deadcode.visitor.dead_code_visitor.open',
            MagicMock(side_effect=self._read_file_side_effect),
            raising=False,
        )
        self.monkeypatch.setattr(
            'deadcode.actions.fix_or_show_unused_code.open',
            MagicMock(side_effect=self._read_file_side_effect),
            raising=False,
        )
        self.os_remove = MagicMock(side_effect=self.removed_files.append)
        self.monkeypatch.setattr('deadcode.actions.fix_or_show_unused_code.os.remove', self.os_remove)

    def assert_files(self, expected_files: dict[str, bytes], removed: list[str] | None = None) -> None:
        """Check that the removed and written file names and contents match the expectation."""
        expected_removed_files = removed

        removed_filenames = [call.args[0] for call in self.os_remove.mock_calls]
        if expected_removed_files:
            assert removed_filenames == expected_removed_files, 'removed files do not match'

        unchanged_files = {
            filename: file_content
            for filename, file_content in self.files.items()
            if filename not in self.updated_files and filename not in removed_filenames
        }
        assert list(expected_files.keys()) == list(self.updated_files.keys()) + list(
            unchanged_files.keys()
        ), 'file names do not match'

        for filename, content in expected_files.items():
            actual_content = self.updated_files.get(filename) or unchanged_files.get(filename) or ''
            assert fix_indent(content) == fix_indent(actual_content), f'content mismatch for {filename}'
            if filename in self.updated_files:
                assert_valid_python(self.updated_files[filename])

    def assert_updated_files(self, expected_updated_files: dict[str, bytes]) -> None:
        """Check that the written file names and contents match the expectation."""
        assert list(expected_updated_files.keys()) == list(self.updated_files.keys()), 'updated file names do not match'

        for filename, content in expected_updated_files.items():
            assert fix_indent(content) == self.updated_files[filename], f'content mismatch for {filename}'
            assert_valid_python(self.updated_files[filename])


@pytest.fixture()
def virtual_file_system(monkeypatch: pytest.MonkeyPatch) -> VirtualFileSystem:
    return VirtualFileSystem(monkeypatch)


@pytest.fixture()
def arguments() -> Args:
    return Args()
