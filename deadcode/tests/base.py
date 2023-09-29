from pathlib import Path
from typing import Dict, List, Union
from unittest import TestCase
from unittest.mock import MagicMock, patch

from deadcode.utils.fix_indent import fix_indent
from deadcode.data_types import Args


class BaseTestCase(TestCase):
    files: Dict[str, str] = {}

    maxDiff = None

    def patch(self, path: str) -> MagicMock:
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _get_filenames(self, *args, **kwargs) -> List[str]:
        return list(self.files.keys())

    def _read_file_side_effect(self, filename: Union[str, Path], *args, **kwargs) -> MagicMock:
        mock = MagicMock()
        mock.filename = str(filename)

        def cache_file_content(file_content: str):
            self.updated_files[mock.filename] = file_content
            return len(file_content)

        file_content = fix_indent(self.files[mock.filename])
        mock.__enter__().read.return_value = file_content
        mock.__enter__().readlines.return_value = [f"{line}\n" for line in file_content.split("\n")]
        mock.__enter__().write.side_effect = cache_file_content
        return mock

    def setUp(self):
        self.updated_files: Dict[str, str] = {}

        self.find_python_filenames_mock = self.patch("deadcode.cli.find_python_filenames")
        self.find_python_filenames_mock.side_effect = self._get_filenames

        self.read_file_mock = self.patch("deadcode.visitor.dead_code_visitor.open")
        self.read_file_mock.side_effect = self._read_file_side_effect

        self.fix_file_mock = self.patch("deadcode.actions.fix_unused_code.open")
        self.fix_file_mock.side_effect = self._read_file_side_effect

        self.os_remove = self.patch("deadcode.actions.fix_unused_code.os.remove")

        self.args = Args(
            fix=False,
            verbose=False,
            paths=[],
            exclude=[],
            ignore_definitions=[],
            ignore_definitions_if_inherits_from=[],
            ignore_names=[],
            ignore_names_in_files=[],
            no_color=False,
            quiet=False,
            count=False,
        )

        # os.listdir should be patched with files keys

    def assertFiles(self, files: Dict[str, str], removed: List[str] = None):
        expected_removed_files = removed
        expected_files = files

        # Check if removed files match
        removed_filenames = [call.args[0] for call in self.os_remove.mock_calls]
        if expected_removed_files:
            self.assertEqual(removed_filenames, expected_removed_files)

        # Check if non removed files are the same
        unchanged_files = {
            filename: file_content
            for filename, file_content in self.files.items()
            if filename not in self.updated_files and filename not in removed_filenames
        }
        self.assertListEqual(
            list(expected_files.keys()), list(self.updated_files.keys()) + list(unchanged_files.keys())
        )

        # Check if non removed file contents match (both changed and unchanged)
        for filename, content in expected_files.items():
            self.assertEqual(
                fix_indent(content),
                fix_indent(self.updated_files.get(filename, unchanged_files.get(filename)) or ""),
            )

    def assertUpdatedFiles(self, expected_updated_files: Dict[str, str]):
        """Checks if updated files match expected updated files."""

        self.assertListEqual(list(expected_updated_files.keys()), list(self.updated_files.keys()))

        for filename, content in expected_updated_files.items():
            self.assertEqual(
                fix_indent(content),
                self.updated_files[filename],
            )
