from deadcode.cli import main


def test_class_with_body_is_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                class Handler:
                    value = 1

                    def method(self):
                        return 2
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@deco'])

    assert unused_names is None


def test_function_with_locals_is_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                def handler():
                    unused_local = 1
                    return unused_local
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@deco'])

    assert unused_names is None


def test_method_inside_used_class_is_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @router.post("/x")
                    def handler(self):
                        pass

                Service()
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@router.*'])

    assert unused_names is None


def test_wildcard_call_decorator(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @app.get("/x")
                def handler():
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@app.*'])

    assert unused_names is None


def test_non_matching_decorators_are_still_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                def plain():
                    pass

                @other
                def decorated():
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@app.*'])

    assert unused_names == (
        'foo.py:1:0: DC02 Function `plain` is never used\n' 'foo.py:5:0: DC02 Function `decorated` is never used'
    )


def test_fix_keeps_whole_decorated_definition(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                def decorated():
                    value = 1

                def unused():
                    pass
                """
    }

    unused_names = main(
        ['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@deco', '--fix']
    )

    assert unused_names == ('foo.py:5:0: DC02 Function `unused` is never used\n\nRemoved 1 unused code item!')

    virtual_file_system.assert_files(
        {
            'foo.py': b"""
                @deco
                def decorated():
                    value = 1
                """
        }
    )


def test_noqa_interaction(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                def decorated():  # noqa: DC02
                    pass

                @deco
                class Decorated:  # noqa: DC03
                    pass
                """
    }

    unused_names = main(['foo.py', '--no-color'])

    assert unused_names is None

    unused_names = main(['foo.py', '--no-color', '--ignore-definitions-if-decorated-with=@deco'])

    assert unused_names is None
