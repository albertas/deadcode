from typing import Dict, Literal


UnusedCodeType = Literal[
    "attribute",
    "class",
    "function",
    "import",
    "method",
    "property",
    "variable",
    "unreachable_code",
    "name",
    "unused_file",
]


UnusedCodeErrorCode = Literal["DC001", "DC002", "DC003", "DC004", "DC005", "DC006", "DC007", "DC008", "DC009", "DC010"]


ERROR_TYPE_TO_ERROR_CODE: Dict[UnusedCodeType, UnusedCodeErrorCode] = {
    "variable": "DC001",
    "function": "DC002",
    "class": "DC003",
    "method": "DC004",
    "attribute": "DC005",
    "name": "DC006",
    "import": "DC007",
    "property": "DC008",
    "unreachable_code": "DC009",
    "unused_file": "DC010",
}
