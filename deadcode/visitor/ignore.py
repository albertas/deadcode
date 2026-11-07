import ast
from fnmatch import fnmatch, fnmatchcase
from pathlib import Path
from typing import Iterable, Set, Union

from deadcode.visitor.code_item import CodeItem


IGNORED_VARIABLE_NAMES = {'object', 'self'}
PYTEST_FUNCTION_NAMES = {
    'setup_module',
    'teardown_module',
    'setup_function',
    'teardown_function',
}
PYTEST_METHOD_NAMES = {
    'setup_class',
    'teardown_class',
    'setup_method',
    'teardown_method',
}

ERROR_CODES = {
    'variable': b'DC01',
    'function': b'DC02',
    'class': b'DC03',
    'method': b'DC04',
    'attribute': b'DC05',
    'name': b'DC06',
    'import': b'DC07',
    'property': b'DC08',
    'unreachable_code': b'DC09',
    'empty_file': b'DC11',
    'commented_out_code': b'DC12',
    'ignore_expression': b'DC13',
}


def _get_unused_items(defined_items: Iterable[CodeItem], used_names: Set[str]) -> Iterable[CodeItem]:
    unused_items = [item for item in defined_items if item.name not in used_names]
    unused_items.sort(key=lambda item: item.name.lower())
    return unused_items


def _is_special_name(name: str) -> bool:
    return name.startswith('__') and name.endswith('__')


def _match(name: Union[str, Path], patterns: Iterable[str], case: bool = True) -> bool:
    func = fnmatchcase if case else fnmatch
    return any(func(str(name), pattern) for pattern in patterns)


def _match_many(names: Union[Iterable[str], Iterable[Path]], patterns: Iterable[str], case: bool = True) -> bool:
    return any(_match(name, patterns, case) for name in names)


def _is_test_file(filename: Path) -> bool:
    return _match(
        filename.resolve(),
        ['*/test/*', '*/tests/*', '*/test*.py', '*[-_]test.py'],
        case=False,
    )


def _assigns_special_variable__all__(node: ast.Assign) -> bool:
    assert isinstance(node, ast.Assign)
    return isinstance(node.value, (ast.List, ast.Tuple)) and any(
        target.id == '__all__' for target in node.targets if isinstance(target, ast.Name)
    )


def _ignore_class(filename: Path, class_name: str) -> bool:
    return _is_test_file(filename) and 'Test' in class_name


def _ignore_import(filename: Path, import_name: str) -> bool:
    """
    Ignore star-imported names since we can't detect whether they are used.
    Ignore imports from __init__.py files since they're commonly used to
    collect objects from a package.
    """
    return filename.name == '__init__.py' or import_name == '*'


def _ignore_function(filename: Path, function_name: str) -> bool:
    return (function_name in PYTEST_FUNCTION_NAMES or function_name.startswith('test_')) and _is_test_file(filename)


def _ignore_method(filename: Path, method_name: str) -> bool:
    return _is_special_name(method_name) or (
        (method_name in PYTEST_METHOD_NAMES or method_name.startswith('test_')) and _is_test_file(filename)
    )


def _ignore_variable(filename: Path, varname: str) -> bool:
    """
    Ignore _ (Python idiom), _x (pylint convention) and
    __x__ (special variable or method), but not __x.
    """
    return (
        varname in IGNORED_VARIABLE_NAMES
        or (varname.startswith('_') and not varname.startswith('__'))
        or _is_special_name(varname)
    )
