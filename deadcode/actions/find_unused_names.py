import re
from typing import Dict
from collections import defaultdict

from deadcode.data_types import Args, Filename, VariableName, AbstractSyntaxTree


def find_unused_names(
    files: Dict[Filename, AbstractSyntaxTree],
    global_names: Dict[VariableName, Filename],
    args: Args,
) -> Dict[VariableName, Filename]:
    name_occourencies: Dict[str, int] = defaultdict(int)

    for name in global_names.keys():
        pattern = re.compile(
            "|".join(
                [
                    rf"FunctionDef\(name=\'{name}\'",
                    rf"ClassDef\(name=\'{name}\'",
                    rf"Name\(id=\'{name}\'",
                    rf"alias\(name=\'{name}\'",
                ]
            )
        )
        for abstract_syntax_tree in files.values():
            name_occourencies[name] += len(re.findall(pattern, abstract_syntax_tree))

    # Filter out used and ignored names
    ignore_names_pattern = "|".join(args.ignore_names) or "^$"
    ignore_names_re = re.compile(ignore_names_pattern)

    unused_variables = {
        name: filename
        for name, filename in global_names.items()
        if name_occourencies[name] == 1 and not re.findall(ignore_names_re, name)
    }
    return unused_variables
