import ast
import re

from deadcode.visitor.utils import get_decorator_name

class TestUtils:
    def test_get_decorator_name_attribute(self):
        # Test with a decorator with an attribute
        decorator = ast.Attribute(value=ast.Name(id='module', ctx=ast.Load()), attr='my_decorator1')
        assert get_decorator_name(decorator).endswith('.my_decorator1')

        # Test with a complex decorator
        decorator = ast.Attribute(
            value=decorator,  # Create nested attributes
            attr='my_decorator2',
            ctx=ast.Load()
        )
        assert re.match(r'@\d+\.my_decorator1\.\d+\.my_decorator2', get_decorator_name(decorator))


    def test_get_decorator_name_call(self):
        decorator = ast.Attribute(value=ast.Name(id='module', ctx=ast.Load()), attr='my_decorator')
        assert re.match(r'@\d+\.my_decorator', get_decorator_name(decorator))

        # Test with a decorator that is a call
        decorator = ast.Call(
            func=decorator,
            args=[],
            keywords=[]
        )
        assert re.match(r'@\d+\.my_decorator', get_decorator_name(decorator))
