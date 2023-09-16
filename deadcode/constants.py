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
    "commented_out_code",
]


UnusedCodeErrorCode = Literal[
    "DC010", "DC020", "DC030", "DC040", "DC050", "DC060", "DC070", "DC080", "DC090", "DC110", "DC120"
]


ERROR_TYPE_TO_ERROR_CODE: Dict[UnusedCodeType, UnusedCodeErrorCode] = {
    "variable": "DC010",
    "function": "DC020",
    "class": "DC030",
    "method": "DC040",
    "attribute": "DC050",
    "name": "DC060",
    "import": "DC070",
    "property": "DC080",
    "unreachable_code": "DC090",
    "unused_file": "DC110",
    "commented_out_code": "DC120",
}
