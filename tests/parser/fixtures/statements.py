"""Fixture: statement-level shapes: layout, globals, asserts, raises."""

GLOBAL_A = 1


def scope_statements():
    global GLOBAL_A
    global GLOBAL_A, GLOBAL_B
    nested_variable = GLOBAL_A

    def inner():
        nonlocal nested_variable
        nonlocal nested_variable, other_nested

    assert GLOBAL_A
    assert GLOBAL_A, "message"
    assert GLOBAL_A, "plain message"
    raise
    raise ValueError("raised")
    raise ValueError from GLOBAL_A
    return inner


separated = 1
other = 2
expression_statement
GLOBAL_A
call_expression(GLOBAL_A)

continued = 1 + 2

if GLOBAL_A and GLOBAL_B:
    pass

x = (
    1,
    2,
)
y = f(
    a,
    b,
)


def multiline_signature(
    a,
    b=2,
    *c,
    **d,
):
    return a
