from deadcode.cli import main


def test_ignore_class_body_by_name(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""


                class AnotherUnusedClass:
                    another_unused_attribute = None
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-of=UnusedClass'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC03 Class `UnusedClass` is never used\n'
        'foo.py:11:0: DC03 Class `AnotherUnusedClass` is never used\n'
        'foo.py:12:4: DC06 Name `another_unused_attribute` is never used'
    )


def test_ignore_function_body_by_name(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function():
                    unused_local_var = 123

                    def unused_nested_function():
                        pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-of=unused_function'])

    # Then
    assert unused_names == ('foo.py:1:0: DC02 Function `unused_function` is never used')


def test_ignore_bodies_of_matched_by_pattern(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedFirst:
                    first_attribute = None


                class UnusedSecond:
                    second_attribute = None


                class UsedClass:
                    pass


                UsedClass()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-of=Unused*'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC03 Class `UnusedFirst` is never used\nfoo.py:5:0: DC03 Class `UnusedSecond` is never used'
    )


def test_non_matching_name_is_still_fully_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-of=Other'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC03 Class `UnusedClass` is never used\n'
        'foo.py:2:4: DC06 Name `unused_attribute` is never used\n'
        'foo.py:4:4: DC04 Method `unused_method` is never used\n'
        'foo.py:5:8: DC01 Variable `unused_local_var` is never used'
    )


def test_fix_removes_matched_item_including_its_body(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self):
                        unused_local_var = 123


                class UsedClass:
                    pass


                UsedClass()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-of=UnusedClass', '--fix'])

    # Then
    assert unused_names == ('foo.py:1:0: DC03 Class `UnusedClass` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class UsedClass:
                    pass


                UsedClass()
                """
        }
    )
