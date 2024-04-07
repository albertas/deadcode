"""
Test class def.
"""

from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


@skip
class TestVariableScopeTracking(BaseTestCase):
    def test_same_variable_name_is_used_for_two_different_classes(self):
        """Usage of the class methods should be tracked properly."""
        self.files = {
            'foo.py': """
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

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_function(self):
        """Usage of the class methods should be tracked properly."""
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass

                def say_foo(some_instance):
                    some_instance.foo()

                say_foo(Foo())
                """
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_function_using_args(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass

                def say_foo(*args):
                    for var in args:
                        var.foo()

                say_foo(Foo())
                """
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_function_using_kwargs(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass

                def say_foo(*args, **kwargs):
                    for key, value in kwargs.items():
                        value.foo()

                say_foo(instance=Foo())
                """
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_method_using_kwargs(self):
        self.files = {
            'foo.py': """
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

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_class_method_using_kwargs(self):
        self.files = {
            'foo.py': """
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

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_passed_into_a_static_method_using_kwargs(self):
        self.files = {
            'foo.py': """
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

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_imported(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass
                """,
            'bar.py': """
                from foo import Foo
                print(Foo().foo())
                """,
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_instance_is_being_imported_with_renaming(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass
                """,
            'bar.py': """
                from foo import Foo as Bar
                print(Bar().foo())
                """,
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_variable_renaming(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass

                instance = Foo()
                instnace2 = instance
                print(instnace2.foo())
                """
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_variable_renaming_using_expansion_from_a_list(self):
        self.files = {
            'foo.py': """
                class Foo:
                    def foo(self):
                        pass

                instance = Foo()
                instnace2, remaining_values* = [instance, 1, 2, 3]
                print(instnace2.foo())
                """,
        }

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})

    def test_function_arguments_are_being_passed_using_partial_instead_of_direct_call(self):
        self.files = {
            'foo.py': """
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

        main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})
