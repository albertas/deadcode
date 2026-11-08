from deadcode.cli import main


def test_unused_class_is_unchanged_if_noqa_comment_is_provided(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:  # noqa: DC03
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                instance = "labas"  # noqa
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                instance = "labas"  # noqa
                """
        }
    )

    assert unused_names is None


def test_noqa_dc_suppresses_every_check_on_the_line(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:  # noqa: DC
                    pass

                unused_variable = 1  # noqa: DC
                unused_other = 2
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:5:0: DC01 Variable `unused_other` is never used'


def test_unused_variable(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC01
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                unused_variable = "Hello"  # noqa: DC02
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files({})
    assert unused_names == 'foo.py:1:0: DC01 Variable `unused_variable` is never used\n\n' 'Removed 1 unused code item!'


def test_unused_function(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    def unused_method(self):  # noqa: DC04
                        pass

                instance = MyTest()
                print(instance)
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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


def test_unused_attribute(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    def __init__(self):
                        self.unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class MyTest:
                    def __init__(self):
                        self.unused_attribute = 123  # noqa: DC05

                instance = MyTest()
                print(instance)
                """
        }
    )

    assert unused_names is None


def test_unused_name(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class MyTest:
                    unused_attribute = 123  # noqa: DC06

                instance = MyTest()
                print(instance)
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                from typing import Optional  # noqa: DC07
                """
        }
    )

    assert unused_names is None


def test_unused_property(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Foo:
                    @property
                    def bar(self):  # noqa: DC08
                        return None
                Foo()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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


def test_unreachable_code(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                if True:
                    pass
                else:  # noqa: DC09
                    print("Hello world")
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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

    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                # noqa: DC11
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                # noqa: DC11
                """
        }
    )

    assert unused_names is None


def test_commented_out_code(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                # print("Hello world")  # noqa: DC12
                """
        }
    )

    assert unused_names is None


def test_unreachable_code_after_return(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function():
                    return 1
                    print("Hello world")  # noqa: DC13
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                def unused_function():
                    return 1
                    print("Hello world")  # noqa: DC13
                """
        }
    )

    assert unused_names == 'foo.py:1:0: DC02 Function `unused_function` is never used'


def test_unused_decorated_function_definition_line_with_alias(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def unused_function():  # noqa: DC002
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @first
                @second
                @third
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache(maxsize=None)
                def unused_function():  # noqa: DC02
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                async def unused_function():  # noqa: DC02
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def unused_function():  # noqa
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache  # noqa: DC02
                def unused_function():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                class MyTest:  # noqa: DC03
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
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

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
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
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @cache
                def check(arg):  # noqa: DC01
                    pass

                value = 1
                print(value)
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_updated_files({'foo.py': b'value = 1\nprint(value)\n'})
    assert unused_names == 'foo.py:2:0: DC02 Function `check` is never used\n\n' 'Removed 1 unused code item!'
