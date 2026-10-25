"""Agent 2: App Explorer & Stateful Navigation Crawler (Step 5.4).

Navigates target application routes, maintains explicit Playwright wait discipline,
triggers stateful prerequisite interactions (e.g. adding a product before visiting /cart),
captures ARIA accessibility snapshots via `page.aria_snapshot()`, parses ARIA trees,
and produces a disambiguated `SelectorMap`.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Sequence

from reqverify.agents.locator_builder import build_selectors_from_nodes
from reqverify.agents.snapshot_parser import parse_aria_snapshot
from reqverify.schemas.contracts import CoverageMatrix
from reqverify.schemas.selectors import PageSnapshot, SelectorMap

DEFAULT_TECHSTORE_ROUTES: tuple[str, ...] = (
    "/login",
    "/products",
    "/cart",
    "/checkout",
    "/admin/orders",
)


def capture_page_aria_snapshot(page: Any) -> str:
    """Capture the ARIA accessibility snapshot from a Playwright Page.

    Uses `page.aria_snapshot()` (Playwright >= 1.59) and falls back cleanly
    to `page.locator("body").aria_snapshot()` on Playwright 1.49-1.58.
    """
    if hasattr(page, "aria_snapshot") and callable(page.aria_snapshot):
        return page.aria_snapshot()
    return page.locator("body").aria_snapshot()


class AppExplorerAgent:
    """Agent 2 (App Explorer) — crawls SUT routes and builds a verified SelectorMap."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        credentials: Optional[Dict[str, str]] = None,
        coverage_matrix: Optional[CoverageMatrix] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credentials = credentials or {}
        self.coverage_matrix = coverage_matrix

    def explore_with_page(
        self,
        page: Any,
        routes: Sequence[str] = DEFAULT_TECHSTORE_ROUTES,
    ) -> SelectorMap:
        """Crawl target routes using an existing Playwright Page (or mock Page) and return SelectorMap."""
        pages_dict: Dict[str, PageSnapshot] = {}

        for raw_route in routes:
            route = raw_route if raw_route.startswith("/") else f"/{raw_route}"
            full_url = f"{self.base_url}{route}"

            page.goto(full_url)
            page.wait_for_load_state("domcontentloaded")

            raw_aria = capture_page_aria_snapshot(page)
            title = page.title() if hasattr(page, "title") and callable(page.title) else route

            parsed_nodes = parse_aria_snapshot(raw_aria)
            selectors = build_selectors_from_nodes(parsed_nodes, page_route=route)

            pages_dict[route] = PageSnapshot(
                route=route,
                title=title,
                raw_aria_tree=raw_aria,
                elements=selectors,
            )

            # After snapshotting /products on a live browser page, trigger stateful cart population
            # so subsequent /cart and /checkout snapshots expose their full interactive controls.
            if route == "/products":
                self._seed_cart_state_if_live(page)

        return SelectorMap(base_url=self.base_url, pages=pages_dict)

    def explore(
        self,
        routes: Sequence[str] = DEFAULT_TECHSTORE_ROUTES,
        headless: bool = True,
    ) -> SelectorMap:
        """Launch a headless Chromium browser, crawl all target routes, and return SelectorMap."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            try:
                return self.explore_with_page(page, routes=routes)
            finally:
                context.close()
                browser.close()

    def _seed_cart_state_if_live(self, page: Any) -> None:
        """Click the first 'Add ... to cart' button on /products when running against a live browser."""
        if not hasattr(page, "get_by_role") or not callable(page.get_by_role):
            return
        try:
            add_btn = page.get_by_role("button", name=re.compile(r"Add .* to cart", re.IGNORECASE)).first
            add_btn.click(timeout=2000)
            page.wait_for_load_state("domcontentloaded")
        except Exception:
            # Non-fatal if products are not yet hydrated or on mock page
            pass
