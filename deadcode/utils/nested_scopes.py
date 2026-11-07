from typing import Any, Dict, List, Optional, Union

from deadcode.visitor.code_item import CodeItem


class NestedScope:
    """This data structure is used to track what types are defined in each scope.

    It allows to correctly detect the type which is being used.

    TODO: This data structure could also be used for tracking the usages of types, but
    there is an issue: the usage could be registered before the definition.
    A mock structure which would hold the usage should used to store count of usages
    until the type is defined.
    """

    def __init__(self) -> None:
        self._scopes: Dict[Union[str, CodeItem], Any] = {}

    def add(self, code_item: CodeItem) -> None:
        """Adds code item to nested scope."""

        if code_item.scope is None:
            return None

        scope_parts = code_item.scope.split('.')

        current_scope = self._scopes
        for scope_part in scope_parts:
            if scope_part not in current_scope:
                current_scope[scope_part] = {}  # Could use None if type cannot have scope
            current_scope = current_scope[scope_part]

        # > TODO: leaf should be replaced. Is it replaced with new code item?
        current_scope[code_item] = {}

    def get(self, name: str, scope: str) -> Optional[Union[CodeItem, str]]:
        """Returns CodeItem which matches scoped_name (e.g. package.class.method.variable)
        from the given scope or None if its not found."""

        # TODO: investigate how modules in subdirectories are being collected into scopes.
        #   Is filename scope flat: meaning it forgets parent directories?
        #   File scope should be created using working path as base dir.
        #   We would get name collisions for this structure:
        #       projects.models, billing.models, auth.models: only one root scope called models would be registered.

        # Create a stack of scopes begining from nearest and following with parent one
        scopes: List[Dict[Union[CodeItem, str], Dict[Any, Any]]] = []
        next_scope = self._scopes
        for scope_part in scope.split('.'):
            if scope_part not in next_scope:
                return None
            next_scope = next_scope[scope_part]
            scopes.insert(0, next_scope)

        # Search for definition with provided name in scopes
        for current_scope in scopes:
            if name in current_scope:
                current_scope_keys = list(current_scope.keys())
                return current_scope_keys[current_scope_keys.index(name)]

        return None

    def mark_as_used(self, name: str, scope: str) -> None:
        # >TODO: This method does not work, when methods are being invoked.
        # The scope is global, name is method name, but the instance and
        # class names are not being taken into account.

        # Solution: parsing of a method invocation should be handled differently.
        # More precicely. The parsing should be in the right order.

        # Next step to solve this issue:
        # > Investigate how usage statement is being handled and what can be done about it.
        # Write tests for Class and instance creations.

        # In this place I should get a list of names, which are being used in the invocation.

        # if name == "spam":
        #     breakpoint()

        code_item = self.get(name, scope)
        if isinstance(code_item, CodeItem):
            code_item.number_of_uses += 1
