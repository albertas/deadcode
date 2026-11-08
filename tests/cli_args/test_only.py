from deadcode.cli import main
from deadcode.utils.fix_indent import fix_indent


def test_output_is_provided_only_for_files_in_only_option(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
        'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
    }

    # When
    unused_names = main('. --only foo.py --no-color'.split())

    # Then
    assert unused_names == fix_indent(
        """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used"""
    )

    virtual_file_system.assert_files(
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


def test_files_are_modified_only_for_files_in_only_option(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this line")""",
        'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
    }

    # When
    unused_names = main('. --only foo.py --no-color --fix'.split())

    # Then
    assert unused_names == fix_indent(
        """\
                foo.py:1:0: DC03 Class `UnusedClass` is never used\n
                Removed 1 unused code item!"""
    )

    # virtual_file_system.assert_files(
    #     {
    #         'bar.py': b"""
    #         def unused_function():
    #             pass

    #         print("Dont change this file")""",
    #         'foo.py': b"""
    #         print("Dont change this line")""",
    #     }
    # )


def test_diffs_are_provided_only_for_files_in_only_option(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    pass

                print("Dont change this file")""",
        'bar.py': b"""
                def unused_function():
                    pass

                print("Dont change this file")""",
    }

    # When
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--dry', '--only', 'foo.py'])

    # Then
    assert unused_names == fix_indent(
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
    )

    virtual_file_system.assert_files(
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
