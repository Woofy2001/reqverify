# Phase 02 — TechStore SUT & Development Application

## 1. Objective & Research Traceability
- **Primary Goal:** Implement the benchmark System Under Test (**TechStore Portal**) on Next.js 16 (TypeScript, App Router) covering 5 operational pages with robust semantic ARIA accessibility, seeded deterministic SQLite database, and credentials. Simultaneously implement the isolated **`dev_app/`** to enforce Invariant D13 (dev/eval prompt split).
- **Traceability:**
  - Guides: §1 (Correction 13), §3 (Decisions D9, D13), §8.1, §9 (Agent 2 accessibility assumption).
  - NFRs: Deterministic test execution against opaque black-box SUT.

## 2. Entry Gate
- [ ] Node.js v22.14.0 verified.
- [ ] Docker engine running.
- [ ] Phase 00 toolchain installed.

## 3. Inputs & Dependencies
- `npx create-next-app@latest` (Next.js 16 LTS)
- SQLite database driver (`better-sqlite3` or Prisma SQLite)
- Seed fixtures: `techstore/prisma/seed.ts` or `techstore/data/seed.json`

## 4. Deliverables
- `techstore/`: Complete Next.js 16 application
  - `src/app/login/page.tsx` (Page 1: Auth form)
  - `src/app/catalog/page.tsx` (Page 2: Product filtering & stock badges)
  - `src/app/cart/page.tsx` (Page 3: Cart table & discount coupon code)
  - `src/app/checkout/page.tsx` (Page 4: Multi-step checkout wizard)
  - `src/app/admin/orders/page.tsx` (Page 5: Order status fulfillment table)
  - `src/lib/db.ts` (Deterministic SQLite database seeder)
- `dev_app/`: Tiny isolated 2-page app (Todo / Mini-shop) for tuning prompts without contaminating evaluation requirements (D13).
- `dev_app/requirements.md`: Small set of dev requirements for Agent 1 & Agent 3 tuning.
- `tests/e2e/test_techstore_clean.py`: Pytest-Playwright E2E suite verifying clean app compliance.
- `tests/e2e/test_dev_app.py`: Verification suite for dev app.

## 5. context7 Lookups
- `context7:/vercel/next.js`: Next.js 16 App Router conventions, form actions, server components.
- `context7:/microsoft/playwright-python`: Locator role selectors (`get_by_role`, `get_by_label`).

## 6. Step-by-Step Tasks

### Step 2.1: Initialize Next.js 16 App with Seeded SQLite Data
- **Goal:** Scaffold `techstore/` with TypeScript, Tailwind CSS, App Router, and deterministic SQLite store.
- **Skill to invoke:** `using-git-worktrees`.
- **Test file written FIRST:** `tests/e2e/test_db_seed.py`
  - `test_db_seed_determinism()`: Proves resetting the DB returns exact seed counts (10 products, 2 users, 1 admin, 1 coupon `SAVE20`).
- **Implementation Spec:**
  - Create app in `techstore/`.
  - Database seed:
    - User: `user@example.com` / `Password123!`
    - Admin: `admin@example.com` / `AdminPass2026!`
    - Coupon: `SAVE20` (20% off cart total).
  - Reset script: `npm run db:reset` or endpoint `POST /api/test/reset`.
- **Verification Command (PowerShell):**
  ```powershell
  cd techstore; npm run db:reset; cd ..
  pytest tests/e2e/test_db_seed.py -v
  ```

### Step 2.2: Implement Pages 1–3 (Login, Catalog/Filter, Cart)
- **Goal:** Deliver fully accessible UI with explicit ARIA roles, accessible names, and form validations.
- **Skills to invoke:** `design-taste-frontend` + `impeccable`, `emil-design-eng`.
- **Test file written FIRST:** `tests/e2e/test_techstore_pages1_to_3.py`
  - `test_login_page_aria_and_auth()`: Verifies `role="textbox", name="Email"` and valid submit redirects.
  - `test_catalog_filtering_and_stock()`: Verifies category filter dropdown and `role="status"` for out-of-stock badge.
  - `test_cart_discount_calculation()`: Verifies applying `SAVE20` subtracts exactly 20% from total.
- **Implementation Spec:**
  - Follow Guide §8.1.
  - Strict ARIA invariant: Every button, input, alert, and table cell has semantic role and non-empty accessible name (`aria-label` or visible text).
- **Verification Command:**
  ```powershell
  pytest tests/e2e/test_techstore_pages1_to_3.py -v
  ```
- **Playwright MCP Action:** Use `playwright` MCP (`init-browser`, `get-full-dom`) to verify accessibility tree of `/catalog` and `/cart`.

### Step 2.3: Implement Pages 4–5 (Multi-step Checkout & Admin Portal)
- **Goal:** Deliver checkout flow (Address -> Payment -> Confirmation) and Admin order status fulfillment table.
- **Skills to invoke:** `design-taste-frontend` + `impeccable`.
- **Test file written FIRST:** `tests/e2e/test_techstore_pages4_to_5.py`
  - `test_checkout_multistep_submission()`: Completes step 1, step 2, submits, verifies order generated.
  - `test_admin_order_status_update()`: Logs in as admin, transitions order to "Shipped", verifies update.
- **Implementation Spec:**
  - Ensure cart is cleared upon successful order placement (`M10` clean counterpart).
- **Verification Command:**
  ```powershell
  pytest tests/e2e/test_techstore_pages4_to_5.py -v
  ```
- **Playwright MCP Action:** Capture screenshots and inspect DOM of completed order confirmation.

### Step 2.4: Implement Isolated Development Application (`dev_app/`)
- **Goal:** Build the separate tiny web app and requirements doc for prompt engineering and ablation tuning (Invariant D13).
- **Skill to invoke:** `test-driven-development`.
- **Test file written FIRST:** `tests/e2e/test_dev_app.py`
  - `test_dev_app_functionality()`: Verifies basic UI observable flows of dev app.
- **Implementation Spec:**
  - Path: `dev_app/` (e.g., Simple task/order manager with 5 requirements).
  - Path: `dev_app/requirements.md` (Contains `REQ-DEV-01` to `REQ-DEV-05`).
- **Verification Command:**
  ```powershell
  pytest tests/e2e/test_dev_app.py -v
  ```

## 7. Test Suite for this Phase

| Test File | What it Proves | Mode |
|---|---|---|
| `tests/e2e/test_db_seed.py` | Deterministic database seeding and reset capability | Offline Unit |
| `tests/e2e/test_techstore_pages1_to_3.py` | Pages 1–3 function with correct ARIA roles and logic | Playwright E2E |
| `tests/e2e/test_techstore_pages4_to_5.py` | Pages 4–5 multi-step checkout and admin order status | Playwright E2E |
| `tests/e2e/test_dev_app.py` | Development app functions independently for prompt tuning | Playwright E2E |

## 8. Exit Gate
- [ ] `pytest tests/e2e/` passes 100% against running clean TechStore.
- [ ] Playwright MCP accessibility audit confirms 0 missing accessible names on interactive controls.
- [ ] `dev_app/` and `dev_app/requirements.md` verified operational.
- [ ] Code review completed (`requesting-code-review`).
- [ ] Logged in `docs/decision-log.md`.

## 9. Pitfalls & Risks
- **Pitfall:** Fragile styling or CSS selectors.
  - *Mitigation:* Design app strictly with standard ARIA roles (`role="button"`, `role="combobox"`).
- **Pitfall:** Test state leakage between runs.
  - *Mitigation:* Deterministic reset endpoint `/api/test/reset` invoked before each test run.

## 10. Unverified Items (⚠️) Resolved in this Phase
- §16.3 Item 6: Node.js LTS v22.14 verified with Next.js 16 build.

## 11. Handoff to Next Phase
- Delivers clean TechStore SUT and `dev_app/` to **Phase 03 (Ground Truth & Mutants)**.
