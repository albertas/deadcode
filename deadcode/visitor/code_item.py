# TODO: filename is incorrect, because `.` is used instead of the actual file.


# TODO: use dataclass with these fields:
# filename: Filename
# name: str
# name_line: IndexInt
# name_column: IndexInt
# expression_line_start: IndexInt
# expression_line_end: Optional[IndexInt]
# expression_column_start: IndexInt
# expression_column_end: Optional[IndexInt]
# variable_type: VariableTypes
# usage_count: int = 0


# @dataclass
# class VariableInfo:
#     filename: Filename
#     name: str
#     name_line: IndexInt
#     name_column: IndexInt
#     expression_line_start: IndexInt
#     expression_line_end: Optional[IndexInt]
#     expression_column_start: IndexInt
#     expression_column_end: Optional[IndexInt]
#     variable_type: VariableTypes
#     usage_count: int = 0


from pathlib import Path
from typing import Optional, Tuple


class CodeItem:
    """
    Store information about code object such as name, type and its location.
    """

    __slots__ = (
        "name",
        "typ",
        "filename",
        "first_lineno",
        "last_lineno",
        "first_column",
        "last_column",
        "name_line",
        "name_column",
        "message",
    )

    def __init__(
        self,
        name: str,
        typ: str,
        filename: Path,
        first_lineno: int,
        last_lineno: int,
        first_column: int,
        last_column: Optional[int],
        name_line: int,
        name_column: int,
        message: str = "",
    ):
        self.name = name
        self.typ = typ
        self.filename = filename
        self.first_lineno = first_lineno
        self.last_lineno = last_lineno
        self.first_column = first_column
        self.last_column = last_column
        self.message = message or f"unused {typ} '{name}'"

        self.name_line = name_line
        self.name_column = name_column

    @property
    def filename_with_position(self) -> str:
        return f"{self.filename}:{self.name_line}:{self.name_column}:"

    @property
    def size(self) -> int:
        assert self.last_lineno >= self.first_lineno
        return self.last_lineno - self.first_lineno + 1

    # def get_report(self) -> str:
    #     from deadcode.visitor.utils import format_path

    #     return "{}:{:d}: {}".format(
    #         format_path(self.filename),
    #         self.first_lineno,
    #         self.message,
    #     )

    # def get_whitelist_string(self) -> str:
    #     from deadcode.visitor.utils import format_path

    #     filename = format_path(self.filename)
    #     if self.typ == "unreachable_code":
    #         return f"# {self.message} ({filename}:{self.first_lineno})"
    #     else:
    #         prefix = ""
    #         if self.typ in ["attribute", "method", "property"]:
    #             prefix = "_."
    #         return "{}{}  # unused {} ({}:{:d})".format(prefix, self.name, self.typ, filename, self.first_lineno)

    def _tuple(self) -> Tuple[Path, int, str]:
        return (self.filename, self.first_lineno, self.name)

    def __repr__(self) -> str:
        return repr(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CodeItem):
            return self._tuple() == other._tuple()
        return False

    def __hash__(self) -> int:
        return hash(self._tuple())
