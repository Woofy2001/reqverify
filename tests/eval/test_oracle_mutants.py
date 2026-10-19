"""Oracle test suite verifying that each seeded mutant (M01..M10) triggers its exact intended defect.

Verifies:
- Under clean execution (MUTANT unset or CLEAN), all conditions PASS.
- Under MUTANT=Mxx, the targeted defect is activated while untargeted features remain correct.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, BrowserContext, expect

TECHSTORE_BASE_URL = "http://127.0.0.1:3000"


def set_active_mutant(context: BrowserContext, mutant_id: str):
    """Sets the mutant cookie in the browser context."""
    context.add_cookies([
        {
            "name": "reqverify_mutant",
            "value": mutant_id,
            "domain": "127.0.0.1",
            "path": "/",
        }
    ])


def clear_active_mutant(context: BrowserContext):
    """Clears mutant cookie in the browser context."""
    context.clear_cookies()


@pytest.fixture(autouse=True)
def reset_techstore_state(page: Page):
    """Reset database and clear browser state before each test."""
    try:
        page.request.post(f"{TECHSTORE_BASE_URL}/api/test/reset")
    except Exception:
        pass


def test_mutant_m01_broken_email_regex(page: Page, context: BrowserContext):
    """M01: Email validation regex accepts 'a@b' without TLD extension."""
    # 1. Clean verification: 'a@b' is rejected with validation message
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/login")
    page.fill('input[type="email"]', "a@b")
    page.fill('input[type="password"]', "password123")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_text("Invalid email format")).to_be_visible()

    # 2. Mutant M01 verification: 'a@b' passes email regex validation
    set_active_mutant(context, "M01")
    page.goto(f"{TECHSTORE_BASE_URL}/login")
    page.fill('input[type="email"]', "a@b")
    page.fill('input[type="password"]', "password123")
    page.get_by_role("button", name="Sign in").click()
    # M01 accepts 'a@b' format, so the "Invalid email format" error is absent
    expect(page.get_by_text("Invalid email format")).not_to_be_visible()


def test_mutant_m02_password_min_length_skipped(page: Page, context: BrowserContext):
    """M02: Minimum password length requirement (<6 chars) skipped."""
    # 1. Clean: 3-character password is rejected
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/login")
    page.fill('input[type="email"]', "test@example.com")
    page.fill('input[type="password"]', "123")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_text("Password must be at least 6 characters")).to_be_visible()

    # 2. Mutant M02: 3-character password check skipped
    set_active_mutant(context, "M02")
    page.goto(f"{TECHSTORE_BASE_URL}/login")
    page.fill('input[type="email"]', "test@example.com")
    page.fill('input[type="password"]', "123")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_text("Password must be at least 6 characters")).not_to_be_visible()


def test_mutant_m03_price_filter_strict_inequality(page: Page, context: BrowserContext):
    """M03: Price filter uses < instead of <=, excluding boundary price items."""
    # Seeded item: ErgoPrecision Wireless Mouse is exactly $49.00
    # 1. Clean: filter with max price 49.00 includes Mouse (49.00 <= 49.00)
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.fill('input[aria-label="Filter by maximum price"]', "49.00")
    page.wait_for_timeout(300)
    expect(page.get_by_text("ErgoPrecision Wireless Mouse")).to_be_visible()

    # 2. Mutant M03: filter with max price 49.00 uses < and excludes Mouse (49.00 < 49.00 is False)
    set_active_mutant(context, "M03")
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.fill('input[aria-label="Filter by maximum price"]', "49.00")
    page.wait_for_timeout(300)
    expect(page.get_by_text("ErgoPrecision Wireless Mouse")).not_to_be_visible()


def test_mutant_m04_out_of_stock_badge_missing(page: Page, context: BrowserContext):
    """M04: 'Out of stock' badge missing when stock is 0."""
    # BassMax Portable Speaker has stock=0
    # 1. Clean: 'Out of stock' status badge is visible
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    expect(page.get_by_role("status", name="Out of stock")).to_be_visible()

    # 2. Mutant M04: 'Out of stock' badge is not rendered
    set_active_mutant(context, "M04")
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    expect(page.get_by_role("status", name="Out of stock")).not_to_be_visible()


def test_mutant_m05_line_total_ignores_quantity(page: Page, context: BrowserContext):
    """M05: Line total ignores quantity (price * 1 instead of price * qty)."""
    # 1. Clean: Add Mouse ($49.00), set qty to 2 -> Line total is $98.00
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    page.fill('input[aria-label="Quantity for ErgoPrecision Wireless Mouse"]', "2")
    expect(page.locator("p", has_text="$98.00")).to_be_visible()

    # 2. Mutant M05: Line total stays at $49.00 regardless of qty=2
    set_active_mutant(context, "M05")
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    page.fill('input[aria-label="Quantity for ErgoPrecision Wireless Mouse"]', "2")
    expect(page.locator("p", has_text="$98.00")).not_to_be_visible()
    expect(page.locator("p", has_text="$49.00")).to_be_visible()


def test_mutant_m06_discount_applied_inverted(page: Page, context: BrowserContext):
    """M06: Discount adds to total instead of subtracting."""
    # Mouse is $49.00 + $10 shipping = $59.00.
    # 20% discount on $49.00 = $9.80.
    # Clean total: $49.00 - $9.80 + $10.00 = $49.20.
    # Mutant M06 total: $49.00 + $9.80 + $10.00 = $68.80 (increases!).
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    page.fill('input[placeholder="Promo code (try SAVE20)"]', "SAVE20")
    page.get_by_role("button", name="Apply Discount").click()
    expect(page.get_by_text("Coupon SAVE20 applied")).to_be_visible()
    expect(page.get_by_text("$49.20")).to_be_visible()

    # 2. Mutant M06: total becomes $68.80
    set_active_mutant(context, "M06")
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    page.fill('input[placeholder="Promo code (try SAVE20)"]', "SAVE20")
    page.get_by_role("button", name="Apply Discount").click()
    expect(page.get_by_text("$68.80")).to_be_visible()


def test_mutant_m07_checkout_accepts_empty_address(page: Page, context: BrowserContext):
    """M07: Step 1 allows proceeding to Step 2 even when address is empty."""
    # 1. Clean: Clicking Continue with empty address blocks with error
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    page.fill('input[aria-label="Street address"]', "")
    page.fill('input[aria-label="City"]', "")
    page.get_by_role("button", name="Continue to Payment").click()
    expect(page.get_by_text("Shipping address and city are required")).to_be_visible()

    # 2. Mutant M07: Step 1 skips address check and transitions to Payment step
    set_active_mutant(context, "M07")
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    page.fill('input[aria-label="Street address"]', "")
    page.fill('input[aria-label="City"]', "")
    page.get_by_role("button", name="Continue to Payment").click()
    expect(page.get_by_role("heading", name="Payment Method")).to_be_visible()


def test_mutant_m08_order_total_omits_shipping(page: Page, context: BrowserContext):
    """M08: Order summary grand total omits shipping charges."""
    # Mouse is $49.00, shipping $10.00.
    # Clean grand total: $59.00.
    # Mutant M08 grand total: $49.00 (omits shipping).
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    expect(page.locator('[aria-label="Order Grand Total"]')).to_have_text("$59.00")

    # 2. Mutant M08: grand total is $49.00
    set_active_mutant(context, "M08")
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    expect(page.locator('[aria-label="Order Grand Total"]')).to_have_text("$49.00")


def test_mutant_m09_admin_shipped_status_rejected(page: Page, context: BrowserContext):
    """M09: Admin status change to 'Shipped' is rejected/reverted."""
    # 1. Clean: Clicking Mark Shipped changes status chip to Shipped
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/admin/orders")
    page.get_by_role("button", name="Mark Shipped for order ORD-1001").click()
    expect(page.locator("tr:has-text('ORD-1001')").get_by_role("status")).to_have_text("Shipped")

    # 2. Mutant M09: Status change is rejected, remains Processing
    set_active_mutant(context, "M09")
    page.goto(f"{TECHSTORE_BASE_URL}/admin/orders")
    page.get_by_role("button", name="Mark Shipped for order ORD-1002").click()
    expect(page.locator("tr:has-text('ORD-1002')").get_by_role("status")).to_have_text("Processing")


def test_mutant_m10_cart_not_cleared_after_checkout(page: Page, context: BrowserContext):
    """M10: Cart is not cleared after successful checkout."""
    # 1. Clean: Placing order clears cart
    clear_active_mutant(context)
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    page.fill('input[aria-label="Street address"]', "123 Main St")
    page.fill('input[aria-label="City"]', "Metropolis")
    page.get_by_role("button", name="Continue to Payment").click()
    page.fill('input[aria-label="Card number"]', "4242424242424242")
    page.get_by_role("button", name="Continue to Review").click()
    page.get_by_role("button", name="Place Order").click()
    expect(page.get_by_text("Order Placed Successfully!")).to_be_visible()
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    expect(page.get_by_text("Your shopping cart is currently empty")).to_be_visible()

    # 2. Mutant M10: Cart retains items after order placement
    set_active_mutant(context, "M10")
    page.goto(f"{TECHSTORE_BASE_URL}/products")
    page.get_by_role("button", name="Add ErgoPrecision Wireless Mouse to cart").click()
    page.goto(f"{TECHSTORE_BASE_URL}/checkout")
    page.fill('input[aria-label="Street address"]', "123 Main St")
    page.fill('input[aria-label="City"]', "Metropolis")
    page.get_by_role("button", name="Continue to Payment").click()
    page.fill('input[aria-label="Card number"]', "4242424242424242")
    page.get_by_role("button", name="Continue to Review").click()
    page.get_by_role("button", name="Place Order").click()
    expect(page.get_by_text("Order Placed Successfully!")).to_be_visible()
    page.goto(f"{TECHSTORE_BASE_URL}/cart")
    expect(page.get_by_text("ErgoPrecision Wireless Mouse")).to_be_visible()
