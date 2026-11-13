import pytest

from deadcode.cli import main


@pytest.mark.parametrize(
    'comment',
    [
        '# type: ignore',
        '# type: ignore[assignment]',
        '#ty: ignore',
        '# ty: ignore[invalid-argument-type]',
        '# ty: ignore[invalid-argument-type, invalid-return-type]',
        '# pyright: ignore',
        '# pyright: ignore[reportGeneralTypeIssues]',
        '# pyre-ignore',
        '# pyre-fixme[9]',
        '# mypy: ignore-errors',
        '# pytype: disable=attribute-error',
        '# TYPE: IGNORE',
    ],
)
def test_type_checker_directive_comment_is_not_dc12(virtual_file_system, comment):
    # Having
    virtual_file_system.files = {
        'foo.py': f"""
                print("Keep")
                {comment}
                """.encode()
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_trailing_type_checker_directive_is_not_dc12(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                value = 1  # ty: ignore[invalid-argument-type]
                print(value)
                """
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result is None


def test_inline_annotations_are_not_dc12(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                class Model:
                    pass


                def annotated(value: list[int] | None, other: 'Model') -> dict[str, int]:
                    result: dict[str, int] = {}
                    return result


                annotated([1], Model())
                """
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert 'DC12' not in (result or '')


def test_pep_484_type_comments_are_not_dc12(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                def typed(value):
                    # type: (int) -> int
                    return value


                value = 1  # type: int
                print(typed(value))
                """
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert 'DC12' not in (result or '')


def test_genuine_commented_out_code_is_still_dc12(virtual_file_system):
    # Having
    virtual_file_system.files = {
        'foo.py': b"""
                print("Keep")
                # print("Hello world")
                """
    }

    # When
    result = main(['foo.py', '--no-color'])

    # Then
    assert result == 'foo.py:2:0: DC12 Commented out code'
