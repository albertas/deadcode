def unused_function():
    if 2 > 1:
        pass


def this_one_is_used():
    pass


this_one_is_used()


def another_unused_function(arg1: str = '', arg2: str = 'Hello') -> None:
    def this_is_unused_closure():
        pass

    print(arg1, arg2)


# def this_method_is_commented():
#     pass
