from deadcode import __version__
from deadcode.cli import main


def test_show_version():
    result = main('--version'.split())

    assert result == __version__


def test_show_version_when_path_provided():
    result = main('. --version'.split())

    assert result == __version__


def test_show_version_with_short_option():
    result = main('-V'.split())

    assert result == __version__


def test_show_version_with_short_option_when_path_provided():
    result = main('. -V'.split())

    assert result == __version__
