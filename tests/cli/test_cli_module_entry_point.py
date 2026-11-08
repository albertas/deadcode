import runpy
import sys

import pytest

from deadcode import __version__


def test_module_entry_point_prints_version_and_exits_with_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    # Having
    monkeypatch.setattr(sys, 'argv', ['deadcode', '--version'])

    # When
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module('deadcode.cli', run_name='__main__')

    # Then
    assert exc_info.value.code == 0
    assert capsys.readouterr().out == f'{__version__}\n'
