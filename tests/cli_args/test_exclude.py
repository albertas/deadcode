from pathlib import Path

from deadcode.cli import main
from deadcode.data_types import Args
from deadcode.actions.find_python_filenames import find_python_filenames


def test_exclude_directories(arguments: Args):
    arguments.paths = ['deadcode/.']
    filenames = find_python_filenames(args=arguments)
    assert any(f.startswith('deadcode/cli.py') for f in filenames)
    assert any(f.startswith('deadcode/utils') for f in filenames)

    arguments.exclude = ['deadcode/utils', 'deadcode/cli.py']
    filenames = find_python_filenames(args=arguments)
    assert not any(f.startswith('deadcode/cli.py') for f in filenames)
    assert not any(f.startswith('deadcode/utils') for f in filenames)


def test_exclude_files(arguments: Args):
    arguments.paths = ['deadcode/.']
    filenames = find_python_filenames(args=arguments)
    assert 'deadcode/cli.py' in filenames

    arguments.exclude = ['deadcode/cli.py']
    filenames = find_python_filenames(args=arguments)
    assert 'deadcode/cli.py' not in filenames


def test_exclude_skips_findings_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('keep.py').write_text('unused_kept = 1\n')
    Path('skip.py').write_text('unused_skipped = 1\n')

    result = main(['.', '--exclude', 'skip.py', '--no-color'])

    assert result is not None
    assert 'keep.py' in result
    assert 'DC01' in result
    assert 'skip.py' not in result

    result_without_exclude = main(['.', '--no-color'])

    assert result_without_exclude is not None
    assert 'keep.py' in result_without_exclude
    assert 'skip.py' in result_without_exclude
