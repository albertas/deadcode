"""Fixture: the `# type:` comment attachment contract (D8)."""

plain = 1  # type: int
first = 2
second = 3  # type: int
multi = (
    4,
    5,
)  # type: tuple[int, int]
ignored = 6  # type: ignore
annotated_ignored = 7  # type: ignore[unused]


class WithComments:
    attribute = 8  # type: int


def commented_signature(number) -> int:  # type: (int) -> int
    local = number  # type: int
    return local


def block_comment(number):
    # type: (int) -> int
    return number


def parameters(
    first,  # type: int
    second=2,  # type: int
    *rest,  # type: int
    keyword,  # type: int
    **options,  # type: int
):  # type: (...) -> int
    return first


for item in iterable:  # type: int
    total = item

with open("file") as handle:  # type: int
    data = handle


def multi_statement_line():
    before = 1
    after = 2  # type: int
    return after
