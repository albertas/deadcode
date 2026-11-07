from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class WildcardImportWithAllTests(BaseTestCase):
    def test_issue_example_reports_name_excluded_by_all(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo', 'bar']

                foo = 1
                bar = 2
                spam = 3
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names == 'foo.py:5:0: DC01 Variable `spam` is never used'

    def test_name_exported_by_all_is_not_reported(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo', 'bar']

                foo = 1
                bar = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_name_excluded_by_all_is_reported_for_variables_and_functions(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['exported']
                exported = 1
                hidden = 2


                def hidden_function():
                    return 1
            """,
            'bar.py': b"""
                from foo import *

                print(exported)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names == (
            'foo.py:3:0: DC01 Variable `hidden` is never used\n'
            'foo.py:6:0: DC02 Function `hidden_function` is never used'
        )

    def test_wildcard_import_from_unanalysed_module_keeps_current_behaviour(self):
        self.files = {
            'bar.py': b"""
                from external_module import *

                print(anything)
            """,
        }
        unused_names = main(['bar.py', '--no-color'])
        assert unused_names is None

    def test_wildcard_import_itself_is_not_reported(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo']

                foo = 1
            """,
            'bar.py': b'from foo import *',
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_attribute_access_still_suppresses_name_excluded_by_all(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo']

                foo = 1
                spam = 2
            """,
            'bar.py': b"""
                import foo

                print(foo.spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_bare_name_used_in_defining_module_is_not_reported(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo']

                foo = 1
                spam = 2
                print(spam)
            """,
            'bar.py': b'from foo import *',
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None


class WildcardImportWithDynamicAllTests(BaseTestCase):
    def test_all_built_by_concatenation_does_not_restrict(self):
        self.files = {
            'foo.py': b"""
                base = ['foo']
                __all__ = base + ['bar']

                foo = 1
                bar = 2
                spam = 3
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_all_augmented_assignment_does_not_restrict(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo']
                __all__ += ['bar']

                foo = 1
                bar = 2
                spam = 3
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_all_comprehension_does_not_restrict(self):
        self.files = {
            'foo.py': b"""
                __all__ = [name for name in ['foo']]

                foo = 1
                spam = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_non_string_all_element_does_not_restrict(self):
        self.files = {
            'foo.py': b"""
                name = 'foo'
                __all__ = ['foo', name]

                foo = 1
                spam = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_conditional_all_does_not_restrict(self):
        self.files = {
            'foo.py': b"""
                if True:
                    __all__ = ['foo']

                foo = 1
                spam = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_explicitly_imported_name_is_used_despite_wildcard_import(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo']

                foo = 1
                _private = 2
            """,
            'bar.py': b"""
                from foo import *
                from foo import _private

                print(_private)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_module_without_all_is_still_unrestricted(self):
        self.files = {
            'foo.py': b"""
                foo = 1
                spam = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None


class WildcardImportPublicDefaultTests(BaseTestCase):
    def test_private_function_excluded_from_wildcard_is_reported(self):
        self.files = {
            'foo.py': b"""
                def public_function(): ...
                def _private_function(): ...
            """,
            'bar.py': b"""
                from foo import *

                public_function()
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names == 'foo.py:2:0: DC02 Function `_private_function` is never used'

    def test_public_function_used_only_through_wildcard_is_not_reported(self):
        self.files = {
            'foo.py': b"""
                def public_function(): ...
            """,
            'bar.py': b"""
                from foo import *

                public_function()
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_empty_all_reports_every_other_name(self):
        self.files = {
            'foo.py': b"""
                __all__ = []
                foo = 1
                bar = 2
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names == (
            'foo.py:2:0: DC01 Variable `foo` is never used\n'
            'foo.py:3:0: DC01 Variable `bar` is never used'
        )

    def test_names_not_defined_at_module_level_are_not_exported(self):
        self.files = {
            'foo.py': b"""
                def public_function():
                    local_name = 1
                    return local_name
            """,
            'bar.py': b"""
                from foo import *

                public_function()
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_attribute_access_still_suppresses_name_excluded_by_empty_all(self):
        self.files = {
            'foo.py': b"""
                __all__ = []
                spam = 1
            """,
            'bar.py': b"""
                import foo

                print(foo.spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names is None

    def test_issue_example_still_reports_only_spam(self):
        self.files = {
            'foo.py': b"""
                __all__ = ['foo', 'bar']

                foo = 1
                bar = 2
                spam = 3
            """,
            'bar.py': b"""
                from foo import *

                print(foo)
                print(bar)
                print(spam)
            """,
        }
        unused_names = main(['foo.py', 'bar.py', '--no-color'])
        assert unused_names == 'foo.py:5:0: DC01 Variable `spam` is never used'
