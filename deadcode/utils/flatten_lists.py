from typing import TypeVar

T = TypeVar('T')


def flatten_lists_of_comma_separated_values(
    list_of_comma_separated_values: list[list[str]] | None,
) -> list[str]:
    """Concatenates lists into one list."""
    if not list_of_comma_separated_values:
        return []
    return flatten_list([v.split(',') for v in flatten_list(list_of_comma_separated_values)])


def flatten_list(list_of_lists: list[list[T]] | None) -> list[T]:
    """Concatenates lists into one list."""
    if not list_of_lists:
        return []
    return [elem for elem_list in list_of_lists for elem in elem_list]
