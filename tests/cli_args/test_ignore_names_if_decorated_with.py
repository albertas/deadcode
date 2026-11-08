from deadcode.cli import main
from deadcode.utils.base_test_case import BaseTestCase


class IgnoreNamesIfDecoratedWithTests(BaseTestCase):
    def test_exact_match(self):
        self.files = {
            'foo.py': b"""
                @deco
                def handler():
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@deco'])

        self.assertEqual(unused_names, None)

    def test_wildcard_call_decorator(self):
        self.files = {
            'foo.py': b"""
                @app.get("/x")
                def handler():
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

        self.assertEqual(unused_names, None)

    def test_async_handler(self):
        self.files = {
            'foo.py': b"""
                @app.get("/x")
                async def handler():
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

        self.assertEqual(unused_names, None)

    def test_method(self):
        self.files = {
            'foo.py': b"""
                class Service:
                    @router.post("/x")
                    def handler(self):
                        pass

                Service()
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@router.*'])

        self.assertEqual(unused_names, None)

    def test_property(self):
        self.files = {
            'foo.py': b"""
                class Model:
                    @property
                    def value(self):
                        return 1

                Model()
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@property'])

        self.assertEqual(unused_names, None)

    def test_class(self):
        self.files = {
            'foo.py': b"""
                @decorated
                class Handler:
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@decorated'])

        self.assertEqual(unused_names, None)

    def test_non_matching_decorators_are_still_reported(self):
        self.files = {
            'foo.py': b"""
                def plain():
                    pass

                @other
                def decorated():
                    pass
                """
        }

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

        self.assertEqual(
            unused_names,
            'foo.py:1:0: DC02 Function `plain` is never used\n'
            'foo.py:5:0: DC02 Function `decorated` is never used',
        )

    def test_noqa_interaction(self):
        self.files = {
            'foo.py': b"""
                @deco
                def decorated():  # noqa: DC02
                    pass

                class Service:
                    def method(self):  # noqa: DC04
                        pass

                Service()
                """
        }

        unused_names = main(['foo.py', '--no-color'])

        self.assertEqual(unused_names, None)

        unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@deco'])

        self.assertEqual(unused_names, None)

    def test_fastapi_single_file(self):
        self.files = {
            'main.py': b"""
                from fastapi import FastAPI

                app = FastAPI()


                @app.get("/")
                def index():
                    return {}


                @app.on_event("startup")
                def startup():
                    pass


                def unused():
                    pass
                """
        }

        unused_names = main(['main.py', '--no-color'])

        self.assertEqual(
            unused_names,
            'main.py:7:0: DC02 Function `index` is never used\n'
            'main.py:12:0: DC02 Function `startup` is never used\n'
            'main.py:16:0: DC02 Function `unused` is never used',
        )

        unused_names = main(['main.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

        self.assertEqual(
            unused_names,
            'main.py:16:0: DC02 Function `unused` is never used',
        )
