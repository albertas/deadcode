"""Fixture: function definitions, decorators, and parameter shapes."""

import functools


def plain():
    pass


def with_docstring():
    """Documented."""
    return


def with_return():
    return 42


def parameters(
    positional,
    /,
    positional_or_keyword,
    *variadic,
    keyword_only,
    keyword_only_with_default=1,
    **keywords,
):
    return positional, positional_or_keyword, variadic, keyword_only


def annotated(parameter: int = 2, *, flag: bool = True) -> str:
    return f"{parameter} {flag}"


def variadic_annotated(*values: int, **mapping: str) -> dict:
    return dict(values, mapping)


@functools.cache
def decorated(argument):
    return argument


@functools.lru_cache(maxsize=None)
@deco
def multiply_decorated(argument):
    return argument


async def async_function(argument):
    return argument


async def async_with_return():
    return 1


def nested_definition():
    def inner():
        return 1

    return inner


lam = lambda: None
lam_with_params = lambda argument, default=1, *rest, keyword=2, **kwargs: argument
parenthesized_lambda = lambda value: value
