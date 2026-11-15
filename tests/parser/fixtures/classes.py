"""Fixture: class definitions with bases, keywords, and decorators."""

import functools


class Plain:
    pass


class WithDocstring:
    """Documented."""


class SingleBase(Plain):
    pass


class MultipleBases(Plain, object):
    pass


class WithKeywords(Plain, metaclass=type):
    pass


@functools.total_ordering
class Decorated(Plain):
    pass


@deco_a
@deco_b(arg=1)
class MultiplyDecorated(Plain):
    pass


class WithMethods(Plain):
    def method(self):
        return 1

    async def async_method(self):
        return 2

    class Nested(Plain):
        pass


class WithAttributes(Plain):
    class_variable = 1
    annotated_variable: int = 2


class ContainsStatements(Plain):
    def method(self):
        if self.attribute:
            return self.attribute
        return None
