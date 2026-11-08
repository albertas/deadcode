from deadcode.cli import main


def test_ignore_class_definition(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=UnusedClass', '--fix'])

    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
    )


def test_ignore_class_definition_another_class_is_detected(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""

                class AnotherUnusedClass:
                    pass
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=UnusedClass', '--fix'])

    assert unused_names == ('foo.py:10:0: DC03 Class `AnotherUnusedClass` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
    )


def test_ignore_class_definition_matched_by_pattern(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=Unused*', '--fix'])

    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class UnusedClass:
                    unused_attribute = None

                    def unused_method(self, unused_parameter: str = "") -> None:
                        unused_local_var = 123

                    class UnusedInnerClass:
                        unused_class_attribute = ""
                """
        }
    )
