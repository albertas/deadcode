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
