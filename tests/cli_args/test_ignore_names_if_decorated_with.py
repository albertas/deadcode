from deadcode.cli import main


def test_exact_match(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                def handler():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@deco'])

    # Then
    assert unused_names is None


def test_wildcard_call_decorator(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @app.get("/x")
                def handler():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

    # Then
    assert unused_names is None


def test_async_handler(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @app.get("/x")
                async def handler():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

    # Then
    assert unused_names is None


def test_method(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @router.post("/x")
                    def handler(self):
                        pass

                Service()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@router.*'])

    # Then
    assert unused_names is None


def test_property(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Model:
                    @property
                    def value(self):
                        return 1

                Model()
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@property'])

    # Then
    assert unused_names is None


def test_class(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @decorated
                class Handler:
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@decorated'])

    # Then
    assert unused_names is None


def test_non_matching_decorators_are_still_reported(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def plain():
                    pass

                @other
                def decorated():
                    pass
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

    # Then
    assert unused_names == (
        'foo.py:1:0: DC02 Function `plain` is never used\nfoo.py:5:0: DC02 Function `decorated` is never used'
    )


def test_noqa_interaction(virtual_file_system):
    # Having
    virtual_file_system.files = {
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

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names is None

    # When
    unused_names = main(['foo.py', '--no-color', '--ignore-names-if-decorated-with=@deco'])

    # Then
    assert unused_names is None


def test_fastapi_single_file(virtual_file_system):
    # Having
    virtual_file_system.files = {
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

    # When
    unused_names = main(['main.py', '--no-color'])

    # Then
    assert unused_names == (
        'main.py:7:0: DC02 Function `index` is never used\n'
        'main.py:12:0: DC02 Function `startup` is never used\n'
        'main.py:16:0: DC02 Function `unused` is never used'
    )

    # When
    unused_names = main(['main.py', '--no-color', '--ignore-names-if-decorated-with=@app.*'])

    # Then
    assert unused_names == ('main.py:16:0: DC02 Function `unused` is never used')
