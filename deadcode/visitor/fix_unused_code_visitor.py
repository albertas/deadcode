"""
Define FixNodeVisitor, which finds additional code parts to removed for unused code items
by visiting the code nodes once again.

#####################################################################################
# Is this visiting really needed? Would it be possible to avoid analying it again?
#
# Question: is single file scope enough for he analysis?
#   Only imports are impacted?
#
#   Only Additional usages mgiht appear.
#
#   Local scope and global scope difference.
#
#
# What is the answer? 
#   I should avoid second reanalysis, but I should have a garanttee, that those code items are unused before finding additional code parts to remove.
#   What are the different cases?
#
#   Partially removable code item types:
#
#   Variable types:
#       Local scope - whole file or scope has to be analysed.
#           cotext manager.
#       Import - whole file has to be analysed.
#       Global scope: unparse has to be analysed.
#           variables, classes, methods - those do not support partial removal.
#
#
# Fix nodes only adjusts patially removal nodes.
#   It does not remove completely, which was in that case test.
# 
# This means that the issue is somewhere else.
#
#######################################################################################

"""

import ast
from difflib import SequenceMatcher
from itertools import chain
import os
import re
import string
import sys
from logging import getLogger

from pathlib import Path
from collections import defaultdict

from typing import Callable, Dict, List, Optional, Set, TextIO, Union, Iterable, Any, Tuple
from deadcode.constants import UnusedCodeType
from deadcode.data_types import Args, Part, Filename
from deadcode.visitor.code_item import CodeItem
from deadcode.visitor.utils import LoggingList, LoggingSet
from deadcode.visitor import utils
from deadcode.actions.parse_abstract_syntax_tree import parse_abstract_syntax_tree
from deadcode.utils.nested_scopes import NestedScope

from deadcode.visitor.find_unused_code_visitor import FindUnusedCodeVisitor
from deadcode.visitor import noqa
from deadcode.utils.print_ast import print_ast as show  # noqa: F401
from deadcode.utils.remove_from_list import remove_from_list
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


class FixUnusedCodeVisitor(ast.NodeVisitor):
    """Adjusts code, which has to be removed.
    
    Example: if import becomes empty after removal - the whole statement has to be removed,
    not only the imported names.
    """

    def __init__(self, find_unused_code_visitor: FindUnusedCodeVisitor) -> None:
        self.find_unused_code_visitor = find_unused_code_visitor
        self.args = self.find_unused_code_visitor.args

        self.filenames = self.find_unused_code_visitor.filenames

        # TODO: CodePart has to contain filename, because these code parts are for different files.
        self.additional_code_parts_to_remove: dict[Filename, list[Part]] = defaultdict(list)

    def visit_abstract_syntax_trees(self) -> dict[Filename, list[Part]]:
        # TODO: rename this method to reflect that it is used to find unused code Items in all the files.

        for file_path in self.filenames:
            with open(file_path) as f:
                filename = os.path.basename(file_path)
                module_name = os.path.splitext(filename)[0]
                self.scope_parts = [module_name]

                file_content = f.read()
                if file_content.strip() or (filename.startswith('__') and filename.endswith('__.py')):
                    self.noqa_lines = noqa.parse_noqa(file_content)

                    node = parse_abstract_syntax_tree(file_content, args=self.args, filename=file_path)
                    self.filename = Path(file_path)

                    # TODO: apply fixing step, only when visiting of all files is finished.

                    # The only bug detected was that current solutions tries to apply changes, when not all files were analysed yet.
                    #
                    # Still strictly separate detection and fixing.
                    # Fixing should be done by reading a file once again, parsing its AST, making inline modification changes as anticipated now.
                    #
                    # Comparison for exact code items will be adjused in the future.


                    # Lets create AST only one time?
                        # Altering AST might be hard: you cannot just modify it.

                    # This means that every single modification will have to be made using AST? I dont want to do it.


                    # All file contents and ASTs will be cached.
                    # Or shoudl I read the files two times and recreate the ATSs?
                        # This way deadcode could handle unlimited number of files.


                    # They will be walked over and compared. 

                    # File content used to be discarded for efficiency.
                    # Should the files be read once again? Are they read two times now?
                    # Lets cache all the file in memory: for efficiency.
                    # I can modifie
                    self.file_content_lines = file_content.splitlines(True)


                    # TODO: this visiting has to be run only after all files were visited already.
                    # Ideally it should a completely new visitor to separate responsibilities.
                    # Parsing should look the same.
                    # Lets do it: just split the responsibilities.

                    # Adjust AST and parts to remove in code items
                    # Fixing can only happend after visiting all the files.
                    self.visit(node)

        return self.additional_code_parts_to_remove

    def get_original_code_lines(self, node: ast.AST) -> List[str]:
        lines = self.file_content_lines[node.lineno -1:node.end_lineno]
        lines[0] = lines[0][node.col_offset:]
        lines[-1] = lines[-1][:node.end_col_offset + 1]
        return lines

    def get_cleaned_up_code(self, node: ast.AST) -> str:
        """Converts cleaned up node back into code by unparsing fixed node to code."""
        return ast.unparse(node)

    def convert_1d_part_to_2d(self, from_char: int, to_char: int, line_lengths: List[int], first_line: int, first_col: int) -> Tuple[int, int, int, int]:
        from_line = None
        from_col = None
        to_line = None
        to_col = None
        char_count = 0
        for current_line, line_length in enumerate(line_lengths):
            if from_line is None and from_char < (char_count + line_length):  # Is it <= or <?
                # TODO: is it 1-indexed line or multiline?
                from_line = current_line + first_line
                from_col = from_char - char_count + first_col

            if to_line is None and to_char <= (char_count + line_length):  # Is it <= or <?
                to_line = current_line + first_line
                to_col = to_char - char_count + first_col

            char_count += line_length

        if from_line is None or from_col is None or to_line is None or to_col is None:
            raise ValueError("Conversion from 1D to 2D code part failed")

        code_part = Part(from_line, to_line, from_col, to_col)
        return code_part

    def get_chars_to_remove(self, original_code_lines, fixed_code, first_line, first_col) -> List[Tuple[int, int, int, int]]:
        """Return a list code parts to be removed from the original code to get the first one.
        So that this could be applied with Code part removal algorithm.
        """
        # TODO: should receive line and col, where the original code started.

        original_code_line_lengths = [len(line) for line in original_code_lines]
        # NOTE: remove trailing newline because fixed_code does not end in new line.
        original_code = ''.join(original_code_lines).rstrip('\r\n')

        # TODO: should some kind of Junk characters be used?
        # Find a diff ignoring white spaces and brackets:
        # Find character positions, which have to be removed: and create a CodeItem with those parts.
        #
        # TODO: This strategy could be applied for all the partially removable code items.
        #   Without reformatting the subnodes (code block)

        # TODO: GOAL: make this method work with multilines.
        # TODO: make this method return coordinates of original file.

        s = SequenceMatcher(None, original_code, fixed_code)

        code_parts_to_remove = []
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            print(f'{tag}   a[{i1}:{i2}] --> b[{j1}:{j2}] {original_code[i1:i2]} --> {fixed_code[j1:j2]}')
            if tag == "delete":
                segment = original_code[i1:i2]
                if segment.strip() == "" and (i1 == 0 or original_code[i1 - 1] == "\n"):
                    continue  # ast.unparse re-indented the body; surplus indent is not a real delete
                code_part_to_remove = self.convert_1d_part_to_2d(i1, i2, original_code_line_lengths, first_line, first_col)
                code_parts_to_remove.append(code_part_to_remove)

        # print("Original:\n", original_code)
        # print("Fixed:\n", fixed_code)
        # print("Part to remove:")
        # for from_part, to_part in code_parts_to_remove:
        #     print(original_code[from_part:to_part], end="")
        # print()

        return code_parts_to_remove

    def add_code_adjustments_for_cleaned_up_code_items(self, node) -> str:
        original_code_lines = self.get_original_code_lines(node)
        fixed_code = self.get_cleaned_up_code(node)

        # TODO: Fixing can only happend after visiting all the files.

        # TODO: >>>> Should provide initial line and column so that result would be absolute.
        code_parts_to_remove = self.get_chars_to_remove(original_code_lines, fixed_code, node.lineno, node.col_offset)  # TODO: test with multiline code blocks
        
        self.additional_code_parts_to_remove[str(self.filename)].extend(code_parts_to_remove)

        # Lets refactor step by step.
        # This method could provide a modified file content.
        #   # What can I say?


        # This method should provide a modified file content, which will be written on top.


        # It changer the flow
        #
        # I have to think this through before making adjustments:
        #
        # This method is not available.
        #
        #
        #
        #


        # but in order to update the content I have to: 
            # > What can I say?


        # >>>
        # Why cant I just modify this file content and write it into file?
        #   I could replace code chunks just like that.



        # That code part removal logic could be thrown out completely?



        ## TODO: find a diff of the code:
        # TODO: create additional CodeItems, which cleans up remaining characters, not only names.

        # TODO: CLI option might be added to preserve function calls, when its result is not needed.

    def remove_node(self, node: ast.AST) -> None:
        self.additional_code_parts_to_remove[str(self.filename)].append(
            Part(node.lineno, node.end_lineno, node.col_offset, node.end_col_offset)
        )

    def visit_With(self, node: ast.ClassDef) -> None:
        # Remove optional_var node from AST if optional_var name is in unused_names
        for item in node.items:
            if isinstance(item.optional_vars, ast.AST):
                # How to find unused names? Why f is not in the unused_names?
                if item.optional_vars.id not in self.find_unused_code_visitor.used_names:
                    item.optional_vars = None

        self.add_code_adjustments_for_cleaned_up_code_items(node)

        #     # self.remove_node(item.optional_vars)
        #     ## TODO: add support to multiple with variables
        #     # elif isinstance(item.optional_vars, list):
        #     #     for optional_var in item.optional_vars:
        #     #         if optional_var not in self.find_unused_code_visitor.used_names:
        #     #             self.remove_node(optional_var)



    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # TODO: Remove variables, methods, classes from nested elements.
        # TODO: add pass statement if needed.

        # This is how the nodes are iterated:
        # ast.iter_fields(node)
        # for node in node.body:


        names = [body_node.name for body_node in node.body if getattr(body_node, 'name', None)]
        names_to_remove = [name for name in names if name not in self.find_unused_code_visitor.used_names]  # Make sure that unused_names is a set

        def should_remove(node: ast.AST) -> bool:
            return getattr(node, 'name', None) in names_to_remove
        remove_from_list(node.body, should_remove)

        # Add pass to the body if body is empty
        if not node.body:
            # TODO: Lets try creating an empty node with code to insert.
            pass_to_add = Part(
                line_start=node.lineno+1,
                col_start=node.col_offset+4,
                line_end=node.lineno+1,
                col_end=node.col_offset+4,
                insert_code='pass\n',
                insert_code_if_character_is_not_removed=(node.lineno, node.col_offset),
                #
                # TODO: >>>  It is not possible to track, when pass has to be removed, or not. New design improvement has to be made.

                # One solution is to remove inserted code when merging parts: if a symbol is removed after which the code has to be inserted, then do not insert the code.
                # The better approach would be to track expressions: if expression has to be removed - then remove it completely with code inserted as well.

                #
                # Pass has to be assigned to a particular character, if it gets removed - pass should not be rendered.
            )

            self.additional_code_parts_to_remove[str(self.filename)].append(pass_to_add)


    def visit_ImportFrom(self, node: ast.Import) -> None:
        if node.module != '__future__':
            self.visit_Import(node)

    # TODO: investigate if usage of an import with aliased name is marked as used properly.
    #       when item is imported, it should not be marked as used: these code items should be linked instead.
    def visit_Import(self, node: ast.Import) -> None:
        # Adjust node by removing unused code items
        names = [e.asname or e.name.partition('.')[0] for e in node.names[::-1]]
        names_to_remove = [name for name in names if name not in self.find_unused_code_visitor.used_names]  # Make sure that unused_names is a set

        # No names are being imported - whole import expression should be removed
        if len(names) == len(names_to_remove):
            self.remove_node(node)
            return

        def should_remove(elem: Any) -> bool:
            return (elem.asname or elem.name.partition('.')[0]) in names_to_remove
        remove_from_list(node.names, should_remove)

        self.add_code_adjustments_for_cleaned_up_code_items(node)
        # Get code chunk.  I dont have the file content, do I? AST was constructed from something.

        # >>>>
        # I want to have a comparison with Used code chunk of this expression.
        # And unuse: can reconstruct code from updated AST.  No need to have CodeItems.
        # How to know which CodeItems are unused.

        # So this AST is actually really cool.


        # We have adjusted the AST node.
        # Now we have to adjust CodeItem parts, which have to be removed.

        ####################
        ## What can I do? ##
        ####################
        # I could ammend the AST nodes with the links of unused code items in this expression.
        #   How to deal with children? Only direct unused code whildren would be saved.
        # 
        #   Lets do it: on save aliases method save.


        # This algorithmic behavior has to be described somewhere.


        # Thats the point these have to be List and Set items.
        #
        # Find CodeItems that are related to this node expression.
        # Are those unused names CodeItems?


        # Should I just create additional CodeItem for the expression it self?


        # TODO: can we also have CodeItem, which has to be added? Like pass?



        ## TODO: Working MVP example, should make a utility out of it.
        # nodes.names = [s,g,h,j]
        # print([(e.name, e.alias) for e in node.names])
        # print("Unused names", unused_names)
        # node = nodes
        # names_count = len(node.names)
        # for i, (name, alias) in enumerate((e.name, e.alias) for e in node.names[::-1]):
        #     if (name and name in unused_names) or (alias and alias in unused_names):
        #         print("removing", names_count-i-1)
        #         node.names.pop(names_count-i-1)
        # print([(e.name, e.alias) for e in node.names])


    # def visit_ImportFrom_after_visiting_child_nodes(self, node: ast.Import) -> None:
    #     # TODO: there is no way to know if code items were used or not at this point.
    #     # AST should be walked two times: first to detect which code items are unused.
    #     # Second is to adjust unused code item fixing (AST has to be modified and reconstructed back).
    #
    #     # > How to get code items, which were detected for this specific node?
    #
    #     # Remove unused code items
    #     # Check if import statement is valid
    #     # Fix import statement if needed (clean it)
    #     # Mark correct parts to be removed after fixing.

    def visit_Assign(self, node: ast.Assign) -> None:
        # node.targets[0].id
        names = [getattr(target, 'id', None) for target in node.targets]
        names_to_remove = [name for name in names if name and name not in self.find_unused_code_visitor.used_names]

        # self.should_ignore_new_definitions

        # Nothing is assigned to the variables - remove whole assignment expression.
        if len(names) == len(names_to_remove):
            self.remove_node(node)
            return

        # TODO: remove noqa comment if it leaves hanging after code removal.

        # TODO: elements from value expression should also be removed.
        # Find indexes of names and adjust node.value accordingly.

        def should_remove(elem: Any) -> bool:
            return getattr(elem, 'id', None) in names_to_remove
        remove_from_list(node.targets, should_remove)

        self.add_code_adjustments_for_cleaned_up_code_items(node)

    def visit(self, node: ast.AST) -> None:
        node_name = getattr(node, 'name', None)

        # > TODO: Expr scope has to be updated after visiting nested nodes.
        # Do I have to merge custom visits with visit method in order to achieve this?
        #
        # I should write a unit test with only an exrepssion and check which methods are being called.
        # I should only handled that single expression handling properly.


        # Visit node before visiting all its children
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, None)
        
        if visitor:
            visitor(node)

        if node:
            for _, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)
