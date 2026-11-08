from deadcode.cli import main


def test_decorated_class_body_is_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                class Handler:
                    unused_attribute = 1

                    def unused_method(self):
                        return 2
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@deco'])

    assert unused_names == ('foo.py:2:0: DC03 Class `Handler` is never used')


def test_decorated_function_body_is_ignored(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @deco
                def handler():
                    unused_local = 1
                    return unused_local
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@deco'])

    assert unused_names == ('foo.py:2:0: DC02 Function `handler` is never used')


def test_decorated_method_and_property_inside_used_class(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                class Service:
                    @deco
                    def unused_method(self):
                        unused_method_local = 1

                    @property
                    def unused_property(self):
                        unused_property_local = 2

                    def used_method(self):
                        pass

                Service().used_method()
                """
    }

    unused_names = main(
        [
            'foo.py',
            '--no-color',
            '--ignore-bodies-if-decorated-with=@deco',
            '--ignore-bodies-if-decorated-with=@property',
        ]
    )

    assert unused_names == (
        'foo.py:3:4: DC04 Method `unused_method` is never used\n'
        'foo.py:7:4: DC08 Property `unused_property` is never used'
    )


def test_wildcard_call_decorator(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @app.get("/x")
                def handler():
                    unused_local = 1
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@app.*'])

    assert unused_names == ('foo.py:2:0: DC02 Function `handler` is never used')


def test_non_matching_decorator_body_is_still_reported(virtual_file_system):
    virtual_file_system.files = {
        'foo.py': b"""
                @other
                def decorated():
                    unused_local = 1
                """
    }

    unused_names = main(['foo.py', '--no-color', '--ignore-bodies-if-decorated-with=@app.*'])

    assert unused_names == (
        'foo.py:2:0: DC02 Function `decorated` is never used\n' 'foo.py:3:4: DC01 Variable `unused_local` is never used'
    )
