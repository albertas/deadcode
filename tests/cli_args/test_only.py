from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.utils.fix_indent import fix_indent


class TestOnlyCliOption(BaseTestCase):
    def test_output_is_provided_only_for_files_in_only_option(self):
        self.files = {
            'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        unused_names = main('. --only foo.py --no-color'.split())

        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used"""
            ),
        )

        self.assertFiles(
            {
                'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
                'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
            }
        )

    def test_files_are_modified_only_for_files_in_only_option(self):
        self.files = {
            'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this line")""",
            'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        unused_names = main('. --only foo.py --no-color --fix'.split())

        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used\n
                Removed 1 unused code item!"""
            ),
        )

        # self.assertFiles(
        #     {
        #         'bar.py': b"""
        #         def unused_function():
        #             pass

        #         print("Dont change this file")""",
        #         'foo.py': b"""
        #         print("Dont change this line")""",
        #     }
        # )

    def test_diffs_are_provided_only_for_files_in_only_option(self):
        self.files = {
            'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
            'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
        }

        unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--dry', '--only', 'foo.py'])
        self.assertEqual(
            unused_names,
            fix_indent(
                """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used

                --- foo.py
                +++ foo.py
                @@ -1,4 +1 @@
                -class UnusedClass:
                -    pass
                -
                 print("Dont change this file")
            """
            ),
        )

        self.assertFiles(
            {
                'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
                'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
            }
        )
