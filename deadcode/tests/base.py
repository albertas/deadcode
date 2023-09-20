from pathlib import Path
from typing import Dict, List, Union
from unittest import TestCase
from unittest.mock import MagicMock, patch

from deadcode.utils.cleandoc import cleandoc
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

        file_content = cleandoc(self.files[mock.filename])
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

    def assertFiles(self, expected_updated_files: Dict[str, str]):
        self.assertListEqual(list(expected_updated_files.keys()), list(self.updated_files.keys()))

        for filename, content in expected_updated_files.items():
            self.assertEqual(
                cleandoc(content),
                self.updated_files[filename],
            )
        # This will return all the different contents for read.
        # but only sequentional write operations.
        #
        # I would like to have write operation per filename.
        # self.fix_file_mock.write.assert_called_once_with('class UnusedClass:\n    pass')
