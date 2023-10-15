from typing import Any, Dict, Optional, Union

from deadcode.visitor.code_item import CodeItem


class NestedScope(dict):  # type: ignore
    """This data structure is used to track what types are defined in each scope.

    It allows to correctly detect the type which is being used.

    TODO: This data structure could also be used for tracking the usages of types, but
    there is an issue: the usage could be registered before the definition.
    A mock structure which would hold the usage should used to store count of usages
    until the type is defined.
    """

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.nested_scope = {}

    def add_to_scope(self, code_item: CodeItem) -> None:
        """Adds code item to nested scope."""

        if code_item.scope is None:
            return None

        scope_parts = code_item.scope.split(".")

        current_scope = self
        for scope_part in scope_parts:
            if scope_part not in current_scope:
                current_scope[scope_part] = {}  # Could use None if type cannot have scope
            current_scope = current_scope[scope_part]

        # > TODO: leef should be replaced. Is it replaced with new code item?
        current_scope[code_item] = {}

    def get_scope(self, scope: str) -> Optional[Dict[Union[CodeItem, str], Optional[Dict[Union[CodeItem, str], Any]]]]:
        scope_parts = scope.split(".")

        current_scope = self
        for scope_part in scope_parts:
            if scope_part not in current_scope:
                return None
            current_scope = current_scope[scope_part]

        return current_scope
