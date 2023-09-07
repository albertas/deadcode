from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class IgnoreNamesByPatternTests(BaseTestCase):
    def test_ignore_names_matched_by_word_and_group_regexp_patterns(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
        }
        # unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=\\w*Model,.*[Ii]{1}gnore.*"])
        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=*Model,*[Ii]gnore*"])

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:7:0: DC100 Global Unused is never used"),
        )

    def test_ignore_names_matched_by_dot_regexp_pattern(self):
        # TODO: README has to be updated to not use .*, use * instead.
        # TODO: Ignoring does not work as expected: wild cards have to be used.

        self.files = {
            "ignore_names_by_pattern.py": """
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color", "--ignore-names=*Model,*Ignore*"])

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:7:0: DC100 Global Unused is never used"),
        )

    def test_ignore_names_matched_exactly(self):
        self.files = {
            "ignore_names_by_pattern.py": """
                class MyModel:
                    pass

                class MyUserModel:
                    pass

                class Unused:
                    pass

                class ThisClassShouldBeIgnored:
                    pass
                """
        }
        unused_names = main(
            ["ignore_names_by_pattern.py", "--no-color", "--ignore-names=MyModel,MyUserModel,ThisClassShouldBeIgnored"]
        )

        self.assertEqual(
            unused_names,
            ("ignore_names_by_pattern.py:7:0: DC100 Global Unused is never used"),
        )
