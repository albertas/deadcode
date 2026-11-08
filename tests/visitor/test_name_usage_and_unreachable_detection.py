import ast
from pathlib import Path

from deadcode.data_types import Args
from deadcode.visitor import noqa
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor


def _visit(source: str, *, ignore_decorators: list[str] | None = None) -> DeadCodeVisitor:
    """Parse the source and run the visitor over it as if it were a module file."""
    # Having
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    visitor.filename = Path('foo.py')
    visitor.module_name = 'foo'
    visitor.scope_parts = ['foo']
    visitor.code = source.splitlines()
    visitor.noqa_lines = noqa.parse_noqa(source.encode())
    if ignore_decorators is not None:
        visitor.ignore_decorators = ignore_decorators

    # When
    visitor.visit(ast.parse(source, filename='foo.py', type_comments=True))

    # Then
    return visitor


def test_name_used_in_module_returns_true_for_a_globally_used_name() -> None:
    # Having
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    visitor.used_names.add('Foo')

    # When
    is_used = visitor.is_name_used_in_module('Foo', 'foo')

    # Then
    assert is_used is True


def test_ternary_with_always_true_condition_marks_else_as_unreachable() -> None:
    # When
    visitor = _visit('x = 1 if True else 2')

    # Then
    unreachable = list(visitor.unreachable_body)
    assert [item.name for item in unreachable] == ['ternary']
    assert unreachable[0].message == 'Unreachable `else` expression'


def test_tuple_assignment_target_has_no_removal_node() -> None:
    # When
    visitor = _visit('a: int = 1\nb, c = (\n    2,\n    3,\n)')

    # Then
    assert sorted(item.name for item in visitor.defined_vars) == ['a', 'b', 'c']
    assert all(item.code_parts for item in visitor.defined_vars)


def test_invalid_format_string_field_is_ignored() -> None:
    # Having
    visitor = _visit("'{invalid'.format(**locals())")

    # When
    names = visitor.used_names

    # Then
    assert 'invalid' not in names


def test_valid_format_string_field_is_recorded_as_used() -> None:
    # When
    visitor = _visit("'{module.value}'.format(**locals())")

    # Then
    assert {'module', 'value'} <= set(visitor.used_names)


def test_match_class_keyword_attribute_is_recorded_as_used() -> None:
    # Having
    source = """
value = Point()
match value:
    case Point(x=1):
        pass
"""

    # When
    visitor = _visit(source)

    # Then
    assert 'x' in visitor.used_names


def test_variable_type_comment_is_parsed() -> None:
    # Having
    source = 'x = 1  # type: int\n'

    # When
    visitor = _visit(source)

    # Then
    assert 'int' in visitor.bare_used_names['foo']


def test_function_type_comment_is_parsed_in_function_type_mode() -> None:
    # Having
    source = """
def function(argument):
    # type: (int) -> str
    return str(argument)
"""

    # When
    visitor = _visit(source)

    # Then
    assert {'int', 'str'} <= visitor.bare_used_names['foo']


def test_class_with_ignored_decorator_is_not_defined() -> None:
    # Having
    source = """
@ignore_me
class Ignored:
    pass
"""

    # When
    visitor = _visit(source, ignore_decorators=['@ignore_me'])

    # Then
    assert [item.name for item in visitor.defined_classes] == []


def test_function_with_ignored_decorator_is_not_defined() -> None:
    # Having
    source = """
@ignore_me
def ignored():
    pass
"""

    # When
    visitor = _visit(source, ignore_decorators=['@ignore_me'])

    # Then
    assert [item.name for item in visitor.defined_funcs] == []


def test_assignment_removal_node_is_none_when_target_does_not_match() -> None:
    # Having
    visitor = DeadCodeVisitor(filenames=[], args=Args())
    statement = ast.parse('b, c = (\n    2,\n    3,\n)').body[0]
    visitor._assignment_nodes = [statement]  # noqa: SLF001
    target = ast.parse('b').body[0].value

    # When
    removal_node = visitor._get_assignment_removal_node(target)  # noqa: SLF001

    # Then
    assert removal_node is None
