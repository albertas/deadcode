import ast


def print_ast(node: ast.AST) -> None:
    print(ast.dump(node, indent=4))
