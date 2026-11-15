"""Fixture: match statements of every pattern shape (3.10+)."""


def classify(value, point, mapping, names):
    match value:
        case 1:
            result = "one"
        case "two":
            result = "two"
        case -1:
            result = "negative"
        case 1 + 2j:
            result = "complex"
        case None:
            result = "none"
        case True:
            result = "true"
        case False:
            result = "false"
        case _:
            result = "anything"

    match point:
        case (a, b):
            result = (a, b)
        case [first, second]:
            result = (first, second)
        case [1, 2, *rest, last]:
            result = (rest, last)
        case A():
            result = "plain class"
        case A(x, y):
            result = (x, y)
        case A(x=1, y=2):
            result = "keywords"
        case {}:
            result = "empty mapping"

    match mapping:
        case {"key": k}:
            result = k
        case {**kw}:
            result = kw
        case {"a": a, "b": b, **kw}:
            result = (a, b, kw)

    match names:
        case 1 | 2 | 3:
            result = "digits"
        case name as alias if alias:
            result = (name, alias)
        case [x] | (x,):
            result = x

    match value, point:
        case (1, 2):
            result = "tuple subject"

    match [value]:
        case _:
            pass
    return result


class A:
    pass


class B:
    pass
