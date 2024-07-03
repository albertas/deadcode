from unittest import TestCase
from deadcode.utils.fix_indent import fix_indent

from deadcode.utils.add_colors_to_diff import add_colors_to_diff


class TestAddColorsToDiff(TestCase):
    def test_add_colors_to_diff(self):
        diff = fix_indent(
            b"""\
            --- foo.py
            +++ foo.py
            @@ -1,4 +1 @@
            -class UnusedClass:
            -    pass
            -
            -with open("tmp.txt") as f:
            +with open("tmp.txt"):
                pass"""
        )

        colorful_diff = add_colors_to_diff(diff)

        self.assertEqual(
            colorful_diff,
            fix_indent(
                b"""\
            \x1b[31m--- foo.py\x1b[0m
            \x1b[32m+++ foo.py\x1b[0m
            @@ -1,4 +1 @@
            \x1b[31m-class UnusedClass:\x1b[0m
            \x1b[31m-    pass\x1b[0m
            \x1b[31m-\x1b[0m
            \x1b[31m-with open("tmp.txt") as f:\x1b[0m
            \x1b[32m+with open("tmp.txt"):\x1b[0m
                pass"""
            ),
        )
