import ast


def show(node: ast.AST) -> None:
    print(ast.dump(node, indent=4))
