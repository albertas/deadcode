from pathlib import Path

from deadcode.cli import main
from deadcode.data_types import Args
from deadcode.actions.find_python_filenames import find_python_filenames


def test_exclude_directories(arguments: Args):
    # Having
    arguments.paths = ['deadcode/.']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert any(f.startswith('deadcode/cli.py') for f in filenames)
    assert any(f.startswith('deadcode/utils') for f in filenames)

    # Having
    arguments.exclude = ['deadcode/utils', 'deadcode/cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert not any(f.startswith('deadcode/cli.py') for f in filenames)
    assert not any(f.startswith('deadcode/utils') for f in filenames)


def test_exclude_files(arguments: Args):
    # Having
    arguments.paths = ['deadcode/.']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert 'deadcode/cli.py' in filenames

    # Having
    arguments.exclude = ['deadcode/cli.py']

    # When
    filenames = find_python_filenames(args=arguments)

    # Then
    assert 'deadcode/cli.py' not in filenames


def test_exclude_skips_findings_end_to_end(tmp_path, monkeypatch):
    # Having
    monkeypatch.chdir(tmp_path)
    Path('keep.py').write_text('unused_kept = 1\n')
    Path('skip.py').write_text('unused_skipped = 1\n')

    # When
    result = main(['.', '--exclude', 'skip.py', '--no-color'])

    # Then
    assert result is not None
    assert 'keep.py' in result
    assert 'DC01' in result
    assert 'skip.py' not in result

    # When
    result_without_exclude = main(['.', '--no-color'])

    # Then
    assert result_without_exclude is not None
    assert 'keep.py' in result_without_exclude
    assert 'skip.py' in result_without_exclude
