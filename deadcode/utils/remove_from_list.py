from collections.abc import Callable


def remove_from_list(elements: list, should_remove: Callable) -> None:
    """
    Removes list items based on criteria (without recreating list).

    >>> elements = [1, 2, 3, 4]
    >>> should_remove = lambda x: x in [2, 4]
    >>> remove_from_list(elements, should_remove)
    >>> print(elements)
    ... [1, 3]
    """
    for i in range(len(elements) - 1, -1, -1):
        if should_remove(elements[i]):
            elements.pop(i)
