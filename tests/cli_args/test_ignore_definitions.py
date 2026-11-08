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


def test_ignore_function_definition(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                def unused_function(unused_parameter: str = "") -> None:
                    unused_local_var = 123

                    def unused_inner_function() -> None:
                        pass
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=unused_function', '--fix'])

    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                def unused_function(unused_parameter: str = "") -> None:
                    unused_local_var = 123

                    def unused_inner_function() -> None:
                        pass
                """
        }
    )


def test_ignore_method_and_property_definitions(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class UsedClass:
                    def unused_method(self) -> None:
                        unused_local_var = 123

                    @property
                    def unused_property(self) -> int:
                        return 1

                UsedClass()
                """
    }
    unused_names = main(
        [
            'ignore_names_by_pattern.py',
            '--no-color',
            '--ignore-definitions=unused_method,unused_property',
            '--fix',
        ]
    )

    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class UsedClass:
                    def unused_method(self) -> None:
                        unused_local_var = 123

                    @property
                    def unused_property(self) -> int:
                        return 1

                UsedClass()
                """
        }
    )


def test_ignore_nested_class_definition(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class OuterClass:
                    class InnerClass:
                        inner_attribute = None

                    def inner_method(self) -> None:
                        pass
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=OuterClass', '--fix'])

    assert unused_names is None

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                class OuterClass:
                    class InnerClass:
                        inner_attribute = None

                    def inner_method(self) -> None:
                        pass
                """
        }
    )


def test_ignore_inner_class_definition_only(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class OuterClass:
                    class InnerClass:
                        pass
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=InnerClass'])

    assert unused_names == ('foo.py:1:0: DC03 Class `OuterClass` is never used')


def test_ignore_definitions_does_not_ignore_module_level_variable(virtual_file_system):
    virtual_file_system.files = {'foo.py': b'\n                unused_var = 123\n                '}
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=unused_var'])

    assert unused_names == ('foo.py:1:0: DC01 Variable `unused_var` is never used')


def test_ignore_definitions_does_not_ignore_class_attribute(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class UsedClass:
                    unused_attribute = None

                UsedClass()
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=unused_attribute'])

    assert unused_names == ('foo.py:2:4: DC01 Variable `unused_attribute` is never used')


def test_ignore_definitions_does_not_ignore_import(virtual_file_system):
    virtual_file_system.files = {'foo.py': b'\n                import unused_module\n                '}
    unused_names = main(['ignore_names_by_pattern.py', '--no-color', '--ignore-definitions=unused_module'])

    assert unused_names == ('foo.py:1:7: DC07 Import `unused_module` is never used')
