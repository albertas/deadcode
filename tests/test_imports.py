from deadcode.cli import main


def test_variable_is_imported_as_an_alias_but_unused(virtual_file_system):
    # Variable is used, because its imported in another file
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b'from foo import used_var as foo_var; print(foo_var)',
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names is None


def test_variable_is_used_if_its_imported_as_a_different_name(virtual_file_system):
    # Variable is used, because its imported in another file
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                from foo import used_var as foo_var
                print(foo_var)""",
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names is None


def test_module_imported_and_var_from_it_is_used(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                import foo
                print(foo.used_var)""",
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    # Attribute(value=Name(id='foo', ctx=Load()), attr='used_var', ctx=Load())
    assert unused_names is None


def test_module_imported_with_alias_and_var_from_it_is_used(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b'used_var = None',
        'bar.py': b"""
                import foo as f
                print(f.used_var)""",
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names is None


def test_relative_module_imports(virtual_file_system):
    # TODO: add more relative import tests
    # https://docs.python.org/3/tutorial/modules.html#intra-package-references
    virtual_file_system.files = {
        'eggs/foo.py': b'used_var = None',
        'eggs/spam/bar.py': b"""
                from .. import foo as f
                print(f.used_var)""",
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names is None


def test_file_contains_syntax_error(virtual_file_system):
    virtual_file_system.files = {'foo.py': b'unused_var = None this is syntax error'}
    unused_names = main(['foo.py', '--no-color'])
    assert unused_names is None

    # The same check works without a Syntax error
    virtual_file_system.files = {'foo.py': b'unused_var = None'}
    unused_names = main(['foo.py', '--no-color'])
    assert unused_names == 'foo.py:1:0: DC01 Variable `unused_var` is never used'


def test_ignore_variable_names_in_comments(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                # unused_variable is empty
                unused_var = None  # This is a comment about unused_var
                # Another comment about unused variable
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names == 'foo.py:2:0: DC01 Variable `unused_var` is never used'


def test_ignore_variable_names_in_strings(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                '''
                unused_var initial value is None - this a string about unused_variable
                '''
                unused_var = None
                print("This is another string about unused_variable")
                """
    }
    unused_names = main(['ignore_names_by_pattern.py', '--no-color'])
    assert unused_names == 'foo.py:4:0: DC01 Variable `unused_var` is never used'


# TODO:
def test_unused_names_found_in_subdirectories():
    pass


def test_exclude_option():
    pass


def test_ignore_names_in_files_option():
    pass
