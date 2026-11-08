"""
Test empty files detection and removal.
"""

from deadcode.cli import main


def test_file_removal(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py DC11 Empty file\n\n' 'Removed 1 unused code item!')

    virtual_file_system.assert_files({}, removed=['foo.py'])


def test_file_removal_from_subpath(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'bar/foo.py': b"""
                """
    }

    # When
    unused_names = main(['bar/foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('bar/foo.py DC11 Empty file\n\n' 'Removed 1 unused code item!')

    virtual_file_system.assert_files({}, removed=['bar/foo.py'])
