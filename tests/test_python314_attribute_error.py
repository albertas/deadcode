from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class TestPython314AttributeError(BaseTestCase):
    def test_string_nodes_use_ast_constant(self):
        self.files = {
            'python314_string_nodes.py': b"""
                exported_name = 'exported'
                used_by_old_format = 'old format'
                used_by_getattr = 'getattr'
                used_by_new_format = 'new format'

                __all__ = ['exported_name']

                old_format_result = '%(used_by_old_format)s' % locals()
                getattr_result = getattr(object(), 'used_by_getattr')
                new_format_result = '{used_by_new_format}'.format(**locals())
                """
        }

        unused_names = main(['python314_string_nodes.py', '--no-color'])

        self.assertEqual(
            unused_names,
            (
                'python314_string_nodes.py:8:0: DC01 Variable `old_format_result` is never used\n'
                'python314_string_nodes.py:9:0: DC01 Variable `getattr_result` is never used\n'
                'python314_string_nodes.py:10:0: DC01 Variable `new_format_result` is never used'
            ),
        )
