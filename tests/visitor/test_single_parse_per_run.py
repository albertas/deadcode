import ast
import os

from deadcode.actions.get_unused_import_parts import get_unused_import_parts
from deadcode.data_types import AbstractSyntaxTree, Args, FileContent, Part
from deadcode.visitor import dead_code_visitor
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.dead_code_visitor import DeadCodeVisitor
from deadcode.visitor.module_exports import collect_module_exports

FILES = {
    'exports.py': b"__all__ = ['exported']\n\nexported = 1\nhidden = 2\n",
    'uses.py': b'from exports import *\nfrom os import chdir, getcwd\n\nprint(exported)\nprint(chdir)\n',
    'dynamic.py': b"__all__ = ['a']\n__all__ += extra\n",
    'only_comments.py': b'# just a comment\n',
    'empty.py': b'\n    ',
    'broken.py': b'def broken(:\n',
}


def make_import_item(name: str, name_line: int, name_column: int, code_parts: list[Part]) -> CodeItem:
    return CodeItem(
        name=name,
        type_='import',
        filename='uses.py',
        code_parts=code_parts,
        name_line=name_line,
        name_column=name_column,
    )


def test_each_file_is_parsed_exactly_once_per_run(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = FILES

    parsed_filenames: list[str] = []
    real_parse = dead_code_visitor.parse_abstract_syntax_tree

    def counting_parse(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
        parsed_filenames.append(str(filename))
        return real_parse(file_content, args=args, filename=filename)

    monkeypatch.setattr(dead_code_visitor, 'parse_abstract_syntax_tree', counting_parse)

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: one parse call per file, in the given file order.
    assert parsed_filenames == list(FILES)
    assert visitor.get_unused_code_items() is not None


def test_module_exports_match_a_fresh_parse_of_each_file(virtual_file_system):
    # Having
    virtual_file_system.files = FILES

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: the cached exports equal the ones a fresh plain parse produces.
    expected_exports = {}
    for filename, content in FILES.items():
        try:
            tree = ast.parse(content, filename=filename)
        except SyntaxError:
            continue
        exports = collect_module_exports(tree)
        if exports is not None:
            expected_exports[os.path.splitext(filename)[0]] = exports

    assert visitor.module_exports == expected_exports


def test_findings_are_produced_from_the_cached_trees(virtual_file_system):
    # Having
    virtual_file_system.files = FILES

    # When
    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    # Then: export resolution, import analysis and the empty-file report keep
    # their previous results for the same fixtures.
    findings = {(str(item.filename), item.type_, item.name) for item in visitor.get_unused_code_items()}
    assert ('exports.py', 'variable', 'hidden') in findings
    assert ('uses.py', 'import', 'getcwd') in findings
    assert ('empty.py', 'unused_file', 'empty.py') in findings
    # `a` in dynamic.py is listed in `__all__`, so it counts as exported.
    assert not [item for item in findings if item[0] == 'dynamic.py']
    assert not [item for item in findings if item[0] == 'broken.py']


def test_cached_tree_is_reused_without_parsing_content_again(monkeypatch):
    # Having
    content = b'import foo, bar\n\nprint(foo)\n'
    item = make_import_item('bar', 1, 11, [Part(1, 1, 11, 14)])

    parse_calls: list[tuple] = []
    real_parse = ast.parse

    def counting_parse(*args: object, **kwargs: object) -> ast.Module:
        parse_calls.append(args)
        return real_parse(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr('deadcode.actions.get_unused_import_parts.ast.parse', counting_parse)

    tree = ast.parse(content)
    parse_calls.clear()

    # When
    parts_from_cached_tree = get_unused_import_parts(content, [item], cached_tree=tree)

    # Then: the cached tree is used and the result matches a fresh parse.
    assert parse_calls == []
    assert parts_from_cached_tree == get_unused_import_parts(content, [item])


def test_import_parts_analysis_matches_a_fresh_parse(virtual_file_system, monkeypatch):
    # Having
    virtual_file_system.files = FILES

    parsed_trees: dict[str, AbstractSyntaxTree] = {}
    real_parse = dead_code_visitor.parse_abstract_syntax_tree

    def tree_recording_parse(file_content: FileContent, args: Args, filename: str) -> AbstractSyntaxTree:
        node = real_parse(file_content, args=args, filename=filename)
        parsed_trees[str(filename)] = node
        return node

    monkeypatch.setattr(dead_code_visitor, 'parse_abstract_syntax_tree', tree_recording_parse)

    visitor = DeadCodeVisitor(list(FILES), Args())
    visitor.visit_abstract_syntax_trees()

    unused_import_items = [
        item for item in visitor.get_unused_code_items() if item.type_ == 'import' and str(item.filename) == 'uses.py'
    ]
    assert unused_import_items

    content = FILES['uses.py']
    cached_tree = parsed_trees['uses.py']

    # When
    parts_from_cached_tree = get_unused_import_parts(content, unused_import_items, cached_tree=cached_tree)
    parts_from_fresh_parse = get_unused_import_parts(content, unused_import_items)

    # Then
    assert parts_from_cached_tree == parts_from_fresh_parse
