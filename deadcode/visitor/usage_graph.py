"""Definition-anchored usage graph and its single reachability pass.

The graph is pure: it takes the collected items, the recorded bare-usage
sources and the plain anchors, and returns the set of live ``(module
basename, name)`` item keys. A usage source ``(module u, name n)`` is live
when it is a root usage (module-level code or an ignore-protected
definition) or when any definition owning it is live; an item is live when
its name is a plain anchor or when a live usage source references it.

Every suppression rule of the legacy per-item check
(``DeadCodeVisitor.is_name_used_in_module``) is reproduced exactly by the
per-usage-source reference predicate below, so behaviour is unchanged
whenever all owners are live; only usages owned exclusively by unused
definitions lose their keep-alive power, which is what makes cascades
detectable in a single run.
"""

from __future__ import annotations

from collections import deque
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Container, Mapping, Sequence

    from deadcode.visitor.code_item import CodeItem


def compute_live_item_keys(
    items: Sequence[CodeItem],
    used_names: Container[str],
    root_usage_sources: set[tuple[str, str]],
    usage_owners: Mapping[tuple[str, str], set[int]],
    owner_keys: Mapping[int, tuple[str, str]],
    resolve_bare_usage: Callable[[str, str], set[tuple[str, str]] | None],
    wildcard_imports: Mapping[str, set[str]],
    module_exports: Mapping[str, set[str]],
    explicit_imports: Mapping[str, set[str]],
) -> set[tuple[str, str]]:
    """Return the set of live ``(module basename, name)`` item keys.

    ``items`` are the collected definitions; ``used_names`` are the plain
    anchors which keep every same-named item alive; ``root_usage_sources``
    are the bare-usage sources not owned by any definition; ``usage_owners``
    maps a usage source to the identity tokens of the definitions owning it;
    ``owner_keys`` maps an owner token back to its item key;
    ``resolve_bare_usage`` resolves a bare usage to its binding targets (or
    ``None`` when the usage is unresolvable or ambiguous).
    """
    items_by_name: dict[str, set[tuple[str, str]]] = {}
    for item in items:
        module = os.path.splitext(os.path.basename(str(item.filename)))[0]
        items_by_name.setdefault(item.name, set()).add((module, item.name))

    # Invert the ownership registry: which usage sources does an item key own?
    sources_of_key: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for source, owners in usage_owners.items():
        for owner in owners:
            if (key := owner_keys.get(owner)) is not None:
                sources_of_key.setdefault(key, set()).add(source)

    reference_targets: dict[tuple[str, str], set[tuple[str, str]]] = {}

    def references(source: tuple[str, str]) -> set[tuple[str, str]]:
        """Every item key that a bare usage of `source` could bind to.

        Exact decomposition of the `is_name_used_in_module` checks: the bare
        usage always satisfies its own module (current check 2); a module
        wildcard-imported by the using module is referenced through the
        `__all__` export rules (current check 3), and only when it is not
        wildcard-imported is the usage resolved to its binding targets, with
        unresolvable and ambiguous usages conservatively referenced (current
        check 4).
        """
        if source not in reference_targets:
            using_module, name = source
            targets = {(using_module, name)}
            wildcard_modules = wildcard_imports.get(using_module, set())
            resolved = resolve_bare_usage(name, using_module)
            exports_known = explicit_imports.get(using_module, set())
            for key in items_by_name.get(name, set()):
                module = key[0]
                if module == using_module:
                    continue
                if module in wildcard_modules:
                    exports = module_exports.get(module)
                    if exports is None or name in exports or name in exports_known:
                        targets.add(key)
                elif resolved is None or key in resolved:
                    targets.add(key)
            reference_targets[source] = targets
        return reference_targets[source]

    live_keys: set[tuple[str, str]] = set()
    live_sources: set[tuple[str, str]] = set()
    queue: deque[tuple[bool, tuple[str, str]]] = deque()

    for source in root_usage_sources:
        live_sources.add(source)
        queue.append((False, source))

    for item in items:
        if item.name in used_names:
            key = owner_keys[id(item)]
            if key not in live_keys:
                live_keys.add(key)
                queue.append((True, key))

    while queue:
        is_key, entry = queue.popleft()
        if is_key:
            for source in sources_of_key.get(entry, set()):
                if source not in live_sources:
                    live_sources.add(source)
                    queue.append((False, source))
        else:
            for target in references(entry):
                if target not in live_keys:
                    live_keys.add(target)
                    queue.append((True, target))

    return live_keys
