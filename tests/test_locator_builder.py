"""Tests verifying the Playwright locator builder and strict-mode disambiguator (Step 5.3)."""

from __future__ import annotations

import pytest
from reqverify.agents.snapshot_parser import parse_aria_snapshot


def test_locator_builder_importable():
    """Verify locator_builder exports build_selectors_from_nodes, resolve_selector, and NoSelectorFoundError."""
    from reqverify.agents.locator_builder import (
        build_selectors_from_nodes,
        resolve_selector,
        NoSelectorFoundError,
    )
    assert callable(build_selectors_from_nodes)
    assert callable(resolve_selector)
    assert issubclass(NoSelectorFoundError, Exception)


def test_single_unique_element_locator():
    """Unique (role, name) produces clean page.get_by_role(..., exact=True)."""
    from reqverify.agents.locator_builder import build_selectors_from_nodes

    raw_tree = """
- heading "Sign in to TechStore" [level=1]
- textbox "Email address"
- button "Sign in"
"""
    nodes = parse_aria_snapshot(raw_tree)
    selectors = build_selectors_from_nodes(nodes, page_route="/login")

    by_name = {s.accessible_name: s for s in selectors}
    assert "Sign in" in by_name
    btn = by_name["Sign in"]
    assert btn.locator_recipe == 'page.get_by_role("button", name="Sign in", exact=True)'
    assert btn.nth_index is None


def test_duplicate_elements_parent_scoping():
    """Duplicate (role, name) inside distinct named parent containers disambiguates via .filter(has_text=...)."""
    from reqverify.agents.locator_builder import build_selectors_from_nodes

    raw_tree = """
- list:
  - listitem:
    - heading "Quantum Pro Laptop" [level=3]
    - button "Add to cart"
  - listitem:
    - heading "Wireless Mouse" [level=3]
    - button "Add to cart"
"""
    nodes = parse_aria_snapshot(raw_tree)
    selectors = build_selectors_from_nodes(nodes, page_route="/products")

    buttons = [s for s in selectors if s.role == "button" and s.accessible_name == "Add to cart"]
    assert len(buttons) == 2

    assert buttons[0].locator_recipe == (
        'page.get_by_role("listitem").filter(has_text="Quantum Pro Laptop")'
        '.get_by_role("button", name="Add to cart", exact=True)'
    )
    assert buttons[1].locator_recipe == (
        'page.get_by_role("listitem").filter(has_text="Wireless Mouse")'
        '.get_by_role("button", name="Add to cart", exact=True)'
    )


def test_duplicate_elements_nth_fallback():
    """Indistinguishable duplicate (role, name) without distinct parent names falls back to .nth(i)."""
    from reqverify.agents.locator_builder import build_selectors_from_nodes

    raw_tree = """
- button "Remove item"
- button "Remove item"
"""
    nodes = parse_aria_snapshot(raw_tree)
    selectors = build_selectors_from_nodes(nodes, page_route="/cart")

    assert len(selectors) == 2
    assert selectors[0].locator_recipe == 'page.get_by_role("button", name="Remove item", exact=True).nth(0)'
    assert selectors[0].nth_index == 0
    assert selectors[1].locator_recipe == 'page.get_by_role("button", name="Remove item", exact=True).nth(1)'
    assert selectors[1].nth_index == 1


def test_no_selector_found_sentinel():
    """Verify resolve_selector raises NoSelectorFoundError when target element does not exist."""
    from reqverify.agents.locator_builder import (
        build_selectors_from_nodes,
        resolve_selector,
        NoSelectorFoundError,
    )

    raw_tree = '- button "Sign in"\n- textbox "Email address"'
    nodes = parse_aria_snapshot(raw_tree)
    selectors = build_selectors_from_nodes(nodes, page_route="/login")

    # Valid lookup succeeds
    found = resolve_selector(selectors, role="button", name="Sign in")
    assert found.accessible_name == "Sign in"

    # Missing element raises NoSelectorFoundError (maps to UNTESTED: no_selector_found)
    with pytest.raises(NoSelectorFoundError) as exc_info:
        resolve_selector(selectors, role="button", name="Export CSV")
    assert "no_selector_found" in str(exc_info.value)
