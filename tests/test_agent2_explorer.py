"""Offline unit tests for Agent 2 AppExplorerAgent and navigation crawler (Step 5.4)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict
import pytest

from reqverify.schemas.selectors import SelectorMap

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "snapshots"

ROUTE_TO_FIXTURE: Dict[str, str] = {
    "/login": "techstore_login.yaml",
    "/products": "techstore_products.yaml",
    "/cart": "techstore_cart.yaml",
    "/checkout": "techstore_checkout.yaml",
    "/admin/orders": "techstore_admin.yaml",
}

ROUTE_TO_TITLE: Dict[str, str] = {
    "/login": "Sign in - TechStore",
    "/products": "Products - TechStore",
    "/cart": "Shopping Cart - TechStore",
    "/checkout": "Checkout - TechStore",
    "/admin/orders": "Admin Orders - TechStore",
}


class FakePlaywrightPage:
    """Deterministic mock of a Playwright Page for offline Agent 2 crawler testing."""

    def __init__(self, base_url: str = "http://localhost:3000") -> None:
        self.base_url = base_url.rstrip("/")
        self.url = f"{self.base_url}/login"
        self.visited_urls: list[str] = []
        self.wait_states: list[str] = []
        self.aria_snapshot_calls: int = 0

    def goto(self, url: str, **kwargs) -> None:
        self.url = url
        self.visited_urls.append(url)

    def wait_for_load_state(self, state: str = "domcontentloaded", **kwargs) -> None:
        self.wait_states.append(state)

    def title(self) -> str:
        route = self._current_route()
        return ROUTE_TO_TITLE.get(route, "TechStore")

    def aria_snapshot(self) -> str:
        self.aria_snapshot_calls += 1
        route = self._current_route()
        fixture_name = ROUTE_TO_FIXTURE.get(route, "techstore_products.yaml")
        return (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")

    def _current_route(self) -> str:
        if self.url.startswith(self.base_url):
            route = self.url[len(self.base_url) :]
            return route if route.startswith("/") else f"/{route}"
        return "/login"


def test_explorer_importable():
    """Verify AppExplorerAgent and helper functions are importable."""
    from reqverify.agents.explorer import (
        AppExplorerAgent,
        DEFAULT_TECHSTORE_ROUTES,
        capture_page_aria_snapshot,
    )

    assert callable(AppExplorerAgent)
    assert callable(capture_page_aria_snapshot)
    assert len(DEFAULT_TECHSTORE_ROUTES) == 5


def test_explorer_crawls_five_pages():
    """Verify AppExplorerAgent visits all 5 TechStore routes and records snapshots."""
    from reqverify.agents.explorer import AppExplorerAgent

    fake_page = FakePlaywrightPage(base_url="http://localhost:3000")
    agent = AppExplorerAgent(base_url="http://localhost:3000")

    selector_map = agent.explore_with_page(fake_page)

    assert isinstance(selector_map, SelectorMap)
    assert set(selector_map.pages.keys()) == {
        "/login",
        "/products",
        "/cart",
        "/checkout",
        "/admin/orders",
    }
    assert len(fake_page.visited_urls) == 5
    assert fake_page.aria_snapshot_calls == 5


def test_explorer_records_selector_map():
    """Verify returned SelectorMap contains disambiguated selectors across all 5 pages."""
    from reqverify.agents.explorer import AppExplorerAgent

    fake_page = FakePlaywrightPage(base_url="http://localhost:3000")
    agent = AppExplorerAgent(base_url="http://localhost:3000")
    selector_map = agent.explore_with_page(fake_page)

    # Login page checks
    login_btns = selector_map.find_by_role_and_name("button", "Sign in", route="/login")
    assert len(login_btns) == 1
    assert login_btns[0].locator_recipe == 'page.get_by_role("button", name="Sign in", exact=True)'

    # Products page checks
    add_btns = selector_map.find_by_role_and_name(
        "button", "Add Quantum Pro Laptop to cart", route="/products"
    )
    assert len(add_btns) == 1
    assert add_btns[0].parent_name == "Quantum Pro Laptop"

    # Checkout page checks
    continue_btns = selector_map.find_by_role_and_name(
        "button", "Continue to Payment", route="/checkout"
    )
    assert len(continue_btns) == 1

    # Admin page checks
    ship_btns = selector_map.find_by_role_and_name(
        "button", "Mark Shipped for order ORD-1001", route="/admin/orders"
    )
    assert len(ship_btns) == 1


def test_explorer_explicit_wait_discipline():
    """Verify explorer uses explicit load-state waits and never calls time.sleep()."""
    import reqverify.agents.explorer as explorer_mod
    from reqverify.agents.explorer import AppExplorerAgent

    fake_page = FakePlaywrightPage(base_url="http://localhost:3000")
    agent = AppExplorerAgent(base_url="http://localhost:3000")
    agent.explore_with_page(fake_page)

    # Every visited page must have triggered an explicit wait_for_load_state call
    assert len(fake_page.wait_states) >= 5
    assert all(state in {"domcontentloaded", "networkidle", "load"} for state in fake_page.wait_states)

    # AST audit of explorer.py: ensure time.sleep is never called
    source = Path(explorer_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "sleep":
                pytest.fail("Forbidden time.sleep() call found in explorer.py")


def test_capture_page_aria_snapshot_body_fallback():
    """Verify capture_page_aria_snapshot falls back to page.locator('body').aria_snapshot()."""
    from reqverify.agents.explorer import capture_page_aria_snapshot

    class LegacyPage:
        def locator(self, selector: str):
            assert selector == "body"

            class _BodyLoc:
                def aria_snapshot(self_inner) -> str:
                    return '- heading "Fallback Snapshot" [level=1]'

            return _BodyLoc()

    snap = capture_page_aria_snapshot(LegacyPage())
    assert 'heading "Fallback Snapshot"' in snap
