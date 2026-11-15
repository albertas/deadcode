"""Fixture: walrus, star expressions, yield, yield from, and await (3.10+)."""


def generators(iterable):
    yield 1
    yield iterable
    yield from iterable
    result = [value for value in iterable]
    return result


async def coroutines(awaitable, iterable):
    await awaitable
    await awaitable()
    value = await awaitable()
    return value


def walrus(iterable):
    if (count := len(iterable)) > 3:
        return count
    while (chunk := next(iter(iterable), None)) is not None:
        if chunk:
            break
    return [filtered for item in iterable if (filtered := item * 2)]


def star_calls(*args, **kwargs):
    return (args, kwargs)


def star_unpack(first, *middle, last):
    return (first, middle, last)


targets = [1, 2, 3, 4]
head, *tail = targets
*head, tail = targets
[first, second] = targets
(a, b), c = (targets, 5)
combined = [*targets, *tail]
merged = {**{}, **{}}
