# Phase 05 — Agent 2: App Explorer

## 1. Objective & Research Traceability
- **Primary Goal:** Implement Agent 2 (App Explorer) to interactively inspect the web application UI using modern Playwright APIs (`page.aria_snapshot()`), parse the accessibility tree into structured UI representations, build disambiguated role-and-accessible-name locators resilient to DOM restructuring, handle Playwright strictness errors gracefully, and identify when required UI elements cannot be found (`no_selector_found` leading to `UNTESTED`).
- **Traceability:**
  - Guides: §1 (Correction 2: ARIA snapshot tree parsing, no `accessibility`), §3 (Decision D2: Python Playwright only, role+name locators), §10 (Agent 2 specification).
  - Blueprints: Section 3.2 (App Explorer state-space mapping).
  - NFRs: NFR-02 (Resilient Selectors), NFR-03 (Strict mode awareness).
  - RQs: RQ4 (UI coverage enabling end-to-end verification).

## 2. Entry Gate
- [ ] Phase 02 (TechStore SUT and `dev_app`) running and accessible locally.
- [ ] Phase 04 (Agent 1: Requirements Analyst) produces valid `CoverageMatrix` and extracted conditions.
- [ ] Spike S-3 (`page.aria_snapshot()` formatting and parser spike) completed in Phase 00.

## 3. Inputs & Dependencies
- Running target application (`http://localhost:3000` or `http://localhost:3001` for `dev_app`)
- Application credentials (from pipeline configuration: test user `testuser@example.com` / `Password123!`, admin `admin@example.com` / `AdminPass123!`)
- `CoverageMatrix` from Agent 1 (to focus exploration on relevant flows)
- `playwright` (Python $\ge 1.59$ with asyncio or synchronous Page API)
- `src/reqverify/schemas/contracts.py`

## 4. Deliverables
- `src/reqverify/schemas/selectors.py` (Pydantic v2 data models for `UIElementSelector`, `SelectorMap`, and `PageSnapshot`)
- `src/reqverify/agents/snapshot_parser.py` (Tolerant YAML-like line parser for `page.aria_snapshot()` tree)
- `src/reqverify/agents/locator_builder.py` (Role + accessible name generator, strictness disambiguator using scoping or `.nth()`)
- `src/reqverify/agents/explorer.py` (`AppExplorerAgent`: deterministic crawler + requirement-guided stateful flow navigator)
- `tests/fixtures/snapshots/` (Real saved ARIA snapshots from TechStore 5 pages)
- `tests/test_snapshot_parser.py` (Offline unit tests validating parser on real snapshot text)
- `tests/test_locator_builder.py` (Unit tests verifying selector generation, duplicate handling, and strictness disambiguation)
- `tests/test_agent2_explorer.py` (Integration tests with recorded Playwright traces and mock page fixtures)
- `tests/test_agent2_live_smoke.py` (`@pytest.mark.live` smoke test verifying live exploration of TechStore)

## 5. context7 Lookups
- `context7:/playwright/playwright`:
  - `page.aria_snapshot()` syntax and schema options (`mode="ai"` vs default).
  - `page.get_by_role(role, name=..., exact=...)` locator construction.
  - Locator filtering and parent scoping (`locator.filter()`, `locator.locator()`).
  - Handling `playwright._impl._errors.Error: strict mode violation`.

## 6. Step-by-Step Tasks

### Step 5.1: Define Selector & Snapshot Data Contracts
- **Goal:** Create strict Pydantic v2 schemas representing discovered UI elements, locator recipes, and page accessibility trees.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_selector_schemas.py`
  - `test_selector_schema_serialization()`: Serializes and deserializes `UIElementSelector` with role, name, locator string, page route, and bounding state.
  - `test_selector_map_lookup()`: Looks up locators by role and normalized accessible name.
- **Implementation Spec:**
  - `src/reqverify/schemas/selectors.py`:
    ```python
    from pydantic import BaseModel, Field
    from typing import Optional, List, Dict

    class UIElementSelector(BaseModel):
        element_id: str
        role: str
        accessible_name: str
        locator_recipe: str  # e.g., 'page.get_by_role("button", name="Add to cart", exact=True)'
        page_route: str
        is_interactive: bool = True
        parent_role: Optional[str] = None
        nth_index: Optional[int] = None

    class PageSnapshot(BaseModel):
        route: str
        title: str
        raw_aria_tree: str
        elements: List[UIElementSelector] = Field(default_factory=list)

    class SelectorMap(BaseModel):
        base_url: str
        pages: Dict[str, PageSnapshot] = Field(default_factory=dict)
    ```
- **Verification Command (PowerShell):**
  ```powershell
  pytest tests/test_selector_schemas.py -v
  ```

### Step 5.2: Tolerant ARIA Snapshot Parser
- **Goal:** Implement an ARIA snapshot parser that ingests Playwright's YAML-like text (e.g., `- button "Add to cart" [disabled]`) and extracts structured roles, accessible names, states, and indentation hierarchy without failing on complex custom trees.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_snapshot_parser.py`
  - `test_parse_standard_roles()`: Parses buttons, links, textboxes, headings, checkboxes, and comboboxes.
  - `test_parse_nested_hierarchy()`: Preserves parent-child nesting via indentation level.
  - `test_parse_real_techstore_snapshots()`: Runs parser over pre-recorded ARIA snapshots saved in `tests/fixtures/snapshots/techstore_*.yaml`.
  - `test_parse_malformed_lines_gracefully()`: Skips comments or non-standard tokens without throwing exceptions.
- **Implementation Spec:**
  - `src/reqverify/agents/snapshot_parser.py`:
    - Regex pattern matching: `^\s*-\s*([a-zA-Z0-9_-]+)(?:\s+"([^"]+)")?(?:\s+\[(.*)\])?`
    - Computes indentation depth (spaces / tabs) to track parent container hierarchy.
    - Extracts inline states (`[disabled]`, `[checked]`, `[expanded]`).
- **Verification Command:**
  ```powershell
  pytest tests/test_snapshot_parser.py -v
  ```

### Step 5.3: Locator Builder & Strictness Disambiguator
- **Goal:** Convert parsed elements into executable Python Playwright locator strings while handling duplicate accessible names and strict mode violations.
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_locator_builder.py`
  - `test_single_element_locator()`: Generates `page.get_by_role("button", name="Sign in", exact=True)`.
  - `test_duplicate_elements_scoping()`: Disambiguates duplicate "Add to cart" buttons by qualifying them with product card parent container.
  - `test_duplicate_elements_nth_fallback()`: Applies `.nth(i)` if no parent semantic container exists.
  - `test_no_selector_found_sentinel()`: Returns `None` or raises `NoSelectorFoundError` when requested role/name cannot be located.
- **Implementation Spec:**
  - `src/reqverify/agents/locator_builder.py`:
    - Check name collision across elements with the same role on the same page route.
    - If unique: `exact=True` on `get_by_role`.
    - If duplicate: check if parent element has distinct accessible name or heading; if so, generate chained locator: `page.locator(...).get_by_role(...)`.
    - If indistinguishable: append `.nth(index)`.
- **Verification Command:**
  ```powershell
  pytest tests/test_locator_builder.py -v
  ```

### Step 5.4: Stateful Explorer & Navigation Crawler
- **Goal:** Implement the high-level `AppExplorerAgent` driving Playwright to visit the initial route, authenticate via seeded credentials, crawl main navigation links, and execute requirement-targeted multi-step flows (e.g., product search $\to$ product detail $\to$ add to cart $\to$ checkout).
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/test_agent2_explorer.py`
  - `test_explorer_crawls_five_pages()`: Simulates visiting `/login`, `/products`, `/cart`, `/checkout`, `/admin/orders` using mock Playwright page.
  - `test_explorer_records_selector_map()`: Asserts populated `SelectorMap` returned with verified locators for each page.
  - `test_explorer_explicit_wait_discipline()`: Verifies explorer waits for network idle or DOM selector visibility rather than `time.sleep()`.
- **Implementation Spec:**
  - `src/reqverify/agents/explorer.py`:
    - Crawl loop:
      1. Navigate to `base_url`.
      2. If login required, locate username/password fields and sign in.
      3. Capture `page.aria_snapshot()` and record current route.
      4. Traverse discovered links matching internal domain.
      5. For flows indicated by `CoverageMatrix` (e.g. cart manipulation), execute deterministic setup sequences.
      6. Return aggregated `SelectorMap`.
- **Verification Command:**
  ```powershell
  pytest tests/test_agent2_explorer.py -v
  ```

## 7. Test Suite for this Phase

### Offline Replay Suite
All offline unit and fixture-based tests run in < 5 seconds without internet or live LLM:
```powershell
pytest tests/test_selector_schemas.py tests/test_snapshot_parser.py tests/test_locator_builder.py tests/test_agent2_explorer.py -v
```

### Live Smoke Test
Runs against local running TechStore (`http://localhost:3000`):
```powershell
# In terminal 1: npm run dev in techstore
# In terminal 2:
pytest tests/test_agent2_live_smoke.py -v -m live
```

## 8. Exit Gate
- [ ] `PageSnapshot` and `SelectorMap` schemas validate all 5 TechStore pages.
- [ ] Parser passes on real saved snapshots from Login, Products, Cart, Checkout, and Admin pages.
- [ ] Locator builder generates strict-mode compliant locators (`exact=True`, parent scoping, `.nth()` fallback).
- [ ] All offline tests pass with 100% success rate.
- [ ] Live smoke test navigates TechStore, captures ARIA snapshots, and extracts valid `SelectorMap`.
