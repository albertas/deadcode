import pytest

from deadcode.cli import main


def test_unused_class_is_unchanged_if_noqa_comment_is_provided(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:  # noqa: DC03
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class MyTest:  # noqa: DC03
                    pass
                """
        }
    )

    assert unused_names is None


def test_noqa_all(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                instance = "labas"  # noqa
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                instance = "labas"  # noqa
                """
        }
    )

    assert unused_names is None


def test_unused_variable(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC01
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC01
                    pass
                """
        }
    )


def test_unused_variable_but_wrong_noqa_specified(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC02
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files({})
    assert unused_names == 'foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'


def test_unused_function(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])
    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                def unused_function():  # noqa: DC02
                    pass
                """
        }
    )


def test_unused_method(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
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

    assert unused_names is None


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_attribute(virtual_file_system):
    # TODO: DC05 does not work.
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
        }
    )

    assert unused_names is None


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unused_name(virtual_file_system):
    # TODO: DC06 does not work.
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC06

                instance = MyTest()
                print(instance)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC06

                instance = MyTest()
                print(instance)
                """
        }
    )

    assert unused_names is None


def test_unused_import(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
        }
    )

    assert unused_names is None


def test_unused_property(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    @property
                    def bar(self):  # noqa: DC08
                        return None
                Foo()
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
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

    assert unused_names is None


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_unreachable_code(virtual_file_system):
    # TODO: identify all cases, when unreachable code is detected, and write unit tests

    virtual_file_system.files = {
        'foo.py': b"""
                if True:
                    pass
                else:  # noqa: DC09
                    print("Hello world")
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                if True:
                    pass
                else:  # noqa: DC09
                    print("Hello world")
                """
        }
    )

    assert unused_names is None


def test_empty_file(virtual_file_system):
    # TODO: this test passes only because comment is treated as non empty file content
    virtual_file_system.files = {
        'foo.py': b"""
                # noqa: DC11
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                # noqa: DC11
                """
        }
    )

    assert unused_names is None


def test_commented_out_code(virtual_file_system):
    # TODO: this test only passes because commented-out-code check is not yet implemented
    virtual_file_system.files = {
        'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
        }
    )

    assert unused_names is None


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_ignore_expression(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:  # noqa: DC13
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class Foo:  # noqa: DC13
                    this_attiribute_is_unused = True

                    def this_method_is_not_used_as_well(self):
                        pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_function_definition_line_with_alias(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def unused_function():  # noqa: DC002
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache
                def unused_function():  # noqa: DC002
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_function_stacked_decorators(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @first
                @second
                @third
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
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

    assert unused_names is None


def test_unused_decorated_function_decorator_with_arguments(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache(maxsize=None)
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache(maxsize=None)
                def unused_function():  # noqa: DC02
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_async_function(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                async def unused_function():  # noqa: DC02
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache
                async def unused_function():  # noqa: DC02
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_function_bare_noqa(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def unused_function():  # noqa
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache
                def unused_function():  # noqa
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_function_noqa_on_first_decorator_line(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache  # noqa: DC02
                def unused_function():
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache  # noqa: DC02
                def unused_function():
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_class_definition_line(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                class MyTest:  # noqa: DC03
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @cache
                class MyTest:  # noqa: DC03
                    pass
                """
        }
    )

    assert unused_names is None


def test_unused_decorated_method_definition_line(virtual_file_system):
    virtual_file_system.files = {
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

    virtual_file_system.assert_files(
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

    assert unused_names is None


def test_unused_decorated_function_definition_line_with_wrong_noqa_code(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def check(arg):  # noqa: DC01
                    pass

                value = 1
                print(value)
                """
    }

    unused_names = main(['foo.py', '--no-color', '--fix'])

    virtual_file_system.assert_updated_files({'foo.py': b'value = 1\nprint(value)\n'})
    assert unused_names == 'foo.py:2:0: DC02 Function `check` is never used\n\n' 'Removed 1 unused code item!'
