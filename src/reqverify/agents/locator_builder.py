"""Playwright Python locator builder and strict-mode disambiguator (Agent 2, Step 5.3).

Converts ParsedAriaNode lists into executable Playwright Python locator strings
while preventing Playwright strict-mode collisions via:
1. Unique (role, accessible_name): page.get_by_role(role, name=name, exact=True)
2. Duplicate (role, accessible_name) with distinct named parent containers:
   page.get_by_role(parent_role).filter(has_text=parent_name).get_by_role(role, name=name, exact=True)
3. Indistinguishable duplicate (role, accessible_name):
   page.get_by_role(role, name=name, exact=True).nth(idx)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from reqverify.agents.snapshot_parser import ParsedAriaNode
from reqverify.schemas.selectors import UIElementSelector


class NoSelectorFoundError(LookupError):
    """Raised when a target UI element cannot be resolved in the captured SelectorMap.

    Maps directly to the deterministic `UNTESTED: no_selector_found` reason code
    in Agent 3 / Agent 4 (Invariant D11).
    """

    def __init__(self, role: str, name: str, page_route: str | None = None) -> None:
        route_info = f" on {page_route!r}" if page_route else ""
        super().__init__(
            f"no_selector_found: could not resolve element with role={role!r}, "
            f"name={name!r}{route_info}"
        )
        self.role = role
        self.name = name
        self.page_route = page_route


_INTERACTIVE_ROLES_WITHOUT_NAME = frozenset({
    "textbox",
    "searchbox",
    "spinbutton",
    "combobox",
    "checkbox",
    "radio",
    "switch",
    "slider",
})


def _escape_quotes(value: str) -> str:
    """Escape double quotes inside Python locator string literals."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().split())


def build_selectors_from_nodes(
    nodes: Sequence[ParsedAriaNode],
    page_route: str,
) -> list[UIElementSelector]:
    """Convert parsed ARIA nodes from a single page into strict-mode safe UIElementSelectors."""
    # Filter to actionable or named semantic elements (skip bare structural containers without names)
    candidate_nodes: list[ParsedAriaNode] = []
    for node in nodes:
        if node.role == "text" and not node.accessible_name:
            continue
        if not node.accessible_name and node.role not in _INTERACTIVE_ROLES_WITHOUT_NAME:
            continue
        candidate_nodes.append(node)

    # Group by (role, normalized accessible_name) to detect strict-mode collisions
    groups: dict[tuple[str, str], list[ParsedAriaNode]] = defaultdict(list)
    for node in candidate_nodes:
        key = (node.role.lower(), _normalize_key(node.accessible_name))
        groups[key].append(node)

    # Pre-compute locator recipe and nth_index per node object id
    node_recipes: dict[int, tuple[str, int | None]] = {}

    for (role, _norm_name), group in groups.items():
        if len(group) == 1:
            node = group[0]
            escaped_name = _escape_quotes(node.accessible_name)
            if node.accessible_name:
                recipe = f'page.get_by_role("{node.role}", name="{escaped_name}", exact=True)'
            else:
                recipe = f'page.get_by_role("{node.role}")'
            node_recipes[id(node)] = (recipe, None)
        else:
            # Check whether all nodes in the duplicate group have a valid parent_role
            # and mutually distinct non-empty parent_name values.
            parent_Move_valid = all(
                bool(n.parent_role and n.parent_name) for n in group
            )
            distinct_parents = (
                len({_normalize_key(n.parent_name or "") for n in group}) == len(group)
            )

            if parent_Move_valid and distinct_parents:
                for node in group:
                    escaped_parent = _escape_quotes(node.parent_name or "")
                    escaped_name = _escape_quotes(node.accessible_name)
                    if node.accessible_name:
                        recipe = (
                            f'page.get_by_role("{node.parent_role}")'
                            f'.filter(has_text="{escaped_parent}")'
                            f'.get_by_role("{node.role}", name="{escaped_name}", exact=True)'
                        )
                    else:
                        recipe = (
                            f'page.get_by_role("{node.parent_role}")'
                            f'.filter(has_text="{escaped_parent}")'
                            f'.get_by_role("{node.role}")'
                        )
                    node_recipes[id(node)] = (recipe, None)
            else:
                for idx, node in enumerate(group):
                    escaped_name = _escape_quotes(node.accessible_name)
                    if node.accessible_name:
                        recipe = (
                            f'page.get_by_role("{node.role}", name="{escaped_name}", exact=True)'
                            f".nth({idx})"
                        )
                    else:
                        recipe = f'page.get_by_role("{node.role}").nth({idx})'
                    node_recipes[id(node)] = (recipe, idx)

    selectors: list[UIElementSelector] = []
    route_slug = page_route.strip("/").replace("/", "-") or "root"
    for seq_idx, node in enumerate(candidate_nodes, start=1):
        recipe, nth_idx = node_recipes[id(node)]
        selectors.append(
            UIElementSelector(
                element_id=f"el-{route_slug}-{seq_idx:03d}",
                page_route=page_route,
                role=node.role,
                accessible_name=node.accessible_name,
                locator_recipe=recipe,
                is_interactive=node.is_interactive,
                parent_role=node.parent_role,
                parent_name=node.parent_name,
                nth_index=nth_idx,
                attributes=dict(node.attributes),
            )
        )

    return selectors


def resolve_selector(
    selectors: Sequence[UIElementSelector],
    role: str,
    name: str,
    *,
    parent_name: str | None = None,
    page_route: str | None = None,
) -> UIElementSelector:
    """Resolve a target (role, name) against a list of UIElementSelectors.

    Raises NoSelectorFoundError (containing 'no_selector_found') if no match exists.
    """
    target_role = role.strip().lower()
    target_name = _normalize_key(name)
    target_parent = _normalize_key(parent_name) if parent_name else None

    pool = [
        s
        for s in selectors
        if (page_route is None or s.page_route == page_route)
        and s.role.lower() == target_role
    ]

    # 1. Exact accessible_name match (with optional parent_name match)
    for sel in pool:
        if _normalize_key(sel.accessible_name) == target_name:
            if target_parent is None or _normalize_key(sel.parent_name or "") == target_parent:
                return sel

    # 2. Substring fallback on accessible_name
    for sel in pool:
        if target_name and target_name in _normalize_key(sel.accessible_name):
            if target_parent is None or target_parent in _normalize_key(sel.parent_name or ""):
                return sel

    raise NoSelectorFoundError(role=role, name=name, page_route=page_route)
