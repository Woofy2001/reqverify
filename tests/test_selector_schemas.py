"""Tests verifying Pydantic v2 schemas for UIElementSelector, PageSnapshot, and SelectorMap (Phase 05 Step 5.1)."""

from __future__ import annotations

import pytest


def test_selector_schemas_importable():
    """Verify selector contracts are exportable from reqverify.schemas.selectors."""
    from reqverify.schemas.selectors import (
        UIElementSelector,
        PageSnapshot,
        SelectorMap,
    )
    assert UIElementSelector is not None
    assert PageSnapshot is not None
    assert SelectorMap is not None


def test_selector_schema_serialization():
    """Verify UIElementSelector serializes and deserializes with full attributes and backwards compatibility."""
    from reqverify.schemas.selectors import UIElementSelector

    # Instantiate using Phase 05 field names
    sel1 = UIElementSelector(
        element_id="el_btn_add_1",
        role="button",
        accessible_name="Add to cart",
        locator_recipe='page.get_by_role("button", name="Add to cart", exact=True)',
        page_route="/products",
        is_interactive=True,
        parent_role="listitem",
        parent_name="Quantum Pro Laptop",
        nth_index=0,
        attributes={"disabled": False},
    )
    assert sel1.role == "button"
    assert sel1.accessible_name == "Add to cart"
    assert sel1.locator_recipe == 'page.get_by_role("button", name="Add to cart", exact=True)'
    assert sel1.locator_code == sel1.locator_recipe
    assert sel1.page_route == "/products"
    assert sel1.page_url == "/products"

    # Round-trip JSON serialization
    json_data = sel1.model_dump_json()
    restored = UIElementSelector.model_validate_json(json_data)
    assert restored.element_id == "el_btn_add_1"
    assert restored.parent_name == "Quantum Pro Laptop"

    # Instantiate using Guide §7.1 contract field names (locator_code, page_url)
    sel2 = UIElementSelector(
        element_id="el_btn_signin",
        role="button",
        accessible_name="Sign in",
        locator_code='page.get_by_role("button", name="Sign in", exact=True)',
        page_url="http://localhost:3000/login",
    )
    assert sel2.locator_code == 'page.get_by_role("button", name="Sign in", exact=True)'
    assert sel2.locator_recipe == sel2.locator_code
    assert sel2.page_url == "http://localhost:3000/login"
    assert sel2.page_route == "http://localhost:3000/login"


def test_page_snapshot_and_selector_map_lookup():
    """Verify PageSnapshot and SelectorMap store and query selectors by role and normalized name."""
    from reqverify.schemas.selectors import (
        UIElementSelector,
        PageSnapshot,
        SelectorMap,
    )

    el_email = UIElementSelector(
        element_id="login_email",
        role="textbox",
        accessible_name="Email address",
        locator_recipe='page.get_by_role("textbox", name="Email address", exact=True)',
        page_route="/login",
    )
    el_signin = UIElementSelector(
        element_id="login_btn",
        role="button",
        accessible_name="Sign in",
        locator_recipe='page.get_by_role("button", name="Sign in", exact=True)',
        page_route="/login",
    )
    el_apply = UIElementSelector(
        element_id="cart_apply",
        role="button",
        accessible_name="Apply Discount",
        locator_recipe='page.get_by_role("button", name="Apply Discount", exact=True)',
        page_route="/cart",
    )

    login_snap = PageSnapshot(
        route="/login",
        title="Sign in - TechStore",
        raw_aria_tree='- heading "Sign in"\n- textbox "Email address"\n- button "Sign in"',
        elements=[el_email, el_signin],
    )
    cart_snap = PageSnapshot(
        route="/cart",
        title="Cart - TechStore",
        raw_aria_tree='- heading "Your Shopping Cart"\n- button "Apply Discount"',
        elements=[el_apply],
    )

    smap = SelectorMap(
        base_url="http://localhost:3000",
        pages={"/login": login_snap, "/cart": cart_snap},
    )

    # Lookup across all pages (case-insensitive & whitespace normalized)
    matches = smap.find_by_role_and_name("button", "  sign   in ")
    assert len(matches) == 1
    assert matches[0].element_id == "login_btn"

    # Lookup scoped to specific route
    cart_buttons = smap.find_by_role_and_name("button", "Apply Discount", route="/cart")
    assert len(cart_buttons) == 1
    assert cart_buttons[0].element_id == "cart_apply"

    # Route miss returns empty list
    wrong_route = smap.find_by_role_and_name("button", "Apply Discount", route="/login")
    assert len(wrong_route) == 0

    # Total elements across map
    all_els = smap.get_all_elements()
    assert len(all_els) == 3
