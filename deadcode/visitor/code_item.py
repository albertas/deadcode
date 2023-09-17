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
from typing import List, Optional, Tuple

from deadcode.constants import UnusedCodeType, ERROR_TYPE_TO_ERROR_CODE

from deadcode.data_types import Part


class CodeItem:  # TODO: This should also be a dataclass, because hash and tuple methods are reimplemented.
    """
    Store information about code object such as name, type and its location.
    """

    __slots__ = (
        "name",
        "type_",
        "filename",
        "code_parts",
        "name_line",
        "name_column",
        "message",
        "error_code",
    )

    def __init__(
        self,
        name: str,
        type_: UnusedCodeType,
        filename: Path,
        # These arguments are being converted to Part
        # first_lineno: int = 0,
        # last_lineno: int = 0,
        # first_column: int = 0,
        # last_column: Optional[int] = None,
        code_parts: Optional[List[Part]] = None,  # TODO: I should use a dataclass instead of a tuple for Part.
        name_line: Optional[int] = None,
        name_column: Optional[int] = None,
        message: str = "",
    ):
        self.name = name
        self.type_ = type_
        self.filename = filename

        if code_parts is None:
            self.code_parts = []
        else:
            self.code_parts = code_parts

        # if first_lineno is not None:
        #     pass

        # self.first_lineno = first_lineno
        # self.last_lineno = last_lineno
        # self.first_column = first_column
        # self.last_column = last_column

        self.error_code = ERROR_TYPE_TO_ERROR_CODE[type_]
        self.message = message

        self.name_line = name_line
        self.name_column = name_column

    @property
    def filename_with_position(self) -> str:
        filename_with_position = str(self.filename)
        if self.name_line is not None:
            filename_with_position += f":{self.name_line}"
            if self.name_column is not None:
                filename_with_position += f":{self.name_column}:"
        return filename_with_position

    # @property
    # def size(self) -> int:
    #     assert self.last_lineno >= self.first_lineno
    #     return self.last_lineno - self.first_lineno + 1

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
    #     if self.type_ == "unreachable_code":
    #         return f"# {self.message} ({filename}:{self.first_lineno})"
    #     else:
    #         prefix = ""
    #         if self.type_ in ["attribute", "method", "property"]:
    #             prefix = "_."
    #         return "{}{}  # unused {} ({}:{:d})".format(prefix, self.name, self.type_, filename, self.first_lineno)

    def _tuple(self) -> Tuple[Path, int, str]:
        # TODO: this should no longer be needed, when dataclass is used.
        first_line = 0
        if self.code_parts:
            first_line = self.code_parts[0][0]

        return (self.filename, first_line, self.name)

    def __repr__(self) -> str:
        return repr(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CodeItem):
            return self._tuple() == other._tuple()
        return False

    def __hash__(self) -> int:
        return hash(self._tuple())
