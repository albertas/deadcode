import ast

from deadcode.cli import main
from deadcode.visitor.lines import get_last_line_number


def test_parse_variable_names_from_files(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'variables.py': b"""
                foo = None
                bar, spam, eggs = 1, 2, 3
            """
    }

    # When
    unused_name_count = main(['ignore_names_by_pattern.py', '--no-color', '--count'])

    # Then
    assert unused_name_count == '4'


def test_parse_function_names_from_files(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'functions.py': b"""
                def foo(an_arg: str):
                    return an_arg
                """
    }

    # When
    unused_name_count = main(['functions.py', '--no-color', '--count'])

    # Then
    assert unused_name_count == '1'


def test_parse_class_names_from_files(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'classes.py': b"""
                class Foo:
                    bar = None
                    spam = None

                    def eggs(self):
                        return None

                class Bar(Foo):
                    pass
                """
    }

    # When
    unused_name_count = main(['ignore_names_by_pattern.py', '--no-color', '--count'])

    # Then
    # `Foo` is cascaded away too: its only user, the dead class `Bar`, is reported.
    assert unused_name_count == '5'


def test_parse_lambda_function_names_from_files(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'variables.py': b"""
                my_func = lambda x: x
                """
    }

    # When
    unused_name_count = main(['ignore_names_by_pattern.py', '--no-color', '--count'])

    # Then
    assert unused_name_count == '1'


# def test_parse_class_names_from_files(virtual_file_system):
#     # Having
#     self.files = {
#         "ignore_names_by_pattern.py": d("""
#             foo = None
#             bar, spam, eggs = 1, 2, 3

#             class MyModel:
#                 pass

#             class MyUserModel:
#                 pass

#             class Unused:
#                 pass

#             class ThisClassShouldBeIgnored:
#                 pass
#             """)
#     }

#     # When
#     unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

#     # Then
#     self.assertEqual(unused_name_count, "4")


def test_last_child_without_line_number_is_skipped():
    # Having
    last_child = ast.arg(arg='value')
    node = ast.arguments(
        posonlyargs=[],
        args=[last_child],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    node.lineno = 7

    # When
    last_line_number = get_last_line_number(node)

    # Then
    assert last_line_number == 7
