"""Fixture: expression operators, containers, slices, and calls."""

binary = a + b - c * d / e // f % g**h << i >> j | k ^ l & m @ n
parens = (a + b) * (c + d)
nested_parens = a
unary = -a + +b - ~c
boolean = a and b and not c or d
compare = a < b <= c == d != e > f >= g
compare_chain = a is b is not c in d not in e
conditional = a if b else c if d else e

name_ctx = a.b.c.d
call = f()
call_args = f(a, b, c)
call_kwargs = f(a, b, key=value, other=1)
call_mixed = f(a.b, obj.method(), key=value)
nested_call = f(g(h(x)))
method_call = obj.method(a, key=b)
chained_call = f(a)(b)(c)

subscript = a[0]
subscript_slice = a[b:c]
subscript_step = a[b:c:d]
subscript_slice_only = a[:]
subscript_step_only = a[::d]
subscript_tuple = a[b, c, ...]
subscript_nested = a[b][c][d]

lists = [[], [1], [1, 2, [3, 4]]]
tuples = [(1,), (1, 2), (1, 2, (3, 4)), (), 1, 2]
bare_tuple_return = 1, 2
dicts = [{}, {1: 2}, {1: 2, 3: 4}, {**spread, 5: 6}]
sets = [{1}, {1, 2, 3}, {1, (2, 3)}]

lambda_expr = lambda: 1
lambda_params = lambda a, b=1: a + b
lambda_conditional = lambda a: a if a else 0
