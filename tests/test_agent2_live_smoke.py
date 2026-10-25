"""Live smoke test for Agent 2 (App Explorer) against running TechStore (Step 5.5)."""

from __future__ import annotations

import urllib.request
import pytest

from reqverify.agents.explorer import AppExplorerAgent, DEFAULT_TECHSTORE_ROUTES

TECHSTORE_BASE_URL = "http://localhost:3000"


def _is_techstore_reachable(url: str = TECHSTORE_BASE_URL) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/login", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.live
def test_agent2_live_smoke_techstore():
    """Navigate all 5 TechStore routes with real Playwright, capture ARIA snapshots, and verify SelectorMap."""
    if not _is_techstore_reachable():
        pytest.skip(f"TechStore server not reachable at {TECHSTORE_BASE_URL}; skipping live smoke test.")

    agent = AppExplorerAgent(base_url=TECHSTORE_BASE_URL)
    selector_map = agent.explore(routes=DEFAULT_TECHSTORE_ROUTES, headless=True)

    assert set(selector_map.pages.keys()) == set(DEFAULT_TECHSTORE_ROUTES)
    for route, page_snap in selector_map.pages.items():
        assert page_snap.raw_aria_tree.strip(), f"Empty ARIA snapshot on {route}"
        assert len(page_snap.elements) > 0, f"No selectors extracted on {route}"
