from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestUnreachableCodeIsNotRemoved(BaseTestCase):
    def test_else_is_not_changed_when_condition_is_true(self):
        self.files = {
            "foo.py": """
                if True:
                    print("Main block")
                else:
                    print("Else block")
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])
        self.assertIsNone(result)

        self.assertFiles(
            {
                "foo.py": """
                if True:
                    print("Main block")
                else:
                    print("Else block")
                """
            }
        )

    def test_else_is_not_changed_when_condition_is_false(self):
        self.files = {
            "foo.py": """
                if False:
                    print("Main block")
                else:
                    print("Else block")
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])
        self.assertIsNone(result)

        self.assertFiles(
            {
                "foo.py": """
                if False:
                    print("Main block")
                else:
                    print("Else block")
                """
            }
        )

    def test_while_is_not_changed_when_condition_is_true(self):
        self.files = {
            "foo.py": """
                while True:
                    print("Main block")
                else:
                    print("Else block")
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])
        self.assertIsNone(result)

        self.assertFiles(
            {
                "foo.py": """
                while True:
                    print("Main block")
                else:
                    print("Else block")
                """
            }
        )

    def test_while_is_not_changed_when_condition_is_false(self):
        self.files = {
            "foo.py": """
                while False:
                    print("Main block")
                else:
                    print("Else block")
                """
        }

        result = main(["foo.py", "--no-color", "--fix"])
        self.assertIsNone(result)

        self.assertFiles(
            {
                "foo.py": """
                while False:
                    print("Main block")
                else:
                    print("Else block")
                """
            }
        )
