from typing import List, Optional


def flatten_lists_of_comma_separated_values(
    list_of_comma_separated_values: Optional[List[List[str]]],
) -> List[str]:
    """Concatenates lists into one list."""
    if not list_of_comma_separated_values:
        return []
    list_of_comma_separated_values = flatten_list(list_of_comma_separated_values)
    return flatten_list([v.split(",") for v in list_of_comma_separated_values])  # type: ignore


def flatten_list(list_of_lists: Optional[List[List]]) -> List:
    """Concatenates lists into one list."""
    if not list_of_lists:
        return []
    return [elem for elem_list in list_of_lists for elem in elem_list]
