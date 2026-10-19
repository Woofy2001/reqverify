import pytest
from playwright.sync_api import sync_playwright
from tests.e2e.test_techstore_pages1_to_3 import techstore_server

def test_checkout_multistep_submission(techstore_server):
    """Verify Page 4: Multi-step checkout wizard flow from shipping to order confirmation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Seed an item into cart first
        page.goto(f"{techstore_server}/products")
        page.get_by_role("button", name="Add Quantum Pro Laptop to cart").click()
        page.wait_for_selector("text=Added Quantum Pro Laptop to cart!", timeout=5000)

        # Navigate to checkout
        page.goto(f"{techstore_server}/checkout")
        assert page.get_by_role("heading", name="Checkout").is_visible()

        # Step 1: Shipping Address
        assert page.get_by_role("heading", name="Shipping Address").is_visible()
        page.get_by_role("button", name="Continue to Payment").click()

        # Step 2: Payment Method
        page.wait_for_selector("text=Payment Method", timeout=5000)
        assert page.get_by_role("heading", name="Payment Method").is_visible()
        page.get_by_role("button", name="Continue to Review").click()

        # Step 3: Review & Place Order
        page.wait_for_selector("text=Review & Place Order", timeout=5000)
        assert page.get_by_role("heading", name="Review & Place Order").is_visible()
        page.get_by_role("button", name="Place Order").click()

        # Step 4: Order Confirmation
        page.wait_for_selector("text=Order Placed Successfully!", timeout=10000)
        confirmation = page.get_by_role("status", name="Order Placed Successfully!")
        assert confirmation.is_visible()
        assert page.get_by_text("Order Reference: ORD-").is_visible()

        browser.close()

def test_admin_order_status_update(techstore_server):
    """Verify Page 5: Administrator order fulfillment portal and status mutation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{techstore_server}/admin/orders")

        # Verify page heading
        assert page.get_by_role("heading", name="Admin Order Fulfillment").is_visible()

        # Locate status select for seeded order ORD-1001
        select_status = page.get_by_role("combobox", name="Update status for ORD-1001")
        assert select_status.is_visible()

        # Update status to Shipped
        select_status.select_option("Shipped")

        # Verify notification
        page.wait_for_selector("text=Order ORD-1001 updated to Shipped", timeout=5000)
        assert page.get_by_text("Order ORD-1001 updated to Shipped").is_visible()

        browser.close()
