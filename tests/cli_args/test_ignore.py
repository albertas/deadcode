from pathlib import Path

from deadcode.cli import main


def test_ignore_suppresses_dc12(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'print("Keep")\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore', 'DC12'])

    # Then
    assert unused_names is None


def test_ignore_leaves_other_rules_visible(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'unused_variable = 1\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore', 'DC12'])

    # Then
    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_variable` is never used')


def test_ignore_accepts_comma_separated_values(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'unused_variable = 1\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore=DC12,DC01'])

    # Then
    assert unused_names is None


def test_ignore_accepts_repeated_values(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'unused_variable = 1\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore=DC12', '--ignore=DC01'])

    # Then
    assert unused_names is None


def test_ignore_is_case_insensitive(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'print("Keep")\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore=dc12'])

    # Then
    assert unused_names is None


def test_unknown_ignore_code_suppresses_nothing(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'print("Keep")\n# print("Hello world")\n',
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore=DC99'])

    # Then
    assert unused_names == ('foo.py:2:0: DC12 Commented out code')


def test_ignored_findings_are_not_fixed(virtual_file_system):
    # Having
    source = b'print("Keep")\n# print("Hello world")\n'
    virtual_file_system.files = {'foo.py': source}

    # When
    unused_names = main(['foo.py', '--no-color', '--fix', '--ignore', 'DC12'])

    # Then
    assert unused_names is None
    virtual_file_system.assert_files({'foo.py': source})


def test_ignore_from_pyproject_toml(project_directory: Path):
    # Having
    (project_directory / 'pyproject.toml').write_text('[tool.deadcode]\nignore = ["DC12"]\n')
    (project_directory / 'service.py').write_text('print("Keep")\n# print("Hello world")\n')

    # When
    unused_names = main(['service.py', '--no-color'])

    # Then
    assert unused_names is None
