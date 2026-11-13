from pathlib import Path, PosixPath, PureWindowsPath

from deadcode.utils.normalize_path import normalize_path


def test_pure_windows_path_is_converted_to_forward_slashes():
    assert normalize_path(PureWindowsPath('pkg/mod.py')) == 'pkg/mod.py'


def test_windows_string_path_is_converted_to_forward_slashes():
    assert normalize_path('pkg\\mod.py') == 'pkg/mod.py'


def test_raw_windows_string_path_is_converted_to_forward_slashes():
    assert normalize_path(r'pkg\mod.py') == 'pkg/mod.py'


def test_backslash_in_posix_filename_is_preserved():
    assert normalize_path(PosixPath('pkg\\mod.py')) == 'pkg\\mod.py'


def test_duplicate_separators_are_preserved():
    assert normalize_path('pkg//mod.py') == 'pkg//mod.py'


def test_plain_path_object_is_converted_to_forward_slashes():
    assert normalize_path(Path('pkg/mod.py')) == 'pkg/mod.py'
