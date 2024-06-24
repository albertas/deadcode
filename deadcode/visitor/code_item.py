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
from typing import List, Optional

from deadcode.constants import UnusedCodeType, ERROR_TYPE_TO_ERROR_CODE

from deadcode.data_types import Part


class CodeItem:  # TODO: This should also be a dataclass, because hash and tuple methods are reimplemented.
    """
    Store information about code object such as name, type and its location.
    """

    __slots__ = (
        'name',
        'type_',
        'filename',
        'code_parts',
        'scope',
        'inherits_from',
        'name_line',
        'name_column',
        'message',
        'error_code',
        'number_of_uses',
    )

    def __init__(
        self,
        name: str,
        type_: UnusedCodeType,
        filename: Path,
        code_parts: Optional[List[Part]] = None,  # TODO: I should use a dataclass instead of a tuple for Part.
        scope: Optional[str] = None,
        inherits_from: Optional[List[str]] = None,
        name_line: Optional[int] = None,
        name_column: Optional[int] = None,
        message: str = '',
        number_of_uses: int = 0,
    ):
        self.name = name
        self.type_ = type_
        self.filename = filename
        self.scope = scope
        self.inherits_from = inherits_from
        self.number_of_uses = number_of_uses

        if code_parts is None:
            self.code_parts = []
        else:
            self.code_parts = code_parts

        self.error_code = ERROR_TYPE_TO_ERROR_CODE[type_]
        self.message = message

        self.name_line = name_line
        self.name_column = name_column

    @property
    def scoped_name(self) -> str:
        return f'{self.scope}.{self.name}'

    @property
    def filename_with_position(self) -> str:
        filename_with_position = str(self.filename)
        if self.name_line is not None:
            filename_with_position += f':{self.name_line}'
            if self.name_column is not None:
                filename_with_position += f':{self.name_column}:'
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

    def __repr__(self) -> str:
        return repr(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other

        if isinstance(other, CodeItem):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)
