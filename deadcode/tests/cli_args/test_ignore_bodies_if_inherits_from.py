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

        output = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-bodies-if-inherits-from=Base", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class Base:
                    pass
                """
            }
        )

        self.assertEqual(
            output,
            "foo.py:5:0: DC03 Class `UnusedClass` is never used\n"
            "foo.py:15:0: DC03 Class `AnotherUnusedClass` is never used\n"
            "foo.py:16:4: DC01 Variable `another_unused_attribute` is never used\n"
            "\n"
            "Removed 3 unused code items!",
        )
