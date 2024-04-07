from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestIgnoreDefinitionsByPattern(BaseTestCase):
    def test_ignore_class_definition(self):
        self.files = {
            'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
        unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=UnusedClass', '--fix'])

        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
            }
        )

    def test_ignore_class_definition_another_class_is_detected(self):
        self.files = {
            'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""

                class AnotherUnusedClass:
                    pass
                """
        }
        unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=UnusedClass', '--fix'])

        self.assertEqual(
            unused_names,
            ('foo.py:10:0: DC03 Class `AnotherUnusedClass` is never used\n\nRemoved 1 unused code item!'),
        )

        self.assertFiles(
            {
                'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
            }
        )

    def test_ignore_class_definition_matched_by_pattern(self):
        self.files = {
            'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
        unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=Unused*', '--fix'])

        self.assertEqual(unused_names, None)

        self.assertFiles(
            {
                'foo.py': """
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
            }
        )
