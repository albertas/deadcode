from deadcode.cli import main


def test_variable_is_imported_as_an_alias_but_unused(virtual_file_system):
    # Variable is used, because its imported in another file

    # Having
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b'from foo import used_var as foo_var; print(foo_var)',
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names is None


def test_variable_is_used_if_its_imported_as_a_different_name(virtual_file_system):
    # Variable is used, because its imported in another file

    # Having
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                from foo import used_var as foo_var
                print(foo_var)""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names is None


def test_module_imported_and_var_from_it_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                import foo
                print(foo.used_var)""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    # Attribute(value=Name(id='foo', ctx=Load()), attr='used_var', ctx=Load())

    # Then
    assert unused_names is None


def test_module_imported_with_alias_and_var_from_it_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                import foo as f
                print(f.used_var)""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names is None


def test_relative_module_imports(virtual_file_system):
    # https://docs.python.org/3/tutorial/modules.html#intra-package-references

    # Having
    virtual_file_system.files = {
        'eggs/foo.py': b'used_var = None',
        'eggs/spam/bar.py': b"""
                from .. import foo as f
                print(f.used_var)""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names is None


def test_sibling_relative_module_imports(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'eggs/foo.py': b'used_var = None',
        'eggs/bar.py': b"""
                from .foo import used_var
                print(used_var)""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names is None


def test_file_contains_syntax_error(virtual_file_system):
    # Having
    virtual_file_system.files = {'foo.py': b'unused_var = None this is syntax error'}

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names is None

    # The same check works without a Syntax error

    # Having
    virtual_file_system.files = {'foo.py': b'unused_var = None'}

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:1:0: DC01 Variable `unused_var` is never used'


def test_ignore_variable_names_in_comments(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                # unused_variable is empty
                unused_var = None  # This is a comment about unused_var
                # Another comment about unused variable
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:2:0: DC01 Variable `unused_var` is never used'


def test_ignore_variable_names_in_strings(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                '''
                unused_var initial value is None - this a string about unused_variable
                '''
                unused_var = None
                print("This is another string about unused_variable")
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:4:0: DC01 Variable `unused_var` is never used'


def test_quoted_annotation_from_issue_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'quoted.py': b"""from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abc import ABC

a: "ABC | None" = None
print(a)
"""
    }

    # When
    result = main(['quoted.py', '--no-color'])

    # Then
    assert result is None


def test_quoted_annassign_annotation_outside_guard_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from abc import ABC

a: "ABC | None" = None
print(a)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_quoted_parameter_annotation_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abc import ABC


def handler(value: "ABC") -> None:
    print(value)


print(handler)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_quoted_return_annotation_with_typing_guard_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""import typing

if typing.TYPE_CHECKING:
    from abc import ABC


def handler() -> "ABC":
    return None


print(handler)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_quoted_annotation_with_typing_extensions_guard_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from abc import ABC

a: "ABC" = None
print(a)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_quoted_annotation_with_aliased_guard_is_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from typing import TYPE_CHECKING as TC

if TC:
    from abc import ABC

a: "ABC" = None
print(a)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_nested_quoted_annotations_are_used(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from abc import ABC

x: list["ABC"] = []


def handler() -> "dict[str, 'ABC']":
    return {}


print(x)
print(handler)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_dotted_quoted_annotation_records_module_name(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from helpers import mod

value: "mod.Type" = None
print(value)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_import_not_mentioned_by_quoted_annotation_is_still_unused(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abc import ABC

a: "XYZ | None" = None
print(a)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result == 'foo.py:4:20: DC07 Import `ABC` is never used'


def test_name_only_in_ordinary_string_is_still_unused(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from abc import ABC

print("ABC")
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result == 'foo.py:1:16: DC07 Import `ABC` is never used'


def test_unparseable_quoted_annotation_is_ignored(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""from abc import ABC

value: "ABC |" = None
print(value)
"""
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result == 'foo.py:1:16: DC07 Import `ABC` is never used'
