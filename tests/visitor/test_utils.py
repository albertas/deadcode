import ast
import unittest

from deadcode.visitor.utils import get_decorator_name


class TestUtils(unittest.TestCase):
    def test_get_decorator_name_simple(self):
        node = ast.parse('@my_decorator\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node), '@my_decorator')

    def test_get_decorator_name_attribute(self):
        node = ast.parse('@module.my_decorator\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node), '@module.my_decorator')

        # Nested attributes
        node2 = ast.parse('@pkg.module.my_decorator\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node2), '@pkg.module.my_decorator')

    def test_get_decorator_name_call(self):
        node = ast.parse('@app.route("/path", methods=["GET"])\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node), '@app.route')

        node2 = ast.parse('@my_decorator()\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node2), '@my_decorator')

    def test_get_decorator_name_chained_call(self):
        # Fix for issue #19: @Class().function() crashed with AttributeError: 'Call' object has no attribute 'id'
        node = ast.parse('@Class().function()\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node), '@Class.function')

    def test_get_decorator_name_unsupported(self):
        node = ast.parse('@(lambda x: x)\ndef f(): pass').body[0].decorator_list[0]
        self.assertEqual(get_decorator_name(node), '')
