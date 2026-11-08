import ast

import pytest

from deadcode.utils.print_ast import print_ast


def test_print_ast_writes_indented_dump(capsys: pytest.CaptureFixture[str]):
    # Having
    node = ast.parse('x = 1')

    # When
    print_ast(node)

    # Then
    assert capsys.readouterr().out == ast.dump(node, indent=4) + '\n'
