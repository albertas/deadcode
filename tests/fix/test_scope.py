"""
Test class def.
"""

import pytest

from deadcode.cli import main

pytestmark = pytest.mark.skip(
    reason='Skipped without a recorded reason before the pytest migration; behaviour preserved'
)


def test_same_variable_name_is_used_for_two_different_classes(virtual_file_system):
    """Usage of the class methods should be tracked properly."""

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                class Spam:
                    def foo(self):
                        pass

                instance = Foo()
                instance.foo()
                print(instance)

                instance = Spam()
                print(instance)
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_function(virtual_file_system):
    """Usage of the class methods should be tracked properly."""

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                def say_foo(some_instance):
                    some_instance.foo()

                say_foo(Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_function_using_args(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                def say_foo(*args):
                    for var in args:
                        var.foo()

                say_foo(Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_function_using_kwargs(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                def say_foo(*args, **kwargs):
                    for key, value in kwargs.items():
                        value.foo()

                say_foo(instance=Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_method_using_kwargs(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                class Bar:
                    def say_foo(self, *args, **kwargs):
                        for key, value in kwargs.items():
                            value.foo()

                Bar().say_foo(instance=Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_class_method_using_kwargs(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                class Bar:
                    @classmethod
                    def say_foo(cls, *args, **kwargs):
                        for key, value in kwargs.items():
                            value.foo()

                Bar().say_foo(instance=Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_passed_into_a_static_method_using_kwargs(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                class Bar:
                    @staticmethod
                    def say_foo(*args, **kwargs):
                        for key, value in kwargs.items():
                            value.foo()

                Bar().say_foo(instance=Foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_imported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass
                """,
        'bar.py': b"""
                from foo import Foo
                print(Foo().foo())
                """,
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_instance_is_being_imported_with_renaming(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass
                """,
        'bar.py': b"""
                from foo import Foo as Bar
                print(Bar().foo())
                """,
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_variable_renaming(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                instance = Foo()
                instnace2 = instance
                print(instnace2.foo())
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_variable_renaming_using_expansion_from_a_list(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                instance = Foo()
                instnace2, remaining_values* = [instance, 1, 2, 3]
                print(instnace2.foo())
                """,
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})


def test_function_arguments_are_being_passed_using_partial_instead_of_direct_call(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    def foo(self):
                        pass

                def say_foo(*args, **kwargs):
                    for key, value in kwargs.items():
                        value.foo()


                say_foo_partial = partial(say_foo, instance=Foo())
                say_foo_partial()
                """
    }

    # When
    main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})
