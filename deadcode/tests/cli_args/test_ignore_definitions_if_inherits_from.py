from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestIgnoreDefinitionIfInheritsFrom(BaseTestCase):
    def test_ignore_class_definition_if_inherits_from_base_class(self):
        self.files = {
            "foo.py": """
                class Base:
                    pass


                class UnusedClass(Base):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
        }

        output = main(
            ["ignore_names_by_pattern.py", "--no-color", "--ignore-definitions-if-inherits-from=Base", "--fix"]
        )

        self.assertFiles(
            {
                "foo.py": """
                class Base:
                    pass


                class UnusedClass(Base):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
            }
        )

        self.assertEqual(
            output,
            "foo.py:15:0: DC003 Class `AnotherUnusedClass` is never used\n"
            "foo.py:16:4: DC001 Variable `another_unused_attribute` is never used\n"
            "\n"
            "Removed 2 unused code items!",
        )

    @skip
    def test_ignore_class_definition_if_inherits_from_multiple_classes(self):
        # TODO:
        # Implement class inheritance tracking, so that not only the first level of
        # inherited classes would be considered, but whole inheritance tree would be considered.

        self.files = {
            "foo.py": """
                class Base:
                    pass


                class Interface(Base):
                    pass


                class UnusedClass(Interface):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
        }

        output = main(
            ["ignore_names_by_pattern.py", "--no-color", "--ignore-definitions-if-inherits-from=Base", "--fix"]
        )

        self.assertFiles(
            {
                "foo.py": """
                class Base:
                    pass


                class Interface(Base):
                    pass


                class UnusedClass(Interface):
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
            }
        )

        self.assertEqual(
            output,
            "foo.py:15:0: DC003 Class `AnotherUnusedClass` is never used\n"
            "foo.py:16:4: DC001 Variable `another_unused_attribute` is never used\n"
            "\n"
            "Removed 2 unused code items!",
        )
