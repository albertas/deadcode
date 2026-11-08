class NotFoundError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name


class UnusedError(Exception):
    pass
