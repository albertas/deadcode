import ast
import sys
import re
import string

from pathlib import Path

from typing import Callable, List, Optional, Set, TextIO, Tuple, Union
from deadcode.constants import UnusedCodeType
from deadcode.data_types import Args
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.utils import LoggingList, LoggingSet
from deadcode.visitor import utils
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree

# TODO: from deadcode.visitor import noqa
from deadcode.visitor import lines
from deadcode.visitor.ignore import (
    # TODO: ERROR_CODES,
    IGNORED_VARIABLE_NAMES,
    _get_unused_items,
    _match,
    _assigns_special_variable__all__,
    _ignore_class,
    _ignore_import,
    _ignore_function,
    _ignore_method,
    _ignore_variable,
)


class DeadCodeVisitor(ast.NodeVisitor):
    """Finds dead code."""

    def __init__(self, filenames: List[str], args: Args) -> None:
        self.filenames = filenames

        self.args = args

        self.ignore_decorators: List[str] = []

        verbose = False
        # verbose = args.verbose
        self.verbose = verbose

        self.defined_attrs: List[CodeItem] = LoggingList("attribute", verbose)
        self.defined_classes: List[CodeItem] = LoggingList("class", verbose)
        self.defined_funcs: List[CodeItem] = LoggingList("function", verbose)
        self.defined_imports: List[CodeItem] = LoggingList("import", verbose)
        self.defined_methods: List[CodeItem] = LoggingList("method", verbose)
        self.defined_props: List[CodeItem] = LoggingList("property", verbose)
        self.defined_vars: List[CodeItem] = LoggingList("variable", verbose)
        self.unused_file: List[CodeItem] = LoggingList("unused_file", verbose)
        self.unreachable_code: List[CodeItem] = LoggingList("unreachable_code", verbose)

        # The purpose and the interface of the visitor is not known
        # Lets investigate the vulture code and pass here what ever I have.

        self.used_names: Set[str] = LoggingSet("name", self.verbose)

        self.filename = Path()
        self.code: List[str] = []
        # self.found_dead_code_or_error = False

        # Workaround
        # self.noqa_lines = {}

    # def scan(self, code, filename=""):
    #     filename = Path(filename)
    #     self.code = code.splitlines()
    #     self.noqa_lines = noqa.parse_noqa(self.code)
    #     self.filename = filename

    #     def handle_syntax_error(e):
    #         text = f' at "{e.text.strip()}"' if e.text else ""
    #         self._log(
    #             f"{utils.format_path(filename)}:{e.lineno}: {e.msg}{text}",
    #             file=sys.stderr,
    #             force=True,
    #         )
    #         self.found_dead_code_or_error = True

    #     try:
    #         node = ast.parse(code, filename=str(self.filename), type_comments=True)
    #     except SyntaxError as err:
    #         handle_syntax_error(err)
    #     except ValueError as err:
    #         # ValueError is raised if source contains null bytes.
    #         self._log(
    #             f'{utils.format_path(filename)}: invalid source code "{err}"',
    #             file=sys.stderr,
    #             force=True,
    #         )
    #         self.found_dead_code_or_error = True
    #     else:
    #         # When parsing type comments, visiting can throw SyntaxError.
    #         try:
    #             self.visit(node)
    #         except SyntaxError as err:
    #             handle_syntax_error(err)

    # TODO: do not load the AST of all the files into memory.
    # Should instead parse the files one by one and discard already parsed files.
    # The memory might add up for larger projects, especially that AST is whay larger the the code itself.

    def visit_abstract_syntax_trees(self) -> None:
        # NEXTODO:
        # So whats here? These examples could be moved to exclusion before.
        # Also AST should not be constructed until the parsing part.

        # def prepare_pattern(pattern):
        #     if not any(char in pattern for char in "*?["):
        #         pattern = f"*{pattern}*"
        #     return pattern

        # exclude = [prepare_pattern(pattern) for pattern in (self.args.exclude or [])]

        # def exclude_path(path):
        #     return _match(path, exclude, case=False)

        # # paths = [Path(path) for path in paths]

        # for module in utils.get_modules(paths):
        #     if exclude_path(module):
        #         self._log("Excluded:", module)
        #         continue

        # self._log("Scanning:", module)
        # try:
        #     module_string = utils.read_file(module)
        # except utils.VultureInputException as err:  # noqa: F841
        #     self._log(
        #         f"Error: Could not read file {module} - {err}\n"
        #         f"Try to change the encoding to UTF-8.",
        #         file=sys.stderr,
        #         force=True,
        #     )
        #     self.found_dead_code_or_error = True
        # else:
        #     self.scan(module_string, filename=module)

        # TODO: should parse the AST here.
        for filename in self.filenames:
            with open(filename) as f:
                node = parse_abstract_syntax_tree(f.read(), args=self.args, filename=filename)

            self.filename = Path(filename)
            self.visit(node)

        # unique_imports = {item.name for item in self.defined_imports}
        # for import_name in unique_imports:
        #     path = Path("whitelists") / (import_name + "_whitelist.py")
        #     if exclude_path(path):
        #         self._log("Excluded whitelist:", path)
        #     else:
        #         try:
        #             module_data = pkgutil.get_data("vulture", str(path))
        #             self._log("Included whitelist:", path)
        #         except OSError:
        #             # Most imported modules don't have a whitelist.
        #             continue
        #         module_string = module_data.decode("utf-8")
        #         self.scan(module_string, filename=path)

    def get_unused_code_items(self, sort_by_size: bool = False) -> List[CodeItem]:
        """
        Return ordered list of unused CodeItem objects.
        """

        def by_name(item: CodeItem) -> Tuple[str, int]:
            return (str(item.filename).lower(), item.first_lineno)

        def by_size(item: CodeItem) -> Tuple[int, str, int]:
            # TODO: default sorting should be by type or by filename
            return (item.size,) + by_name(item)

        unused_code = (
            self.unused_attrs
            + self.unused_classes
            + self.unused_funcs
            + self.unused_imports
            + self.unused_methods
            + self.unused_props
            + self.unused_vars
            + self.unreachable_code
        )

        return sorted(unused_code, key=by_size if sort_by_size else by_name)

    # TODO: investigate whitelisting options
    # def report(self, sort_by_size=False, make_whitelist=False):
    #     """
    #     Print ordered list of CodeItem objects to stdout.
    #     """
    #     for item in self.get_unused_code_items(sort_by_size=sort_by_size):
    #         self._log(
    #             item.get_whitelist_string() if make_whitelist else item.get_report(add_size=sort_by_size),
    #             force=True,
    #         )
    #         self.found_dead_code_or_error = True
    #     return self.found_dead_code_or_error

    @property
    def unused_classes(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_classes, self.used_names)

    @property
    def unused_funcs(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_funcs, self.used_names)

    @property
    def unused_imports(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_imports, self.used_names)

    @property
    def unused_methods(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_methods, self.used_names)

    @property
    def unused_props(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_props, self.used_names)

    @property
    def unused_vars(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_vars, self.used_names)

    @property
    def unused_attrs(self) -> List[CodeItem]:
        return _get_unused_items(self.defined_attrs, self.used_names)

    def _log(self, *args, file: Optional[TextIO] = None, force: bool = False) -> None:  # type: ignore
        if self.verbose or force:
            file = file or sys.stdout
            try:
                print(*args, file=file)
            except UnicodeEncodeError:
                # Some terminals can't print Unicode symbols.
                x = " ".join(map(str, args))
                print(x.encode(), file=file)

    def _add_aliases(self, node: Union[ast.Import, ast.ImportFrom]) -> None:
        """
        We delegate to this method instead of using visit_alias() to have
        access to line numbers and to filter imports from __future__.
        """
        assert isinstance(node, (ast.Import, ast.ImportFrom))
        for name_and_alias in node.names:
            # Store only top-level module name ("os.path" -> "os").
            # We can't easily detect when "os.path" is used.
            name = name_and_alias.name.partition(".")[0]
            alias = name_and_alias.asname
            self._define(
                self.defined_imports,
                alias or name,
                node,
                ignore=_ignore_import,
            )
            if alias is not None:
                self.used_names.add(name_and_alias.name)

    def _handle_conditional_node(self, node: Union[ast.If, ast.IfExp, ast.While], name: str) -> None:
        if utils.condition_is_always_false(node.test):
            self._define(
                self.unreachable_code,
                name,
                node,
                last_node=node.body if isinstance(node, ast.IfExp) else node.body[-1],
                message=f"unsatisfiable '{name}' condition",
            )
        elif utils.condition_is_always_true(node.test):
            else_body = node.orelse
            if name == "ternary":
                self._define(
                    self.unreachable_code,
                    name,
                    else_body,  # type: ignore
                    message="unreachable 'else' expression",
                )
            elif else_body:
                self._define(
                    self.unreachable_code,
                    "else",
                    else_body[0],  # type: ignore
                    last_node=else_body[-1],  # type: ignore
                    message="unreachable 'else' block",
                )
            elif name == "if":
                # Redundant if-condition without else block.
                self._define(
                    self.unreachable_code,
                    name,
                    node,
                    message="redundant if-condition",
                )

    def _define(
        self,
        collection: List[CodeItem],
        name: str,
        first_node: ast.AST,
        last_node: Optional[ast.AST] = None,
        message: str = "",
        ignore: Optional[Callable[[Path, str], bool]] = None,
    ) -> None:
        # TODO: add support for ignore_definitions, ignore_definitions_if_inherits_from options
        self._log(
            f"Options ignore_definitions, ignore_definitions_if_inherits_from not implemented yet. "
            f"Got these values: ignore_definitions={self.args.ignore_definitions}, "
            f"ignore_definitions_if_inherits_from={self.args.ignore_definitions_if_inherits_from}"
        )

        def ignored(lineno: int) -> bool:
            return bool(
                (ignore and ignore(self.filename, name))
                or _match(name, self.args.ignore_names)
                or _match(self.filename, self.args.ignore_names_in_files)
                # TODO: noqa comments should be supported
                # or noqa.ignore_line(self.noqa_lines, lineno, ERROR_CODES[typ])
            )

        last_node = last_node or first_node
        type_: UnusedCodeType = collection.type_  # type: ignore
        first_lineno = lines.get_first_line_number(first_node)

        if ignored(first_lineno):
            self._log(f'Ignoring {type_} "{name}"')
        else:
            last_lineno = lines.get_last_line_number(last_node)

            collection.append(
                CodeItem(
                    name=name,
                    type_=type_,
                    filename=self.filename,
                    first_lineno=first_lineno,
                    last_lineno=last_lineno,
                    first_column=last_node.col_offset,
                    last_column=last_node.end_col_offset,
                    name_line=last_node.lineno,
                    name_column=last_node.col_offset,
                    message=message,
                )
            )

    def _define_variable(self, name: str, node: ast.AST) -> None:
        self._define(
            self.defined_vars,
            name,
            node,
            ignore=_ignore_variable,
        )

    # def visit_arg(self, node: ast.AST) -> None:
    #     """Function argument"""
    #     self._define_variable(node.arg, node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return self.visit_FunctionDef(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Store):
            self._define(self.defined_attrs, node.attr, node)
        elif isinstance(node.ctx, ast.Load):
            self.used_names.add(node.attr)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """
        Parse variable names in old format strings:

        "%(my_var)s" % locals()
        """
        if isinstance(node.left, ast.Str) and isinstance(node.op, ast.Mod) and self._is_locals_call(node.right):
            self.used_names |= set(re.findall(r"%\((\w+)\)", node.left.s))

    def visit_Call(self, node: ast.Call) -> None:
        # Count getattr/hasattr(x, "some_attr", ...) as usage of some_attr.
        if isinstance(node.func, ast.Name) and (
            (node.func.id == "getattr" and 2 <= len(node.args) <= 3)
            or (node.func.id == "hasattr" and len(node.args) == 2)
        ):
            attr_name_arg = node.args[1]
            if isinstance(attr_name_arg, ast.Str):
                self.used_names.add(attr_name_arg.s)

        # Parse variable names in new format strings:
        # "{my_var}".format(**locals())
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Str)
            and node.func.attr == "format"
            and any(kw.arg is None and self._is_locals_call(kw.value) for kw in node.keywords)
        ):
            self._handle_new_format_string(node.func.value.s)

    def _handle_new_format_string(self, s: str) -> None:
        def is_identifier(name: str) -> bool:
            return bool(re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", name))

        parser = string.Formatter()
        try:
            names = [name for _, name, _, _ in parser.parse(s) if name]
        except ValueError:
            # Invalid format string.
            names = []

        for field_name in names:
            # Remove brackets and their contents: "a[0][b].c[d].e" -> "a.c.e",
            # then split the resulting string: "a.b.c" -> ["a", "b", "c"]
            vars = re.sub(r"\[\w*\]", "", field_name).split(".")
            for var in vars:
                if is_identifier(var):
                    self.used_names.add(var)

    @staticmethod
    def _is_locals_call(node: ast.AST) -> bool:
        """Return True if the node is `locals()`."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "locals"
            and not node.args
            and not node.keywords
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            if _match(utils.get_decorator_name(decorator), self.ignore_decorators):  # type: ignore
                self._log(f'Ignoring class "{node.name}" (decorator whitelisted)')
                break
        else:
            self._define(self.defined_classes, node.name, node, ignore=_ignore_class)

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
        decorator_names = [utils.get_decorator_name(decorator) for decorator in node.decorator_list]  # type: ignore

        first_arg = node.args.args[0].arg if node.args.args else None

        if "@property" in decorator_names:
            type_ = "property"
        elif "@staticmethod" in decorator_names or "@classmethod" in decorator_names or first_arg == "self":
            type_ = "method"
        else:
            type_ = "function"

        if any(_match(name, self.ignore_decorators) for name in decorator_names):
            self._log(f'Ignoring {type_} "{node.name}" (decorator whitelisted)')
        elif type_ == "property":
            self._define(self.defined_props, node.name, node)
        elif type_ == "method":
            self._define(self.defined_methods, node.name, node, ignore=_ignore_method)
        else:
            self._define(self.defined_funcs, node.name, node, ignore=_ignore_function)

    def visit_If(self, node: ast.If) -> None:
        self._handle_conditional_node(node, "if")

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._handle_conditional_node(node, "ternary")

    def visit_Import(self, node: ast.Import) -> None:
        self._add_aliases(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != "__future__":
            self._add_aliases(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Load, ast.Del)) and node.id not in IGNORED_VARIABLE_NAMES:
            self.used_names.add(node.id)
        elif isinstance(node.ctx, (ast.Param, ast.Store)):
            self._define_variable(node.id, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if _assigns_special_variable__all__(node):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            for elt in node.value.elts:
                if isinstance(elt, ast.Str):
                    self.used_names.add(elt.s)

    def visit_While(self, node: ast.While) -> None:
        self._handle_conditional_node(node, "while")

    # def visit_MatchClass(self, node: ast.MatchClass) -> None:  # type: ignore
    def visit_MatchClass(self, node) -> None:  # type: ignore
        for kwd_attr in node.kwd_attrs:
            self.used_names.add(kwd_attr)

    def visit(self, node: ast.AST) -> None:
        method_name = "visit_" + node.__class__.__name__
        visitor = getattr(self, method_name, None)
        if self.verbose:
            lineno = getattr(node, "lineno", 1)
            line = self.code[lineno - 1] if self.code else ""
            self._log(lineno, ast.dump(node), line)

        if visitor:
            visitor(node)

        # There isn't a clean subset of node types that might have type
        # comments, so just check all of them.
        type_comment = getattr(node, "type_comment", None)
        if type_comment is not None:
            mode = "func_type" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "eval"
            self.visit(ast.parse(type_comment, filename="<type_comment>", mode=mode))

        self.generic_visit(node)

    def _handle_ast_list(self, ast_list: List[ast.AST]) -> None:
        """
        Find unreachable nodes in the given sequence of ast nodes.
        """
        for index, node in enumerate(ast_list):
            if isinstance(node, (ast.Break, ast.Continue, ast.Raise, ast.Return)):
                try:
                    first_unreachable_node = ast_list[index + 1]
                except IndexError:
                    continue
                class_name = node.__class__.__name__.lower()
                self._define(
                    self.unreachable_code,
                    class_name,
                    first_unreachable_node,
                    last_node=ast_list[-1],
                    message=f"unreachable code after '{class_name}'",
                )
                return None

    def generic_visit(self, node: ast.AST) -> None:
        """Called if no explicit visitor function exists for a node."""
        # TODO: for assignment statements unused_code unit should be whole assignment statement instead of a name itself

        # Note: Node is None if file is empty, contains only a docstring, a comment or has a SyntaxError.
        if not node:
            return None

        for _, value in ast.iter_fields(node):
            if isinstance(value, list):
                self._handle_ast_list(value)
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
