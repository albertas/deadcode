from deadcode.cli import main

FILES_WITH_UNUSED_CLASSES = {
    'ignored/foo.py': b"""
                class UnusedClass:
                    pass
                """,
    'kept/bar.py': b"""
                class AnotherUnusedClass:
                    pass
                """,
}


def test_finding_in_matching_file_is_suppressed(virtual_file_system):
    # Having
    virtual_file_system.files = FILES_WITH_UNUSED_CLASSES

    # When
    unused_names = main(['ignored', 'kept', '--ignore-names-in-files=ignored/*', '--no-color'])

    # Then
    assert unused_names is not None
    assert 'kept/bar.py' in unused_names
    assert 'DC03' in unused_names
    assert 'ignored/foo.py' not in unused_names


def test_matching_file_is_reported_without_the_option(virtual_file_system):
    # Having
    virtual_file_system.files = FILES_WITH_UNUSED_CLASSES

    # When
    unused_names = main(['ignored', 'kept', '--no-color'])

    # Then
    assert unused_names is not None
    assert 'ignored/foo.py' in unused_names
    assert 'kept/bar.py' in unused_names


def test_path_expression_glob_is_honoured(virtual_file_system):
    # Having
    virtual_file_system.files = FILES_WITH_UNUSED_CLASSES

    # When
    unused_names = main(['ignored', 'kept', '--ignore-names-in-files=*.py', '--no-color'])

    # Then
    assert unused_names is None


def test_fix_leaves_ignored_file_unchanged(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignored/foo.py': b"""
                import os
                """,
    }

    # When
    result = main(['ignored/foo.py', '--ignore-names-in-files=ignored/*', '--fix', '--no-color'])

    # Then
    assert result is None
    virtual_file_system.assert_files(
        {
            'ignored/foo.py': b"""
                import os
                """,
        }
    )
