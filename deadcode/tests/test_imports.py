from unittest import skip

from deadcode.cli import main
from deadcode.tests.base import BaseTestCase


@skip("NotImplemented")
class NonImplementedUseCaseTests(BaseTestCase):
    def setUp(self):
        self.read_files_mock = self.patch("deadcode.cli.read_files")

    def test_variable_is_used_if_its_imported_as_a_different_name(self):
        # Variable is used, because its imported in another file
        self.read_files_mock.return_value = {
            "foo.py": "used_var = None",
            "bar.py": "from foo import used_var as foo_var",
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names is None

    def test_module_imported_and_var_from_it_is_used(self):
        # TODO: Not working case.
        self.read_files_mock.return_value = {
            "foo.py": "used_var = None",
            "bar.py": """\
import foo
print(foo.used_var)
""",
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        # Attribute(value=Name(id='foo', ctx=Load()), attr='used_var', ctx=Load())
        assert unused_names is None

    def test_module_imported_with_alias_and_var_from_it_is_used(self):
        # TODO: Not working case.
        self.read_files_mock.return_value = {
            "foo.py": "used_var = None",
            "bar.py": """\
import foo as f
print(f.used_var)
""",
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names is None

    def test_relative_module_imports(self):
        # TODO: Not working case.
        # https://docs.python.org/3/tutorial/modules.html#intra-package-references
        self.read_files_mock.return_value = {
            "eggs/foo.py": "used_var = None",
            "eggs/spam/bar.py": """\
from .. import foo as f
print(f.used_var)
""",
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names is None

    def test_file_contains_syntax_error(self):
        self.read_files_mock.return_value = {"foo.py": "unused_var = None this is syntax error"}
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names is None

        # The same check works without a Syntax error
        self.read_files_mock.return_value = {"foo.py": "unused_var = None"}
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names == "foo.py:1:0: DC100 Global unused_var is never used"

    def test_ignore_variable_names_in_comments(self):
        self.read_files_mock.return_value = {
            "foo.py": """
# unused_variable is empty
unused_var = None  # This is a comment about unused_var
# Another comment about unused variable
"""
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names == "foo.py:3:0: DC100 Global unused_var is never used"

    def test_ignore_variable_names_in_strings(self):
        self.read_files_mock.return_value = {
            "foo.py": """
'''
unused_var initial value is None - this a string about unused_variable
'''
unused_var = None
print("This is another string about unused_variable")
"""
        }
        unused_names = main(["ignore_names_by_pattern.py", "--no-color"])
        assert unused_names == "foo.py:5:0: DC100 Global unused_var is never used"

    # TODO:
    def test_unused_names_found_in_subdirectories(self):
        pass

    def test_exclude_option(self):
        pass

    def test_ignore_names_in_files_option(self):
        pass
