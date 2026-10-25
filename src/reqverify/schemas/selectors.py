"""Selector and ARIA snapshot data contracts for Agent 2 (App Explorer)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


def _normalize_str(s: str) -> str:
    return " ".join(s.lower().split())


class UIElementSelector(BaseModel):
    """Semantic UI element selector mapped from Playwright ARIA snapshot tree."""

    element_id: str
    role: str
    accessible_name: str
    locator_recipe: str = ""
    locator_code: str = ""
    page_route: str = ""
    page_url: str = ""
    is_interactive: bool = True
    parent_role: Optional[str] = None
    parent_name: Optional[str] = None
    nth_index: Optional[int] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sync_compatible_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync locator_recipe <-> locator_code
            recipe = data.get("locator_recipe") or data.get("locator_code") or ""
            data["locator_recipe"] = recipe
            data["locator_code"] = recipe

            # Sync page_route <-> page_url
            route = data.get("page_route") or data.get("page_url") or ""
            data["page_route"] = route
            data["page_url"] = route
        return data


class PageSnapshot(BaseModel):
    """Captured ARIA accessibility snapshot and extracted selectors for a single page state."""

    route: str
    title: str
    raw_aria_tree: str
    elements: List[UIElementSelector] = Field(default_factory=list)


class SelectorMap(BaseModel):
    """Global repository of page snapshots and disambiguated selectors across the SUT."""

    base_url: str
    pages: Dict[str, PageSnapshot] = Field(default_factory=dict)

    def find_by_role_and_name(
        self,
        role: str,
        name: str,
        route: Optional[str] = None,
    ) -> List[UIElementSelector]:
        """Find selectors matching role and normalized accessible name."""
        norm_role = _normalize_str(role)
        norm_name = _normalize_str(name)

        results: List[UIElementSelector] = []
        target_pages = (
            [self.pages[route]]
            if route is not None and route in self.pages
            else ([] if route is not None else list(self.pages.values()))
        )

        for page_snap in target_pages:
            for el in page_snap.elements:
                if _normalize_str(el.role) == norm_role and _normalize_str(el.accessible_name) == norm_name:
                    results.append(el)

        return results

    def get_all_elements(self) -> List[UIElementSelector]:
        """Return a flat list of all discovered elements across all pages."""
        all_els: List[UIElementSelector] = []
        for page_snap in self.pages.values():
            all_els.extend(page_snap.elements)
        return all_els
