import pytest

from deadcode.cli import main


def test_unused_class_was_removed(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                class UnusedClass:
                    pass

                print("Keep the file")
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'ignore_names_by_pattern.py:1:0: DC03 Class `UnusedClass` is never used\n\n' 'Removed 1 unused code item!'
    )

    virtual_file_system.assert_files(
        {
            'ignore_names_by_pattern.py': b"""
            print("Keep the file")
        """
        }
    )


def test_function_removal(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                def foo(bar: str = "Bar") -> str:
                    return 1 ** 2

                print("Keep the file")
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'ignore_names_by_pattern.py:1:0: DC02 Function `foo` is never used\n\n' 'Removed 1 unused code item!'
    )

    virtual_file_system.assert_files(
        {
            'ignore_names_by_pattern.py': b"""
                print("Keep the file")
        """
        }
    )


# TODO: treat variables unused if they are referenced only by other unused code.


def test_function_removal_in_the_middle(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                used_variable = "one"

                def foo(bar: str = "Bar") -> str:
                    return 1 ** 2

                spam = "Spam"
                print(spam, used_variable)
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'ignore_names_by_pattern.py:3:0: DC02 Function `foo` is never used\n\n' 'Removed 1 unused code item!'
    )

    virtual_file_system.assert_files(
        {
            'ignore_names_by_pattern.py': b"""
                used_variable = "one"

                spam = "Spam"
                print(spam, used_variable)
                """
        }
    )


def test_function_removal_of_several_items(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'ignore_names_by_pattern.py': b"""
                used_variable = "one"

                unused_variable = ""

                def unused_function(bar: str = "Bar") -> str:
                    return 1 ** 2

                spam = "Spam"
                print(spam, used_variable)
                """
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    assert unused_names == (
        'ignore_names_by_pattern.py:3:0: DC01 Variable `unused_variable` is never used\n'
        'ignore_names_by_pattern.py:5:0: DC02 Function `unused_function` is never used\n\n'
        'Removed 2 unused code items!'
    )

    virtual_file_system.assert_files(
        {
            'ignore_names_by_pattern.py': b"""
                used_variable = "one"

                spam = "Spam"
                print(spam, used_variable)
                """
        }
    )


def test_empty_lines_are_removed_properly_indented(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                    name = "World"

                    unused_variable = "This variable is unused"


                    def say_hello_world():
                        print(f"Hello {name}")


                    def unused_function():
                        pass


                    say_hello_world()


                    class Example:
                        def unused_method(self):
                            pass

                        def foo(self):
                            another_unused_variable = "Hello world"

                            with open("example.txt") as unused_file:
                                print("File was openned")


                    class UnusedClass:
                        def unused_method(self):
                            pass


                    instance = Example()
                    print(instance.foo())
                """
    }

    # When
    main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                    name = "World"

                    def say_hello_world():
                        print(f"Hello {name}")


                    say_hello_world()


                    class Example:
                        def foo(self):
                            with open("example.txt"):
                                print("File was openned")


                    instance = Example()
                    print(instance.foo())
                """
        }
    )


def test_empty_lines_are_removed_properly(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                NAME = "World"

                UNUSED_VARIABLE = "This variable is unused"


                def say_hello_world():
                    print(f"Hello {NAME}")


                def unused_function():
                    pass


                say_hello_world()


                class Example:
                    def foo(self):
                        pass


                class UnusedClass:
                    def unused_method(self):
                        pass


                instance = Example()
                print(instance.foo())
                """
    }

    # When
    main(['ignore_names_by_pattern.py', '--no-color', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                    NAME = "World"

                    def say_hello_world():
                        print(f"Hello {NAME}")


                    say_hello_world()


                    class Example:
                        def foo(self):
                            pass


                    instance = Example()
                    print(instance.foo())
                """
        }
    )


def test_empty_class_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            class Example:
                def unused_method(self):
                    print("Unused method")

            example = Example()
            print(example)
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            class Example:
                pass

            example = Example()
            print(example)
            """
        }
    )


def test_empty_function_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            def foo():
                bar = 1

            foo()
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            def foo():
                pass

            foo()
            """
        }
    )


def test_empty_if_main_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            import sys

            if sys.argv[1:]:
                unused = 1
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            import sys

            if sys.argv[1:]:
                pass
            """
        }
    )


def test_empty_if_else_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            if spam:
                bar = 1
                print(bar)
            else:
                unused = 1
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            if spam:
                bar = 1
                print(bar)
            else:
                pass
            """
        }
    )


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_empty_if_statement_else_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            if spam:
                bar = 1
                print(bar)
            else:
                pass
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            if spam:
                bar = 1
                print(bar)
            """
        }
    )


@pytest.mark.skip(reason='Skipped without a recorded reason before the pytest migration; behaviour preserved')
def test_if_is_not_fixed_correctly_when_branch_is_unreachable(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            if False:
                bar = 1
                print(bar)
            else:
                unused = 1
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            if True:
                pass
            """
        }
    )


def test_empty_with_block(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            with open("tmp.txt") as f:
                unused = 1
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            with open("tmp.txt"):
                pass
            """
        }
    )


def test_empty_block_is_at_the_end_of_file():
    # Having
    pass  # tested by test_empty_with_block


def test_some_code_follows_empty_block():
    # Having
    pass  # tested by test_empty_class_block


def test_space_is_kept_after_whole_class_block_removal(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            class Example:
                def unused_method(self):
                    print("Unused method")

            example = Example()
            print(example)
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            class Example:
                pass

            example = Example()
            print(example)
            """
        }
    )


def test_two_spaces_are_kept_after_whole_class_block_removal(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            class Example:
                def unused_method(self):
                    print("Unused method")


            example = Example()
            print(example)
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            class Example:
                pass


            example = Example()
            print(example)
            """
        }
    )


def test_two_spaces_are_kept_after_one_method_removal(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            class Example:
                def unused_method(self):
                    print("Unused method")

                def used_method(self):
                    print("Used method")


            example = Example()
            print(example.used_method())
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            class Example:
                def used_method(self):
                    print("Used method")


            example = Example()
            print(example.used_method())
            """
        }
    )


def test_assignment(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
            bar = 1
            print("Keep the file")
            """
    }

    # When
    main(['.', '--fix'])

    # Then
    virtual_file_system.assert_files(
        {
            'foo.py': b"""
            print("Keep the file")
        """
        }
    )
