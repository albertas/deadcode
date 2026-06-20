from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class DynamicUsageBoundaryTests(BaseTestCase):
    def test_getattr_literal_attr_suppresses_method(self):
        # Control: literal string second arg IS honored -> method suppressed.
        self.files = {
            'foo.py': """
                class C:
                    def secret(self):
                        return 1


                def go(o):
                    return getattr(o, "secret")()


                go(C())
                """
        }
        assert main(['foo.py', '--no-color']) is None

    def test_getattr_nonliteral_attr_does_not_suppress(self):
        # Boundary: a variable second arg is NOT matched -> method reported.
        self.files = {
            'foo.py': """
                class C:
                    def secret(self):
                        return 1


                def go(o, name):
                    return getattr(o, name)()


                go(C(), "secret")
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC04 Method `secret` is never used')

    def test_format_with_locals_suppresses_var(self):
        # Control: `.format(**locals())` IS honored -> name suppressed.
        self.files = {
            'foo.py': """
                def render():
                    name = "x"
                    return "{name}".format(**locals())


                render()
                """
        }
        assert main(['foo.py', '--no-color']) is None

    def test_format_with_vars_not_matched(self):
        # Boundary: `**vars()` is NOT matched -> name reported.
        self.files = {
            'foo.py': """
                def render():
                    name = "x"
                    return "{name}".format(**vars())


                render()
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:2:4: DC01 Variable `name` is never used')

    def test_builtins_getattr_not_matched(self):
        # Boundary: qualified `builtins.getattr` is NOT matched -> method reported.
        self.files = {
            'foo.py': """
                import builtins


                class C:
                    def secret(self):
                        return 1


                def go(o):
                    return builtins.getattr(o, "secret")()


                go(C())
                """
        }
        unused_names = main(['foo.py', '--no-color'])
        self.assertEqual(unused_names, 'foo.py:5:4: DC04 Method `secret` is never used')
