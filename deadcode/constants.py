from typing import Dict, Literal


UnusedCodeType = Literal[
    'attribute',
    'class',
    'function',
    'import',
    'method',
    'property',
    'variable',
    'unreachable_code',
    'name',
    'unused_file',
    'commented_out_code',
    'ignore_expression',
]


UnusedCodeErrorCode = Literal[
    'DC01',
    'DC02',
    'DC03',
    'DC04',
    'DC05',
    'DC06',
    'DC07',
    'DC08',
    'DC09',
    'DC11',
    'DC12',
    'DC13',
]


ERROR_TYPE_TO_ERROR_CODE: Dict[UnusedCodeType, UnusedCodeErrorCode] = {
    'variable': 'DC01',
    'function': 'DC02',
    'class': 'DC03',
    'method': 'DC04',
    'attribute': 'DC05',
    'name': 'DC06',
    'import': 'DC07',
    'property': 'DC08',
    'unreachable_code': 'DC09',
    'unused_file': 'DC11',
    'commented_out_code': 'DC12',
    'ignore_expression': 'DC13',
}
