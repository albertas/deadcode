def unused_function():
    if 2 > 1:
        pass


def this_one_is_used():
    pass


this_one_is_used()


def another_unused_function(arg1: str = "", arg2: str = "Hello") -> None:
    print(arg1, arg2)


# def this_method_is_commented():
#     pass
