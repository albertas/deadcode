"""Fixture: comprehension shapes of every slice-04 form."""

list_comp = [item for item in iterable]
list_comp_if = [item for item in iterable if item]
list_comp_multi = [a + b for a in first for b in second]
list_comp_async = [item async for item in iterable]

set_comp = {item for item in iterable}
set_comp_if = {item for item in iterable if item if other}

dict_comp = {key: value for key, value in pairs}
dict_comp_if = {key: value for key, value in pairs if key}

genexp = (item for item in iterable)
genexp_if = (item for item in iterable if item)
genexp_in_call = sum(item for item in iterable)
genexp_parenthesized = sum((item for item in iterable))
genexp_multi = (a * b for a in first for b in second)


def consume():
    return list_comp, list_comp_if, set_comp, dict_comp, genexp
