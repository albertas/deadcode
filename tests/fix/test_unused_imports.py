"""
Test unused import detection and removal.
"""

from unittest import skip

from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestAssignmentExpressionRemoval(BaseTestCase):
    def test_variable(self):
        self.files = {
            'file2.py': b"""
                from file1 import (
                    foo,
                    bar,
                    xyz
                )

                from file1 import foo

                def fn():
                    pass

                fn()
                """
        }

        unused_names = main('file2.py --no-color --fix -v'.split())

        self.assertEqual(
            unused_names,
            fix_indent("""\
                file2.py:2:4: DC07 Import `foo` is never used
                file2.py:3:4: DC07 Import `bar` is never used
                file2.py:4:4: DC07 Import `xyz` is never used
                file2.py:7:18: DC07 Import `foo` is never used

                Removed 4 unused code items!"""),
        )

        # TODO: empty imports statements should be removed as well.
        self.assertFiles(
            {
                'file2.py': b"""
                    from file1 import (
                    )
                    from file1 import 


                    def fn():
                        pass

                    fn()
                    """
            }
        )
