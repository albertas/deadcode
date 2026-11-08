from pathlib import Path

import pytest

from deadcode.cli import main, print_main
from deadcode.utils.base_test_case import BaseTestCase

SOURCE = b"""
from unittest import TestCase


class MyTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def setUpClass(cls):
        pass

    def tearDownClass(cls):
        pass

    def test_something(self):
        pass
"""

SOURCE_WITH_UNUSED_HELPER = (
    SOURCE
    + b"""
    def unused_helper(self):
        pass
"""
)


class TestUnittestLifecycleMethods(BaseTestCase):
    def test_lifecycle_methods_in_test_file_are_not_reported(self):
        self.files = {'/project/tests/test_sample.py': SOURCE}

        self.assertIsNone(main(['/project/tests/test_sample.py', '--no-color']))
        self.assertEqual(print_main(['/project/tests/test_sample.py', '--no-color']), 0)

    def test_lifecycle_methods_outside_test_file_are_still_reported(self):
        self.files = {'/project/sample.py': SOURCE}

        output = main(['/project/sample.py', '--no-color'])

        assert output is not None
        self.assertIn('DC04 Method `setUp` is never used', output)
        self.assertIn('DC04 Method `tearDown` is never used', output)
        self.assertIn('DC02 Function `setUpClass` is never used', output)
        self.assertIn('DC02 Function `tearDownClass` is never used', output)
        self.assertEqual(print_main(['/project/sample.py', '--no-color']), 1)

    def test_unrelated_unused_method_in_test_file_is_still_reported(self):
        self.files = {'/project/tests/test_sample.py': SOURCE_WITH_UNUSED_HELPER}

        output = main(['/project/tests/test_sample.py', '--no-color'])

        assert output is not None
        self.assertEqual(len(output.splitlines()), 1)
        self.assertTrue(output.endswith('DC04 Method `unused_helper` is never used'))


def test_unittest_lifecycle_in_temporary_test_directory_returns_no_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_directory = tmp_path / 'tests'
    test_directory.mkdir()
    (test_directory / 'test_sample.py').write_bytes(SOURCE)
    monkeypatch.chdir(tmp_path)

    assert main(['tests', '--no-color']) is None
    assert print_main(['tests', '--no-color']) == 0
