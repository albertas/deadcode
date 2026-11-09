from pathlib import Path

import pytest

from deadcode.cli import main, print_main

SOURCE = b"""
from unittest import TestCase


class MyTests(TestCase):
    def setUpTestData(cls):
        pass

    def _pre_setup(self):
        pass

    def _post_teardown(self):
        pass

    def _fixture_setup(self):
        pass

    def _fixture_teardown(self):
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

SOURCE_WITH_DECORATED_SET_UP_TEST_DATA = b"""
from django.test import TestCase


class MyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def test_something(self):
        pass
"""

SOURCE_WITHOUT_TEST_CASE_BASE = b"""
class TestMySuite:
    def setUpTestData(cls):
        pass

    def _pre_setup(self):
        pass
"""

SOURCE_WITH_USER_INVOKED_HELPERS = b"""
class MyTests:
    def assertContains(self):
        pass

    def assertNumQueries(self):
        pass

    def settings(self):
        pass

    def modify_settings(self):
        pass

    def captureOnCommitCallbacks(self):
        pass
"""


def test_django_lifecycle_methods_in_test_file_are_not_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/tests/test_sample.py': SOURCE}

    # When
    result = main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result is None

    # When
    result = print_main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result == 0


def test_django_lifecycle_declared_without_classmethod_is_not_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/tests/test_sample.py': SOURCE_WITHOUT_TEST_CASE_BASE}

    # When
    result = main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result is None

    # When
    result = print_main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result == 0


def test_django_test_case_class_method_set_up_test_data_is_not_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/tests/test_sample.py': SOURCE_WITH_DECORATED_SET_UP_TEST_DATA}

    # When
    result = main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result is None

    # When
    result = print_main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result == 0


def test_django_lifecycle_methods_outside_test_file_are_still_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/sample.py': SOURCE}

    # When
    output = main(['/project/sample.py', '--no-color'])

    # Then
    assert output is not None
    assert 'DC02 Function `setUpTestData` is never used' in output
    assert 'DC04 Method `_pre_setup` is never used' in output
    assert 'DC04 Method `_post_teardown` is never used' in output
    assert 'DC04 Method `_fixture_setup` is never used' in output
    assert 'DC04 Method `_fixture_teardown` is never used' in output

    # When
    result = print_main(['/project/sample.py', '--no-color'])

    # Then
    assert result == 1


def test_unrelated_unused_method_in_test_file_is_still_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/tests/test_sample.py': SOURCE_WITH_UNUSED_HELPER}

    # When
    output = main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert output is not None
    assert len(output.splitlines()) == 1
    assert output.endswith('DC04 Method `unused_helper` is never used')


def test_user_invoked_django_helpers_in_test_file_are_still_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {'/project/tests/test_sample.py': SOURCE_WITH_USER_INVOKED_HELPERS}

    # When
    output = main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert output is not None
    assert 'DC04 Method `assertContains` is never used' in output
    assert 'DC04 Method `assertNumQueries` is never used' in output
    assert 'DC04 Method `settings` is never used' in output
    assert 'DC04 Method `modify_settings` is never used' in output
    assert 'DC04 Method `captureOnCommitCallbacks` is never used' in output

    # When
    result = print_main(['/project/tests/test_sample.py', '--no-color'])

    # Then
    assert result == 1


def test_django_lifecycle_in_nested_test_directory_returns_no_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Having
    test_directory = tmp_path / 'app' / 'tests'
    test_directory.mkdir(parents=True)
    (test_directory / 'test_models.py').write_bytes(SOURCE)
    monkeypatch.chdir(tmp_path)

    # When
    result = main(['app', '--no-color'])

    # Then
    assert result is None

    # When
    result = print_main(['app', '--no-color'])

    # Then
    assert result == 0
