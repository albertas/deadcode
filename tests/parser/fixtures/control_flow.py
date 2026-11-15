"""Fixture: compound statements of every slice-04 shape."""


def control_flow(condition, iterable, mapping, handler_type):
    if condition:
        result = 1
    elif condition == 2:
        result = 2
    elif condition == 3:
        result = 3
    else:
        result = 4

    if condition:
        result = 5

    if condition:
        result = 6
    else:
        result = 7

    while condition:
        result -= 1
    else:
        result += 1

    while condition:
        break

    for item in iterable:
        result += item
    else:
        result -= 1

    for item in iterable:
        continue

    for key, value in mapping.items():
        result += key + value

    with open("file") as handle:
        result = handle.read()

    with open("a") as first, open("b") as second:
        result = first, second

    with first_context as first, second_context as second:
        result = first, second

    try:
        result = 1
    except ValueError:
        result = 2
    except (TypeError, KeyError) as caught:
        result = caught
    except:
        result = 3
    else:
        result = 4
    finally:
        result = 5

    try:
        result = 6
    finally:
        result = 7

    return result


async def async_control_flow(condition, iterable):
    if condition:
        async for item in iterable:
            result = item

    async with open("file") as handle:
        content = handle.read()

    return content
