from pathlib import Path

import pytest

from deadcode.cli import main
from deadcode.utils.nested_scopes import NestedScope
from deadcode.visitor.code_item import CodeItem


def test_class_should_be_in_scope(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC03 Class `Foo` is never used\n\n' 'Removed 1 unused code item!')

    virtual_file_system.assert_files({})


def test_class_and_its_method_should_be_in_scope(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def bar(self):
                        variable = 123
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_name_is_overriden(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    pass


                class Foo:
                    pass
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_multi_parent_inheritance_should_be_tracked(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    pass


                class Bar(Foo):
                    pass


                class Spam(Bar):
                    pass
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix', '--ignore-definitions-if-inherits-from=Foo'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:
                    pass


                class Bar(Foo):
                    pass


                class Spam(Bar):
                    pass
                """
        }
    )

    assert result is None


def test_take_parent_scopes_into_consideration_when_searching_for_definition(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    pass


                class Bar(Foo):
                    class Spam(Foo):
                        pass

                    class Eggs(Spam):
                        pass
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix', '--ignore-definitions-if-inherits-from=Foo'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:
                    pass


                class Bar(Foo):
                    class Spam(Foo):
                        pass

                    class Eggs(Spam):
                        pass
                """
        }
    )

    assert result is None


@pytest.mark.skip(reason='This feature is being implemented')
def test_type_tracking_for_function_arguments(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def bar(self):
                        pass

                def spam(eggs):
                    eggs.bar()

                foo = Foo()
                spam(foo)

                def bar():
                    pass
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # TODO: detect eggs type inside spam function and mark Foo.bar as used in CodeItem instance.
    # Usages should be marked directly on the CodeItem instances, not in a pool of names.

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:
                    def bar(self):
                        pass

                def spam(eggs):
                    eggs.bar()

                foo = Foo()
                spam(foo)
                """
        }
    )

    assert result is None


@pytest.mark.skip(reason='>> Observed types in scope definition is still being implemented')
def test_scope_update_for_method_call_expression(virtual_file_system):
    # >>> TODO: Mark types in scope usage correctly for method invocation

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                Bar().spam()
                """
    }

    # When
    result = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({'foo.py': b""""""})

    assert result is None


def test_add_code_item_without_scope_is_ignored():
    # Having
    nested_scope = NestedScope()
    code_item = CodeItem(name='Foo', type_='class', filename=Path('foo.py'))

    # When
    result = nested_scope.add(code_item)

    # Then
    assert result is None
    assert nested_scope._scopes == {}  # noqa: SLF001
