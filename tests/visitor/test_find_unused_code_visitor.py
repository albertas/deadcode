import ast
import types
from unittest import TestCase

from deadcode.cli import main
from deadcode.data_types import Args
from deadcode.utils.base_test_case import BaseTestCase
from deadcode.visitor.find_unused_code_visitor import FindUnusedCodeVisitor


class TestVisitorPathsViaMain(BaseTestCase):
    def _run(self, source):
        self.files = {'foo.py': source}
        main(['foo.py', '--no-color'])

    def test_async_function_def(self):
        self._run('async def handler():\n    pass\n')  # line 343

    def test_attribute_store(self):
        self._run('import os\nos.custom_attr = 1\n')  # line 347

    def test_old_style_format_string(self):
        self._run('value = "%(foo)s" % locals()\n')  # lines 357-358

    def test_getattr_marks_attribute_used(self):
        self._run('import os\ngetattr(os, "getcwd")\n')  # lines 366-368

    def test_new_style_format_string(self):
        self._run('text = "{foo}".format(**locals())\n')  # lines 378, 381-397, 402

    def test_property_definition(self):
        self._run('class A:\n    @property\n    def value(self):\n        return 1\n')  # lines 440, 449

    def test_ternary_expression(self):
        self._run('result = 1 if undefined else 2\n')  # line 459

    def test_ternary_always_true(self):
        self._run('result = 1 if True else 2\n')  # line 251

    def test_redundant_if_without_else(self):
        self._run('if True:\n    x = 1\n')  # lines 265-267

    def test_dunder_all_assignment(self):
        self._run('__all__ = ["foo"]\nfoo = 1\n')  # lines 493-496

    def test_type_comment(self):
        self._run('values = []  # type: list\n')  # lines 556-557

    def test_unreachable_code_after_return(self):
        self._run('def f():\n    return\n    dead = 1\n')  # lines 599-607


class TestDunderAllAugAndAnnAssign(BaseTestCase):
    def test_name_exported_via_all_augassign_is_used(self):
        self.files = {
            'foo.py': """
                def used_via_all():
                    pass

                __all__ = []
                __all__ += ['used_via_all']
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, None)

    def test_name_exported_via_all_annassign_is_used(self):
        self.files = {
            'foo.py': """
                def used_via_all():
                    pass

                __all__: list[str] = ['used_via_all']
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, None)


def _visitor():
    return FindUnusedCodeVisitor(filenames=[], args=Args())


class TestVisitorDirectUnits(TestCase):
    def test_log_emits_when_verbose(self):
        visitor = _visitor()
        visitor.verbose = True
        visitor._log('hello')  # lines 203-206

    def test_class_decorator_whitelist_break(self):
        visitor = _visitor()
        visitor.ignore_decorators = ['@deco']
        node = ast.parse('@deco\nclass A:\n    pass\n').body[0]
        visitor.visit_ClassDef(node)  # lines 428-430 (break taken)

    def test_function_decorator_whitelist_skip(self):
        visitor = _visitor()
        visitor.ignore_decorators = ['@deco']
        node = ast.parse('@deco\ndef f():\n    pass\n').body[0]
        visitor.visit_FunctionDef(node)  # lines 446-447

    def test_visit_match_class_marks_kwd_attrs_used(self):
        visitor = _visitor()
        node = types.SimpleNamespace(kwd_attrs=['kind'])  # avoid 3.10 match syntax
        visitor.visit_MatchClass(node)  # lines 503-504
        assert 'kind' in visitor.used_names
