from deadcode.cli import main


def test_decorator_call_on_class_instance(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @Class().function()
                def a():
                    return "42"
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == 'foo.py:2:0: DC02 Function `a` is never used'


def test_unusual_decorator_shapes_do_not_crash(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                @factory()()
                def nested_call():
                    return None

                @decorators[0]
                def subscript_decorator():
                    return None

                @(lambda function: function)
                def lambda_decorator():
                    return None
                """
    }

    # When
    unused_names = main(['foo.py', '--no-color'])

    # Then
    assert unused_names == (
        'foo.py:2:0: DC02 Function `nested_call` is never used\n'
        'foo.py:6:0: DC02 Function `subscript_decorator` is never used\n'
        'foo.py:10:0: DC02 Function `lambda_decorator` is never used'
    )
