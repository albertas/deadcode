import ast
from itertools import chain
import io
import os
import re
import string
import sys
import tokenize

from pathlib import Path

from typing import Any, TextIO, cast
from collections.abc import Callable, Iterable
from deadcode.constants import UnusedCodeType
from deadcode.data_types import Args, Part
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.utils import LoggingList, LoggingSet
from deadcode.visitor import utils
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.utils.nested_scopes import NestedScope
from deadcode.visitor.usage_graph import compute_live_item_keys

from deadcode.visitor import noqa
from deadcode.utils.print_ast import print_ast as show  # noqa: F401
from deadcode.utils.print_safely import print_safely
from deadcode.visitor import lines
from deadcode.visitor.module_exports import collect_module_exports
from deadcode.visitor.ignore import (
    ERROR_CODES,
    IGNORED_INTERFACE_DECORATOR_NAMES,
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

TYPE_CHECKER_COMMENT_PATTERN = re.compile(r'^(?:(?:type|ty|pyright|pytype|mypy)\s*:|pyre-)', re.IGNORECASE)


class DeadCodeVisitor(ast.NodeVisitor):
    """Finds dead code."""

    def __init__(self, filenames: list[str], args: Args) -> None:
        self.filenames = filenames

        self.args = args

        self.ignore_decorators: list[str] = []

        verbose = False
        self.verbose = verbose

        self.defined_attrs: list[CodeItem] = LoggingList('attribute', verbose)
        self.defined_classes: list[CodeItem] = LoggingList('class', verbose)
        self.defined_funcs: list[CodeItem] = LoggingList('function', verbose)
        self.defined_imports: list[CodeItem] = LoggingList('import', verbose)
        self.defined_methods: list[CodeItem] = LoggingList('method', verbose)
        self.defined_props: list[CodeItem] = LoggingList('property', verbose)
        self.defined_vars: list[CodeItem] = LoggingList('variable', verbose)
        self.defined_names: list[CodeItem] = LoggingList('name', verbose)
        self.unused_file: list[CodeItem] = LoggingList('unused_file', verbose)
        self.unreachable_body: list[CodeItem] = LoggingList('unreachable_body', verbose)
        self.unreachable_code: list[CodeItem] = LoggingList('unreachable_code', verbose)
        self.commented_out_code: list[CodeItem] = LoggingList('commented_out_code', verbose)

        self.used_names: set[str] = LoggingSet('name', self.verbose)

        self.module_name: str = ''
        self.module_exports: dict[str, set[str]] = {}
        self.bare_used_names: dict[str, set[str]] = {}
        self.wildcard_imports: dict[str, set[str]] = {}
        self.explicit_imports: dict[str, set[str]] = {}
        self.qualified_imports: dict[str, dict[str, str]] = {}
        self.import_edges: dict[str, dict[str, set[tuple[str, str]]]] = {}
        self.module_definitions: dict[str, set[str]] = {}

        self.filename = Path()
        self.code: list[str] = []
        self.scope_kinds: list[str] = []

        # Note: scope is a stack containing current module name, class names, function names
        self.scope_parts: list[str] = []

        # This flag is used to stop registering code definitions in a code item
        # during recursive its parsing
        self.should_ignore_new_definitions = False

        self.noqa_lines: dict[bytes, set[int]] = {}
        self.scopes = NestedScope()

        # Usage-context stack: the innermost enclosing collected `CodeItem`, or `None`
        # for an ignored definition or a root (module-level) context.
        self._usage_context_stack: list[CodeItem | None] = []
        # Ownership registry: usage sources `(module basename, used name)` mapped to the
        # identity tokens (`id(code_item)`) of the definitions owning the usage site.
        self._usage_owners: dict[tuple[str, str], set[int]] = {}
        # Bare-usage sources with no owning definition: they execute at import time
        # or belong to an ignore-protected definition, so they are live anchors.
        self._root_usage_sources: set[tuple[str, str]] = set()
        self._last_defined_item: CodeItem | None = None
        self._live_item_keys: set[tuple[str, str]] | None = None

        self._assignment_nodes: list[ast.Assign | ast.AnnAssign | ast.AugAssign] = []

    @property
    def scope(self) -> str:
        return '.'.join(self.scope_parts)

    def add_used_name(self, name: str, scope: str | None = None, *, is_bare: bool = False) -> None:
        # TODO: Usage should be tracked on CodeItem.

        # TODO: Lets first resolve, how to correctly set the type of a function argument.
        # We should have CodeItem as a type, not only name as string.
        # TODO: investigate: am I always able to retrieve the type of a variable?

        if is_bare:
            self.bare_used_names.setdefault(self.module_name, set()).add(name)
            source = (self.module_name, name)
            usage_context = self._usage_context_stack[-1] if self._usage_context_stack else None
            if usage_context is not None:
                self._usage_owners.setdefault(source, set()).add(id(usage_context))
            else:
                self._root_usage_sources.add(source)
        else:
            self.used_names.add(name)
        self.scopes.mark_as_used(name, self.scope)

    def _resolve_bare_usage(self, name: str, importer: str) -> set[tuple[str, str]] | None:
        """Resolve a bare usage of `name` in module `importer` to binding targets.

        Returns the set of ``(module, name)`` pairs the usage can bind to, or ``None`` when
        the usage is unresolvable or ambiguous (both fall back to the legacy suppression).
        """
        candidates: set[tuple[str, str]] = set()

        if name in self.module_definitions.get(importer, set()):
            candidates.add((importer, name))

        visited: set[tuple[str, str]] = set()
        expanded: set[tuple[str, str]] = set()
        frontier = list(self.import_edges.get(importer, {}).get(name, set()))
        while frontier:
            pair = frontier.pop()
            if pair in visited:
                # A cycle makes the usage unresolvable.
                return None
            visited.add(pair)
            edge_module, edge_name = pair
            # Package `__init__` twin hop (D6): `from x import n` can bind either in
            # `x.py` (module key `x`) or in `x/__init__.py` (module key `__init__`),
            # so every hop target also contributes its `__init__` twin. For a target
            # already keyed `__init__` the twin is the target itself. Twin candidates
            # only widen suppression; the `expanded` bookkeeping keeps every hop
            # target's out-edges enqueued once, so twin hops follow re-export chains
            # without inventing phantom cycles.
            for hop_module in {edge_module, '__init__'}:
                if (hop_module, edge_name) in expanded:
                    continue
                expanded.add((hop_module, edge_name))
                if edge_name in self.module_definitions.get(hop_module, set()):
                    candidates.add((hop_module, edge_name))
                frontier.extend(self.import_edges.get(hop_module, {}).get(edge_name, set()))

        if not candidates:
            for wildcard_module in self.wildcard_imports.get(importer, set()):
                exports = self.module_exports.get(wildcard_module)
                if exports is None:
                    # Unknown exports make the usage unresolvable.
                    return None
                if name in exports:
                    candidates.add((wildcard_module, name))

        if len(candidates) == 1:
            return candidates
        # No candidate at all, or more than one candidate: unresolvable or ambiguous.
        return None

    def _is_item_used(self, item: CodeItem) -> bool:
        module = os.path.splitext(os.path.basename(str(item.filename)))[0]
        if self._live_item_keys is None:
            self._live_item_keys = self._compute_live_item_keys()
        return (module, item.name) in self._live_item_keys

    def _compute_live_item_keys(self) -> set[tuple[str, str]]:
        """Run the reachability pass once and memoize the live item keys."""
        items = list(
            chain(
                self.defined_attrs,
                self.defined_classes,
                self.defined_funcs,
                self.defined_imports,
                self.defined_methods,
                self.defined_props,
                self.defined_vars,
                self.defined_names,
            )
        )
        owner_keys: dict[int, tuple[str, str]] = {
            id(item): (os.path.splitext(os.path.basename(str(item.filename)))[0], item.name) for item in items
        }

        return compute_live_item_keys(
            items,
            self.used_names,
            self._root_usage_sources,
            self._usage_owners,
            owner_keys,
            self._resolve_bare_usage,
            self.wildcard_imports,
            self.module_exports,
            self.explicit_imports,
        )

    def _collect_module_exports(self) -> None:
        for file_path in self.filenames:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                tree = ast.parse(file_content, filename=file_path)
            except (SyntaxError, OSError):
                continue
            exports = collect_module_exports(tree)
            if exports is not None:
                self.module_exports[module_name] = exports

    def visit_abstract_syntax_trees(self) -> None:
        self._collect_module_exports()
        for file_path in self.filenames:
            with open(file_path, 'rb') as f:
                filename = os.path.basename(file_path)
                module_name = os.path.splitext(filename)[0]
                self.module_name = module_name
                self.qualified_imports[self.module_name] = {}
                self.scope_parts = [module_name]
                self._usage_context_stack = []
                self._last_defined_item = None

                file_content = f.read()
                if file_content.strip() or (filename.startswith('__') and filename.endswith('__.py')):
                    self.noqa_lines = noqa.parse_noqa(file_content)

                    node = parse_abstract_syntax_tree(file_content, args=self.args, filename=file_path)
                    self.filename = Path(file_path)
                    self.code = file_content.decode('utf-8', errors='replace').splitlines()
                    self._collect_commented_out_code(file_content)
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
            self.unused_names,
            self.unreachable_body,
            self.unreachable_code,
            self.commented_out_code,
            self.unused_file,
        )

        return sorted(unused_code, key=lambda item: (item.filename, item.name_line or 0))

    @property
    def unused_classes(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_classes, self.used_names, is_used=self._is_item_used)

    @property
    def unused_funcs(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_funcs, self.used_names, is_used=self._is_item_used)

    @property
    def unused_imports(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_imports, self.used_names, is_used=self._is_item_used)

    @property
    def unused_methods(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_methods, self.used_names, is_used=self._is_item_used)

    @property
    def unused_props(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_props, self.used_names, is_used=self._is_item_used)

    @property
    def unused_vars(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_vars, self.used_names, is_used=self._is_item_used)

    @property
    def unused_attrs(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_attrs, self.used_names, is_used=self._is_item_used)

    @property
    def unused_names(self) -> Iterable[CodeItem]:
        return _get_unused_items(self.defined_names, self.used_names, is_used=self._is_item_used)

    def _log(self, *args, file: TextIO | None = None, force: bool = False) -> None:  # type: ignore
        if self.verbose or force:
            file = file or sys.stdout
            print_safely(' '.join(map(str, args)), file=file)

    def _add_aliases(self, node: ast.Import | ast.ImportFrom) -> None:
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
            self._record_qualified_import(node, name_and_alias)
            self._define(
                self.defined_imports,
                alias or name,
                first_node=name_and_alias,
                ignore=_ignore_import,
            )
            if alias is not None:
                self.add_used_name(name_and_alias.name)

    def _record_qualified_import(self, node: ast.Import | ast.ImportFrom, name_and_alias: ast.alias) -> None:
        """Record absolute imports so qualified names can be resolved."""
        qualified_imports = self.qualified_imports.setdefault(self.module_name, {})
        if isinstance(node, ast.Import):
            if name_and_alias.asname:
                qualified_imports[name_and_alias.asname] = name_and_alias.name
            else:
                top_level = name_and_alias.name.partition('.')[0]
                qualified_imports[top_level] = top_level
            return

        if node.level > 0 or node.module is None or node.module == '__future__':
            return
        if name_and_alias.name == '*':
            return
        local_name = name_and_alias.asname or name_and_alias.name
        qualified_imports[local_name] = f'{node.module}.{name_and_alias.name}'

    def _resolve_qualified_expression(self, expression: str) -> str | None:
        """Resolve the first component of a dotted expression through absolute imports."""
        first_component, separator, remaining = expression.partition('.')
        target = self.qualified_imports.get(self.module_name, {}).get(first_component)
        if target is None:
            return None
        return f'{target}{separator}{remaining}' if separator else target

    def _collect_commented_out_code(self, file_content: bytes) -> None:
        """Collect comments whose text parses as Python code."""
        try:
            tokens = list(tokenize.tokenize(io.BytesIO(file_content).readline))
        except (tokenize.TokenError, IndentationError):
            return
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            comment_text = token.string[1:]
            code_text = re.sub(r'#\s*noqa.*$', '', comment_text, flags=re.IGNORECASE).strip()
            if not self._is_commented_out_code(code_text):
                continue
            lineno, column = token.start
            if noqa.ignore_line(self.noqa_lines, lineno, ERROR_CODES['commented_out_code']):
                continue
            line = file_content.splitlines(keepends=True)[lineno - 1]
            prefix = line.decode('utf-8', errors='replace')[:column]
            comment_byte_end = len(prefix.encode('utf-8')) + len(token.string.encode('utf-8'))
            removal_start = len(prefix.rstrip().encode('utf-8'))
            self.commented_out_code.append(
                CodeItem(
                    name=code_text,
                    type_='commented_out_code',
                    filename=self.filename,
                    code_parts=[Part(lineno, lineno, removal_start, comment_byte_end)],
                    name_line=lineno,
                    name_column=column,
                    message='Commented out code',
                )
            )

    @staticmethod
    def _is_commented_out_code(code_text: str) -> bool:
        """Return True when a comment text looks like a Python expression or statement."""
        if TYPE_CHECKER_COMMENT_PATTERN.match(code_text):
            return False
        statement_keywords = (
            'import ',
            'from ',
            'def ',
            'class ',
            'return',
            'raise',
            'break',
            'continue',
            'pass',
            'if ',
            'for ',
            'while ',
            'with ',
            'try:',
            'except',
            'elif ',
            'else:',
        )
        has_code_marker = any(marker in code_text for marker in ('(', '=', '[', '{'))
        if not has_code_marker and not code_text.startswith(statement_keywords):
            return False
        try:
            expression = ast.parse(code_text, mode='eval')
        except SyntaxError:
            expression = None
        if expression is not None and not isinstance(expression.body, (ast.Constant, ast.Name)):
            return True
        try:
            module = ast.parse(code_text)
        except SyntaxError:
            return False
        return any(
            not isinstance(node, ast.Expr) or not isinstance(node.value, (ast.Constant, ast.Name))
            for node in module.body
        )

    def _handle_conditional_node(self, node: ast.If | ast.IfExp | ast.While, name: str) -> None:
        if utils.condition_is_always_false(node.test):
            self._define(
                self.unreachable_body,
                name,
                node,
                last_node=node.body if isinstance(node, ast.IfExp) else node.body[-1],
                message=f'Unsatisfiable `{name}` condition',
                removal_node=node,
            )
        elif utils.condition_is_always_true(node.test):
            else_body = node.orelse
            if name == 'ternary':
                self._define(
                    self.unreachable_body,
                    name,
                    else_body,  # type: ignore
                    message='Unreachable `else` expression',
                )
            elif else_body:
                self._define(
                    self.unreachable_body,
                    'else',
                    else_body[0],  # type: ignore
                    last_node=else_body[-1],  # type: ignore
                    message='Unreachable `else` block',
                    ignore_linenos=self._get_else_linenos(node, else_body[0]),  # type: ignore
                )
            elif name == 'if':
                # Redundant if-condition without else block.
                self._define(
                    self.unreachable_body,
                    name,
                    node,
                    message='Redundant `if` condition',
                    removal_node=node,
                )

    def _get_else_linenos(self, node: ast.If | ast.IfExp | ast.While, first_else_node: ast.AST) -> tuple[int, ...]:
        """Return line numbers of the `else` keyword preceding the first else statement."""
        for lineno in range(int(cast('Any', first_else_node).lineno) - 1, int(cast('Any', node).lineno), -1):
            if 0 < lineno <= len(self.code) and self.code[lineno - 1].strip().startswith('else:'):
                return (lineno,)
        return ()

    def _define(
        self,
        collection: list[CodeItem],
        name: str,
        first_node: ast.AST,
        last_node: ast.AST | None = None,
        message: str = '',
        ignore: Callable[[Path, str], bool] | None = None,
        *,
        decorator_names: Iterable[str] = (),
        removal_node: ast.AST | None = None,
        ignore_linenos: Iterable[int] = (),
    ) -> None:
        def ignored(linenos: Iterable[int], type_: UnusedCodeType) -> bool:
            return bool(
                (ignore and ignore(self.filename, name))
                or _match(name, self.args.ignore_names)
                or _match(self.filename, self.args.ignore_names_in_files)
                or _match_many(decorator_names, self.args.ignore_names_if_decorated_with)
                or _match_many(decorator_names, IGNORED_INTERFACE_DECORATOR_NAMES)
                or (
                    (item_inherits_from := getattr(first_node, 'inherits_from', None))
                    and _match_many(item_inherits_from, self.args.ignore_names_if_inherits_from)
                )
                or self.should_ignore_new_definitions
                or any(noqa.ignore_line(self.noqa_lines, lineno, ERROR_CODES[type_]) for lineno in linenos)
            )

        last_node = last_node or first_node
        type_: UnusedCodeType = collection.type_  # type: ignore

        first_lineno = lines.get_first_line_number(first_node)
        last_lineno = lines.get_last_line_number(last_node)
        name_line = int(cast('Any', last_node).lineno)

        removal_node_end_lineno = getattr(removal_node, 'end_lineno', None)
        if removal_node is not None and removal_node_end_lineno is not None:
            line_start = lines.get_first_line_number(removal_node)
            line_end = removal_node_end_lineno
            col_start = int(cast('Any', removal_node).col_offset)
            col_end = int(cast('Any', removal_node).end_col_offset or 0)
        else:
            line_start = first_lineno
            line_end = last_lineno
            col_start = int(cast('Any', last_node).col_offset)
            col_end = int(cast('Any', last_node).end_col_offset or 0)

        inherits_from = getattr(first_node, 'inherits_from', None)
        code_item = CodeItem(
            name=name,
            type_=type_,
            filename=self.filename,
            code_parts=[Part(line_start, line_end, col_start, col_end)],
            scope=self.scope,
            name_line=name_line,  # TODO: Maybe this should be a property?
            name_column=int(cast('Any', last_node).col_offset),  # TODO: Maybe this should be a property?
            message=message,
            inherits_from=inherits_from,
        )

        self.scopes.add(code_item)
        self._last_defined_item = code_item

        if ignored((first_lineno, name_line, *ignore_linenos), type_=type_):
            self._log(f'Ignoring {type_} "{name}"')
            # An ignored definition contributes no owner: usages inside its body
            # stay root usages and keep their targets alive.
            self._last_defined_item = None
        else:
            collection.append(code_item)
            is_module_level_definition = any(
                collection is c for c in (self.defined_funcs, self.defined_classes, self.defined_vars)
            ) and self.scope_parts == [self.module_name]
            if is_module_level_definition:
                self.module_definitions.setdefault(self.module_name, set()).add(name)

    def _get_assignment_removal_node(self, target: ast.AST) -> ast.AST | None:
        if not self._assignment_nodes:
            return None

        statement = self._assignment_nodes[-1]
        if statement.end_lineno is None or statement.end_lineno <= statement.lineno:
            return None

        if isinstance(statement, ast.Assign):
            if len(statement.targets) == 1 and statement.targets[0] is target:
                return statement
        elif isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
            if statement.target is target:
                return statement

        return None

    def _define_variable(self, name: str, node: ast.AST) -> None:
        collection = self.defined_names if self.scope_kinds and self.scope_kinds[-1] == 'class' else self.defined_vars
        self._define(
            collection,
            name,
            node,
            ignore=_ignore_variable,
            removal_node=self._get_assignment_removal_node(node),
        )

    def _record_annotation_names(self, annotation: ast.AST | None) -> None:
        for name in utils.collect_names_from_annotation_strings(annotation):
            self.add_used_name(name, is_bare=True)

    def visit_arg(self, node: ast.arg) -> None:
        self._record_annotation_names(node.annotation)

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
        if (
            isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)
            and isinstance(node.op, ast.Mod)
            and self._is_locals_call(node.right)
        ):
            self.used_names |= set(re.findall(r'%\((\w+)\)', node.left.value))

    def visit_Call(self, node: ast.Call) -> None:
        # Count getattr/hasattr(x, "some_attr", ...) as usage of some_attr.
        if isinstance(node.func, ast.Name) and (
            (node.func.id == 'getattr' and 2 <= len(node.args) <= 3)
            or (node.func.id == 'hasattr' and len(node.args) == 2)
        ):
            attr_name_arg = node.args[1]
            if isinstance(attr_name_arg, ast.Constant) and isinstance(attr_name_arg.value, str):
                self.add_used_name(attr_name_arg.value)

        # Parse variable names in new format strings:
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and node.func.attr == 'format'
            and any(kw.arg is None and self._is_locals_call(kw.value) for kw in node.keywords)
        ):
            self._handle_new_format_string(node.func.value.value)

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

    def _get_decorator_names(self, node: ast.AST) -> list[str]:
        """Returns decorator names of the given node, including resolved absolute imports."""
        decorator_names = []
        for decorator in getattr(node, 'decorator_list', ()):
            name = utils.get_decorator_name(decorator)
            decorator_names.append(name)
            resolved = self._resolve_qualified_expression(name[1:])
            if resolved is not None and '@' + resolved != name:
                decorator_names.append('@' + resolved)
        return decorator_names

    def get_inherits_from(self, node: ast.AST) -> list[str] | None:
        """Returns a set of base classes from any level in inheritance tree."""

        if not (bases_attr := getattr(node, 'bases', None)):
            return None

        bases = []
        for base in bases_attr:
            bases.extend(utils.get_base_class_names(base))
            if isinstance(base, (ast.Name, ast.Attribute)):
                source = ast.unparse(base)
                resolved = self._resolve_qualified_expression(source)
                if resolved is not None and resolved != source:
                    bases.append(resolved)
        inherits_from = bases[:]

        for base in bases:
            if base_code_item := self.scopes.get(name=base, scope=self.scope):
                if base_inherits_from := getattr(base_code_item, 'inherits_from', None):
                    inherits_from.extend(base_inherits_from)

        return list(dict.fromkeys(inherits_from))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        decorator_names = self._get_decorator_names(node)
        for decorator in node.decorator_list:
            if _match(utils.get_decorator_name(decorator), self.ignore_decorators):
                self._log(f'Ignoring class "{node.name}" (decorator whitelisted)')
                break
        else:
            self._define(
                self.defined_classes,
                node.name,
                node,
                ignore=_ignore_class,
                decorator_names=decorator_names,
            )

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._record_annotation_names(node.returns)
        decorator_names = self._get_decorator_names(node)

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
            self._define(self.defined_props, node.name, node, decorator_names=decorator_names)
        elif type_ == 'method':
            self._define(self.defined_methods, node.name, node, ignore=_ignore_method, decorator_names=decorator_names)
        else:
            self._define(self.defined_funcs, node.name, node, ignore=_ignore_function, decorator_names=decorator_names)

    def visit_If(self, node: ast.If) -> None:
        self._handle_conditional_node(node, 'if')

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._handle_conditional_node(node, 'ternary')

    def visit_Import(self, node: ast.Import) -> None:
        self._add_aliases(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != '__future__':
            if node.module is not None:
                explicit_imports = self.explicit_imports.setdefault(self.module_name, set())
                edges = self.import_edges.setdefault(self.module_name, {})
                for name_and_alias in node.names:
                    if name_and_alias.name != '*':
                        explicit_imports.add(name_and_alias.asname or name_and_alias.name)
                        edges.setdefault(name_and_alias.asname or name_and_alias.name, set()).add(
                            (node.module.rpartition('.')[2], name_and_alias.name)
                        )
                if any(name_and_alias.name == '*' for name_and_alias in node.names):
                    wildcard_module = node.module.rpartition('.')[2]
                    self.wildcard_imports.setdefault(self.module_name, set()).add(wildcard_module)
            self._add_aliases(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Load, ast.Del)) and node.id not in IGNORED_VARIABLE_NAMES:
            self.add_used_name(node.id, is_bare=True)
        elif isinstance(node.ctx, (ast.Param, ast.Store)):
            self._define_variable(node.id, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if _assigns_special_variable__all__(node):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.add_used_name(elt.value)

        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == 'MIDDLEWARE'
            and len(self.scope_parts) == 1
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    final_component = elt.value.rpartition('.')[2]
                    if final_component:
                        self.add_used_name(final_component)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_annotation_names(node.annotation)

    def visit_While(self, node: ast.While) -> None:
        self._handle_conditional_node(node, 'while')

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

        decorator_names = self._get_decorator_names(node)

        should_turn_off_ignore_new_definitions = False
        if (
            (
                # Name is in ignore_definitions
                node_name and _match(node_name, self.args.ignore_definitions)
            )
            or (
                # Class inherits from ignore_definitions_if_inherits_from
                inherits_from and _match_many(inherits_from, self.args.ignore_definitions_if_inherits_from)
            )
            or (
                # Definition is decorated with ignore_definitions_if_decorated_with
                decorator_names and _match_many(decorator_names, self.args.ignore_definitions_if_decorated_with)
            )
        ):
            if not self.should_ignore_new_definitions:
                self.should_ignore_new_definitions = True
                should_turn_off_ignore_new_definitions = True

        is_definition_node = isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        if is_definition_node:
            # Decorator expressions are root usages: they run at definition time and
            # decorate names are conservative anchors, so they are visited before the
            # definition's own usage context is pushed.
            decorators: list[ast.expr] = getattr(node, 'decorator_list', [])
            for decorator in decorators:
                self._usage_context_stack.append(None)
                try:
                    self.visit(decorator)
                finally:
                    self._usage_context_stack.pop()
            # A definition suppressed without `_define` (e.g. a decorator-whitelisted
            # class) contributes no owner either.
            self._last_defined_item = None

        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, None)

        if visitor:
            visitor(node)

        # TODO: use decorator for this code chunk
        was_scope_increased = True
        if isinstance(node, ast.ClassDef):
            self.scope_parts.append(node.name)
            self.scope_kinds.append('class')
            self._usage_context_stack.append(self._last_defined_item)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.scope_parts.append(node.name)
            self.scope_kinds.append('function')
            self._usage_context_stack.append(self._last_defined_item)
        else:
            was_scope_increased = False

        # Class inherits from ignore_bodies_if_inherits_from
        if inherits_from and _match_many(inherits_from, self.args.ignore_bodies_if_inherits_from):
            if not self.should_ignore_new_definitions:
                self.should_ignore_new_definitions = True
                should_turn_off_ignore_new_definitions = True

        # Name is in ignore_bodies_of
        if node_name and _match(node_name, self.args.ignore_bodies_of):
            if not self.should_ignore_new_definitions:
                self.should_ignore_new_definitions = True
                should_turn_off_ignore_new_definitions = True

        # Definition is decorated with ignore_bodies_if_decorated_with
        if decorator_names and _match_many(decorator_names, self.args.ignore_bodies_if_decorated_with):
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
        # Single-target assignments are removed as a whole statement via `removal_node`.
        # Multi-target and tuple assignments still fall back to reporting the name only.
        # Note: Node is None if file is empty, contains only a docstring, a comment or has a SyntaxError.
        pushed_assignment_node: ast.Assign | ast.AnnAssign | ast.AugAssign | None = None
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            pushed_assignment_node = node
            self._assignment_nodes.append(node)
        try:
            if node:
                for field_name, value in ast.iter_fields(node):
                    if is_definition_node and field_name == 'decorator_list':
                        # Decorators have already been visited as root usages.
                        continue
                    if isinstance(value, list):
                        self._handle_ast_list(value)
                        for item in value:
                            if isinstance(item, ast.AST):
                                self.visit(item)
                    elif isinstance(value, ast.AST):
                        self.visit(value)
        finally:
            if pushed_assignment_node is not None:
                self._assignment_nodes.pop()

        # TODO: use decorator for this code chunk
        if should_turn_off_ignore_new_definitions:
            self.should_ignore_new_definitions = False

        # TODO: use decorator for this code chunk
        if was_scope_increased:
            self.scope_parts.pop()
            self.scope_kinds.pop()
            self._usage_context_stack.pop()

    def _handle_ast_list(self, ast_list: list[ast.AST]) -> None:
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
