from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestNoqaComments(BaseTestCase):
    def test_unused_class_is_unchanged_if_noqa_comment_is_provided(self):
        self.files = {
            'foo.py': b"""
                class MyTest:  # noqa: DC03
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class MyTest:  # noqa: DC03
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_noqa_all(self):
        self.files = {
            'foo.py': b"""
                instance = "labas"  # noqa
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                instance = "labas"  # noqa
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_variable(self):
        self.files = {
            'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC01
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC01
                    pass
                """
            }
        )

    def test_unused_variable_but_wrong_noqa_specified(self):
        self.files = {
            'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC02
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles({})
        self.assertEqual(
            unused_names,
            ('foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'),
        )

    def test_unused_function(self):
        self.files = {
            'foo.py': b"""
                def unused_function():  # noqa: DC02
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])
        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                'foo.py': b"""
                def unused_function():  # noqa: DC02
                    pass
                """
            }
        )

    def test_unused_method(self):
        self.files = {
            'foo.py': b"""
                class MyTest:
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class MyTest:
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unused_attribute(self):
        # TODO: DC05 does not work.
        self.files = {
            'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unused_name(self):
        # TODO: DC06 does not work.
        self.files = {
            'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC06

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC06

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_import(self):
        self.files = {
            'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_property(self):
        self.files = {
            'foo.py': b"""
                class Foo:
                    @property
                    def bar(self):  # noqa: DC08
                        return None
                Foo()
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class Foo:
                    @property
                    def bar(self):  # noqa: DC08
                        return None
                Foo()
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_unreachable_code(self):
        # TODO: identify all cases, when unreachable code is detected, and write unit tests

        self.files = {
            'foo.py': b"""
                if True:
                    pass
                else:  # noqa: DC09
                    print("Hello world")
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                if True:
                    pass
                else:  # noqa: DC09
                    print("Hello world")
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_empty_file(self):
        # TODO: this test passes only because comment is treated as non empty file content
        self.files = {
            'foo.py': b"""
                # noqa: DC11
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                # noqa: DC11
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_commented_out_code(self):
        # TODO: this test only passes because commented-out-code check is not yet implemented
        self.files = {
            'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
            }
        )

        self.assertEqual(unused_names, None)

    @skip
    def test_ignore_expression(self):
        self.files = {
            'foo.py': b"""
                class Foo:  # noqa: DC13
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class Foo:  # noqa: DC13
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_definition_line_with_alias(self):
        self.files = {
            'foo.py': b"""
                @cache
                def unused_function():  # noqa: DC002
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache
                def unused_function():  # noqa: DC002
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_stacked_decorators(self):
        self.files = {
            'foo.py': b"""
                @first
                @second
                @third
                def unused_function():  # noqa: DC02
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @first
                @second
                @third
                def unused_function():  # noqa: DC02
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_decorator_with_arguments(self):
        self.files = {
            'foo.py': b"""
                @cache(maxsize=None)
                def unused_function():  # noqa: DC02
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache(maxsize=None)
                def unused_function():  # noqa: DC02
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_async_function(self):
        self.files = {
            'foo.py': b"""
                @cache
                async def unused_function():  # noqa: DC02
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache
                async def unused_function():  # noqa: DC02
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_bare_noqa(self):
        self.files = {
            'foo.py': b"""
                @cache
                def unused_function():  # noqa
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache
                def unused_function():  # noqa
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_noqa_on_first_decorator_line(self):
        self.files = {
            'foo.py': b"""
                @cache  # noqa: DC02
                def unused_function():
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache  # noqa: DC02
                def unused_function():
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_class_definition_line(self):
        self.files = {
            'foo.py': b"""
                @cache
                class MyTest:  # noqa: DC03
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                @cache
                class MyTest:  # noqa: DC03
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_method_definition_line(self):
        self.files = {
            'foo.py': b"""
                class MyTest:
                    @cache
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertFiles(
            {
                'foo.py': b"""
                class MyTest:
                    @cache
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
            }
        )

        self.assertEqual(unused_names, None)

    def test_unused_decorated_function_definition_line_with_wrong_noqa_code(self):
        self.files = {
            'foo.py': b"""
                @cache
                def check(arg):  # noqa: DC01
                    pass

                value = 1
                print(value)
                """
        }

        unused_names = main(['foo.py', '--no-color', '--fix'])

        self.assertUpdatedFiles({'foo.py': b'value = 1\nprint(value)\n'})
        self.assertEqual(
            unused_names,
            ('foo.py:2:0: DC02 Function `check` is never used\n\n' 'Removed 1 unused code item!'),
        )
