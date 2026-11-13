import pytest

from deadcode.cli import main


@pytest.mark.xfail(
    strict=True,
    reason='DEP 5 stage A: a used name in one module must not mark a same-named definition in another module as used',
)
def test_same_named_definition_in_another_module_is_reported_unused(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'a.py': b"""
                def foo():
                    return 1


                print(foo())
                """,
        'b.py': b"""
                def foo():
                    return 2
                """,
    }

    # When
    unused_names = main(['.', '--no-color'])

    # Then
    assert unused_names == 'b.py:1:0: DC02 Function `foo` is never used'
