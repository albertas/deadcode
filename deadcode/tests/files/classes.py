class UnusedClass(object):
    pass


class ThisClassIsUsed:
    name = "One"


instance_of_a_used_class = ThisClassIsUsed()
print(instance_of_a_used_class)


class AnotherUnusedClass:
    def __init__(self):
        pass
