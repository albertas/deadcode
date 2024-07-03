import ast
from itertools import chain
import os
import re
import string
import sys
from logging import getLogger

from pathlib import Path

from typing import Callable, Dict, List, Optional, Set, TextIO, Union, Iterable
from deadcode.constants import UnusedCodeType
from deadcode.data_types import Args, Part
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.utils import LoggingList, LoggingSet
from deadcode.visitor import utils
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.utils.nested_scopes import NestedScope

from deadcode.visitor import noqa
from deadcode.utils.print_ast import print_ast as show  # noqa: F401
from deadcode.visitor import lines
from deadcode.visitor.ignore import (
    ERROR_CODES,
    IGNORED_VARIABLE_NAMES,
    _get_unused_items,
    _match,
    _match_many,
    _assigns_special_variable__all__,
    _ignore_class,
    _ignore_import,
    _ignore_function,
    _ignore_method,
    _ignore_variable,
)

logger = getLogger()


class DeadCodeVisitor(ast.NodeVisitor):
    """Finds dead code."""

    def __init__(self, filenames: List[str], args: Args) -> None:
        self.filenames = filenames

        self.args = args

        self.ignore_decorators: List[str] = []

        verbose = False
        # verbose = args.verbose
        self.verbose = verbose

        self.defined_attrs: List[CodeItem] = LoggingList('attribute', verbose)
        self.defined_classes: List[CodeItem] = LoggingList('class', verbose)
        self.defined_funcs: List[CodeItem] = LoggingList('function', verbose)
        self.defined_imports: List[CodeItem] = LoggingList('import', verbose)
        self.defined_methods: List[CodeItem] = LoggingList('method', verbose)
        self.defined_props: List[CodeItem] = LoggingList('property', verbose)
        self.defined_vars: List[CodeItem] = LoggingList('variable', verbose)
        self.unused_file: List[CodeItem] = LoggingList('unused_file', verbose)
        self.unreachable_code: List[CodeItem] = LoggingList('unreachable_code', verbose)

        self.used_names: Set[str] = LoggingSet('name', self.verbose)

        self.filename = Path()
        self.code: List[str] = []

        # Note: scope is a stack containing current module name, class names, function names
        self.scope_parts: List[str] = []

        # This flag is used to stop registering code definitions in a code item
        # during recursive its parsing
        self.should_ignore_new_definitions = False

        self.noqa_lines: Dict[bytes, Set[int]] = {}
        self.scopes = NestedScope()

    @property
    def scope(self) -> str:
        return '.'.join(self.scope_parts)

    def add_used_name(self, name: str, scope: Optional[str] = None) -> None:
        # TODO: Usage should be tracked on CodeItem.

        # TODO: Lets first resolve, how to correctly set the type of a function argument.
        # We should have CodeItem as a type, not only name as string.
        # TODO: investigate: am I always able to retrieve the type of a variable?

        self.used_names.add(name)
        self.scopes.mark_as_used(name, self.scope)

    def visit_abstract_syntax_trees(self) -> None:
        for file_path in self.filenames:
            with open(file_path, 'rb') as f:
                filename = os.path.basename(file_path)
                module_name = os.path.splitext(filename)[0]
                self.scope_parts = [module_name]

                file_content = f.read()
                if file_content.strip() or (filename.startswith('__') and filename.endswith('__.py')):
                    self.noqa_lines = noqa.parse_noqa(file_content)

                    node = parse_abstract_syntax_tree(file_content, args=self.args, filename=file_path)
                    self.filename = Path(file_path)
                    self.visit(node)
                else:
                    self.unused_file.append(
                        CodeItem(
                            name=filename,
                            type_='unused_file',
                            filename=Path(file_path),
                            message='Empty file',
                        )
                    )

    def get_unused_code_items(self) -> Iterable[CodeItem]:
        """
        Return ordered list of unused CodeItem objects.
        """

        unused_code = chain(
            self.unused_attrs,
            self.unused_classes,
            self.unused_funcs,
            self.unused_imports,
            self.unused_methods,
            self.unused_props,
            self.unused_vars,
            # self.unreachable_code,  # TODO: removal of unreachable_code has a lot of edge cases
            self.unused_file,
        )

        return sorted(unused_code, key=lambda item: (item.filename, item.name_line or 0))

    @property
    def unused_classes(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_classes, self.used_names)

    @property
    def unused_funcs(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_funcs, self.used_names)

    @property
    def unused_imports(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_imports, self.used_names)

    @property
    def unused_methods(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_methods, self.used_names)

    @property
    def unused_props(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_props, self.used_names)

    @property
    def unused_vars(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_vars, self.used_names)

    @property
    def unused_attrs(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_attrs, self.used_names)

    def _log(self, *args, file: Optional[TextIO] = None, force: bool = False) -> None:  # type: ignore
        if self.verbose or force:
            file = file or sys.stdout
            try:
                print(*args, file=file)
            except UnicodeEncodeError:
                # Some terminals can't print Unicode symbols.
                x = ' '.join(map(str, args))
                print(x.encode(), file=file)

    def _add_aliases(self, node: Union[ast.Import, ast.ImportFrom]) -> None:
        """
        We delegate to this method instead of using visit_alias() to have
        access to line numbers and to filter imports from __future__.
        """
        # TODO: store full module path. Consider relative and absolute module import collisions.

        assert isinstance(node, (ast.Import, ast.ImportFrom))
        for name_and_alias in node.names:
            # Store only top-level module name ("os.path" -> "os").
            # We can't easily detect when "os.path" is used.
            name = name_and_alias.name.partition('.')[0]
            alias = name_and_alias.asname
            self._define(
                self.defined_imports,
                alias or name,
                first_node=name_and_alias,
                ignore=_ignore_import,
            )
            if alias is not None:
                self.add_used_name(name_and_alias.name)

    def _handle_conditional_node(self, node: Union[ast.If, ast.IfExp, ast.While], name: str) -> None:
        if utils.condition_is_always_false(node.test):
            self._define(
                self.unreachable_code,
                name,
                node,
                last_node=node.body if isinstance(node, ast.IfExp) else node.body[-1],
                message=f'Unsatisfiable `{name}` condition',
            )
        elif utils.condition_is_always_true(node.test):
            else_body = node.orelse
            if name == 'ternary':
                self._define(
                    self.unreachable_code,
                    name,
                    else_body,  # type: ignore
                    message='Unreachable `else` expression',
                )
            elif else_body:
                self._define(
                    self.unreachable_code,
                    'else',
                    else_body[0],  # type: ignore
                    last_node=else_body[-1],  # type: ignore
                    message='Unreachable `else` block',
                )
            elif name == 'if':
                # Redundant if-condition without else block.
                self._define(
                    self.unreachable_code,
                    name,
                    node,
                    message='Redundant `if` condition',
                )

    def _define(
        self,
        collection: List[CodeItem],
        name: str,
        first_node: ast.AST,
        last_node: Optional[ast.AST] = None,
        message: str = '',
        ignore: Optional[Callable[[Path, str], bool]] = None,
    ) -> None:
        # TODO: add support for ignore_definitions, ignore_definitions_if_inherits_from options
        self._log(
            f'Options ignore_definitions, ignore_definitions_if_inherits_from not implemented yet. '
            f'Got these values: ignore_definitions={self.args.ignore_definitions}, '
            f'ignore_definitions_if_inherits_from={self.args.ignore_definitions_if_inherits_from}'
        )

        def ignored(lineno: int, type_: UnusedCodeType) -> bool:
            return bool(
                (ignore and ignore(self.filename, name))
                or _match(name, self.args.ignore_names)
                or _match(self.filename, self.args.ignore_names_in_files)
                or self.should_ignore_new_definitions
                or noqa.ignore_line(self.noqa_lines, lineno, ERROR_CODES[type_])
            )

        last_node = last_node or first_node
        type_: UnusedCodeType = collection.type_  # type: ignore

        first_lineno = lines.get_first_line_number(first_node)
        last_lineno = lines.get_last_line_number(last_node)

        inherits_from = getattr(first_node, 'inherits_from', None)
        code_item = CodeItem(
            name=name,
            type_=type_,
            filename=self.filename,
            code_parts=[Part(first_lineno, last_lineno, last_node.col_offset, last_node.end_col_offset or 0)],
            scope=self.scope,
            name_line=last_node.lineno,  # TODO: Maybe this should be a property?
            name_column=last_node.col_offset,  # TODO: Maybe this should be a property?
            message=message,
            inherits_from=inherits_from,
        )

        self.scopes.add(code_item)

        if ignored(first_lineno, type_=type_):
            self._log(f'Ignoring {type_} "{name}"')
        else:
            collection.append(code_item)

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
            self.add_used_name(node.attr)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        """
        Parse variable names in old format strings:

        "%(my_var)s" % locals()
        """
        if isinstance(node.left, ast.Str) and isinstance(node.op, ast.Mod) and self._is_locals_call(node.right):
            self.used_names |= set(re.findall(r'%\((\w+)\)', node.left.s))

    def visit_Call(self, node: ast.Call) -> None:
        # Count getattr/hasattr(x, "some_attr", ...) as usage of some_attr.
        if isinstance(node.func, ast.Name) and (
            (node.func.id == 'getattr' and 2 <= len(node.args) <= 3)
            or (node.func.id == 'hasattr' and len(node.args) == 2)
        ):
            attr_name_arg = node.args[1]
            if isinstance(attr_name_arg, ast.Str):
                self.add_used_name(attr_name_arg.s)

        # Parse variable names in new format strings:
        # "{my_var}".format(**locals())
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Str)
            and node.func.attr == 'format'
            and any(kw.arg is None and self._is_locals_call(kw.value) for kw in node.keywords)
        ):
            self._handle_new_format_string(node.func.value.s)

    def _handle_new_format_string(self, s: str) -> None:
        def is_identifier(name: str) -> bool:
            return bool(re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', name))

        parser = string.Formatter()
        try:
            names = [name for _, name, _, _ in parser.parse(s) if name]
        except ValueError:
            # Invalid format string.
            names = []

        for field_name in names:
            # Remove brackets and their contents: "a[0][b].c[d].e" -> "a.c.e",
            # then split the resulting string: "a.b.c" -> ["a", "b", "c"]
            vars = re.sub(r'\[\w*\]', '', field_name).split('.')
            for var in vars:
                if is_identifier(var):
                    self.add_used_name(var)

    @staticmethod
    def _is_locals_call(node: ast.AST) -> bool:
        """Return True if the node is `locals()`."""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'locals'
            and not node.args
            and not node.keywords
        )

    def get_inherits_from(self, node: ast.AST) -> Optional[List[str]]:
        """Returns a set of base classes from any level in inheritance tree."""

        if not (bases_attr := getattr(node, 'bases', None)):
            return None

        bases = [base.id for base in bases_attr if getattr(base, 'id', None)]
        inherits_from = bases[:]

        for base in bases:
            if base_code_item := self.scopes.get(name=base, scope=self.scope):
                if base_inherits_from := getattr(base_code_item, 'inherits_from', None):
                    inherits_from.extend(base_inherits_from)

        return inherits_from

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

        if '@property' in decorator_names:
            type_ = 'property'
        elif '@staticmethod' in decorator_names or '@classmethod' in decorator_names or first_arg == 'self':
            type_ = 'method'
        else:
            type_ = 'function'

        if any(_match(name, self.ignore_decorators) for name in decorator_names):
            self._log(f'Ignoring {type_} "{node.name}" (decorator whitelisted)')
        elif type_ == 'property':
            self._define(self.defined_props, node.name, node)
        elif type_ == 'method':
            self._define(self.defined_methods, node.name, node, ignore=_ignore_method)
        else:
            self._define(self.defined_funcs, node.name, node, ignore=_ignore_function)

    def visit_If(self, node: ast.If) -> None:
        self._handle_conditional_node(node, 'if')

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._handle_conditional_node(node, 'ternary')

    def visit_Import(self, node: ast.Import) -> None:
        self._add_aliases(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != '__future__':
            self._add_aliases(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Load, ast.Del)) and node.id not in IGNORED_VARIABLE_NAMES:
            self.add_used_name(node.id)
        elif isinstance(node.ctx, (ast.Param, ast.Store)):
            self._define_variable(node.id, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if _assigns_special_variable__all__(node):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            for elt in node.value.elts:
                if isinstance(elt, ast.Str):
                    self.add_used_name(elt.s)

    def visit_While(self, node: ast.While) -> None:
        self._handle_conditional_node(node, 'while')

    # def visit_MatchClass(self, node: ast.MatchClass) -> None:  # type: ignore
    def visit_MatchClass(self, node) -> None:  # type: ignore
        for kwd_attr in node.kwd_attrs:
            self.add_used_name(kwd_attr)

    def visit(self, node: ast.AST) -> None:
        node_name = getattr(node, 'name', None)

        # > TODO: Expr scope has to be updated after visiting nested nodes.
        # Do I have to merge custom visits with visit method in order to achieve this?
        #
        # I should write a unit test with only an exrepssion and check which methods are being called.
        # I should only handled that single expression handling properly.

        if inherits_from := self.get_inherits_from(node):
            node.inherits_from = inherits_from  # type: ignore

        should_turn_off_ignore_new_definitions = False
        if (
            # Name is in ignore_definitions
            node_name and _match(node_name, self.args.ignore_definitions)
        ) or (
            # Class inherits from ignore_definitions_if_inherits_from
            inherits_from and _match_many(inherits_from, self.args.ignore_definitions_if_inherits_from)
        ):
            if not self.should_ignore_new_definitions:
                self.should_ignore_new_definitions = True
                should_turn_off_ignore_new_definitions = True

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, None)

        if visitor:
            visitor(node)

        # TODO: use decorator for this code chunk
        was_scope_increased = True
        if isinstance(node, ast.ClassDef):
            self.scope_parts.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.scope_parts.append(node.name)
        else:
            was_scope_increased = False

        # Class inherits from ignore_bodies_if_inherits_from
        if inherits_from and _match_many(inherits_from, self.args.ignore_bodies_if_inherits_from):
            if not self.should_ignore_new_definitions:
                self.should_ignore_new_definitions = True
                should_turn_off_ignore_new_definitions = True

        # There isn't a clean subset of node types that might have type
        # comments, so just check all of them.
        type_comment = getattr(node, 'type_comment', None)
        if type_comment is not None:
            mode = 'func_type' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'eval'
            self.visit(ast.parse(type_comment, filename='<type_comment>', mode=mode))

        ###########
        # """Called if no explicit visitor function exists for a node."""
        # TODO: for assignment statements unused_code unit should be whole assignment statement instead of a name itself
        # Note: Node is None if file is empty, contains only a docstring, a comment or has a SyntaxError.
        if node:
            for _, value in ast.iter_fields(node):
                if isinstance(value, list):
                    self._handle_ast_list(value)
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)

        # TODO: use decorator for this code chunk
        if should_turn_off_ignore_new_definitions:
            self.should_ignore_new_definitions = False

        # TODO: use decorator for this code chunk
        if was_scope_increased:
            self.scope_parts.pop()

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
