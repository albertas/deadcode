from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


class TestNoqaComments(BaseTestCase):
    def test_unused_class_is_unchanged_if_noqa_comment_is_provided(self):
        self.files = {
            "foo.py": """
                class MyTest:  # noqa: DC003
                    pass
                """
        }

        unused_names = main(["foo.py", "--no-color", "--fix"])

        self.assertFiles(
            {
                "foo.py": """
                class MyTest:  # noqa: DC003
                    pass
                """
            }
        )

        self.assertEqual(unused_names, None)
