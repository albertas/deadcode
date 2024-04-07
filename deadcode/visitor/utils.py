import ast
from typing import Union

from deadcode.visitor.code_item import CodeItem
from deadcode.constants import UnusedCodeType


def _safe_eval(node: ast.AST, default: bool) -> bool:
    """
    Safely evaluate the Boolean expression under the given AST node.

    Substitute `default` for all sub-expressions that cannot be
    evaluated (because variables or functions are undefined).

    We could use eval() to evaluate more sub-expressions. However, this
    function is not safe for arbitrary Python code. Even after
    overwriting the "__builtins__" dictionary, the original dictionary
    can be restored
    (https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html).

    """
    if isinstance(node, ast.BoolOp):
        results = [_safe_eval(value, default) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(results)
        else:
            return any(results)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, not default)
    else:
        try:
            eval_result: bool = ast.literal_eval(node)
            return eval_result
        except ValueError:
            return default


def condition_is_always_false(condition: ast.AST) -> bool:
    return not _safe_eval(condition, True)


def condition_is_always_true(condition: ast.AST) -> bool:
    return _safe_eval(condition, False)


# def format_path(path: pathlib.Path) -> pathlib.Path:
#     try:
#         return path.relative_to(pathlib.Path.cwd())
#     except ValueError:
#         # Path is not below the current directory.
#         return path


def get_decorator_name(decorator: Union[ast.Call, ast.Attribute]) -> str:
    if isinstance(decorator, ast.Call):
        decorator = decorator.func  # type: ignore
    parts = []
    while isinstance(decorator, ast.Attribute):
        parts.append(decorator.attr)
        decorator = decorator.value  # type: ignore
    parts.append(decorator.id)  # type: ignore
    return '@' + '.'.join(reversed(parts))


class LoggingList(list):  # type: ignore
    def __init__(self, type_: UnusedCodeType, verbose: bool) -> None:
        self.type_ = type_
        self._verbose = verbose
        return super().__init__()

    def append(self, item: CodeItem) -> None:
        if self._verbose:
            print(f'define {self.type_} "{item.name}"')
        super().append(item)


class LoggingSet(set):  # type: ignore
    def __init__(self, type_: UnusedCodeType, verbose: bool) -> None:
        self.type_ = type_
        self._verbose = verbose
        return super().__init__()

    def add(self, name: str) -> None:
        if self._verbose:
            print(f'use {self.type_} "{name}"')
        super().add(name)
