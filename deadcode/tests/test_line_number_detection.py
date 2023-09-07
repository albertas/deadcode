from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class DetectLineNumbersOfExpressionsTests(BaseTestCase):
    def test_parse_variable_names_from_files(self):
        # Having
        self.files = {
            "variables.py": """
                foo = None
                bar, spam, eggs = 1, 2, 3
            """
        }

        # When
        unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "4")

    def test_parse_function_names_from_files(self):
        # Having
        self.files = {
            "functions.py": """
                def foo(an_arg: str):
                    return an_arg
                """
        }

        # When
        unused_name_count = main(["functions.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "1")

    def test_parse_class_names_from_files(self):
        # Having
        self.files = {
            "classes.py": """
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
        unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "4")

    def test_parse_lambda_function_names_from_files(self):
        # Having
        self.files = {
            "variables.py": """
                my_func = lambda x: x 
                """
        }

        # When
        unused_name_count = main(["ignore_names_by_pattern.py", "--no-color", "--count"])

        # Then
        self.assertEqual(unused_name_count, "1")

    # def test_parse_class_names_from_files(self):
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
