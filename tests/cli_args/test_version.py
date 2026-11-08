from deadcode import __version__
from deadcode.cli import main


def test_show_version():
    # When
    result = main('--version'.split())

    # Then
    assert result == __version__


def test_show_version_when_path_provided():
    # When
    result = main('. --version'.split())

    # Then
    assert result == __version__


def test_show_version_with_short_option():
    # When
    result = main('-V'.split())

    # Then
    assert result == __version__


def test_show_version_with_short_option_when_path_provided():
    # When
    result = main('. -V'.split())

    # Then
    assert result == __version__
