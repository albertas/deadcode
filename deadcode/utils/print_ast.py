import ast


def print_ast(node: ast.AST) -> None:  # pragma: no cover
    print(ast.dump(node, indent=4))  # type: ignore
