import subprocess
import time
import urllib.request
import pytest
from playwright.sync_api import sync_playwright

TECHSTORE_PORT = 3000
TECHSTORE_URL = f"http://127.0.0.1:{TECHSTORE_PORT}"

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{url}/api/products", headers={"User-Agent": "pytest"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False

@pytest.fixture(scope="module")
def techstore_server():
    """Ensure TechStore server is available."""
    already_running = False
    try:
        req = urllib.request.Request(TECHSTORE_URL, headers={"User-Agent": "pytest"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                already_running = True
    except Exception:
        already_running = False

    proc = None
    if not already_running:
        proc = subprocess.Popen(["npm", "run", "dev"], cwd="techstore", shell=True)
        ready = wait_for_server(TECHSTORE_URL, timeout=45)
        if not ready:
            if proc:
                proc.terminate()
            pytest.fail("TechStore dev server failed to become ready within timeout")

    yield TECHSTORE_URL

    if proc:
        proc.terminate()
        proc.wait()

def test_login_page_aria_and_auth(techstore_server):
    """Verify Page 1: Login page semantic ARIA elements and credential authentication."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{techstore_server}/login")

        # Verify ARIA elements
        assert page.get_by_role("heading", name="Sign in to TechStore").is_visible()
        email_input = page.get_by_role("textbox", name="Email address")
        pass_input = page.get_by_role("textbox", name="Password")
        submit_btn = page.get_by_role("button", name="Sign in")
        forgot_link = page.get_by_role("link", name="Forgot your password?")

        assert email_input.is_visible()
        assert pass_input.is_visible()
        assert submit_btn.is_visible()
        assert forgot_link.is_visible()

        # Submit valid credentials
        email_input.fill("testuser@example.com")
        pass_input.fill("Password123!")
        submit_btn.click()

        # Wait for redirect to products
        page.wait_for_url("**/products", timeout=10000)
        assert "/products" in page.url
        browser.close()

def test_catalog_filtering_and_stock(techstore_server):
    """Verify Page 2: Product catalog category filtering and stock status indicators."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{techstore_server}/products")

        # Verify page heading
        assert page.get_by_role("heading", name="Product Catalog").is_visible()
        page.wait_for_selector("text=Quantum Pro Laptop", timeout=10000)

        # Filter by Audio
        category_select = page.get_by_role("combobox", name="Filter by category")
        category_select.select_option("Audio")

        # Wait for filtered products
        page.wait_for_selector("text=SonicANC Wireless Headphones", timeout=10000)
        assert page.get_by_text("SonicANC Wireless Headphones").is_visible()

        # Check Out of Stock item
        out_of_stock_item = page.locator("div").filter(has_text="BassMax Portable Speaker")
        assert out_of_stock_item.get_by_role("status", name="Out of Stock").is_visible()

        # Verify Add to cart button is disabled for out of stock item
        add_btn = page.get_by_role("button", name="Add BassMax Portable Speaker to cart")
        assert add_btn.is_disabled()
        browser.close()

def test_cart_discount_calculation(techstore_server):
    """Verify Page 3: Cart quantity manipulation and SAVE20 coupon discount computation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Add item from products page
        page.goto(f"{techstore_server}/products")
        page.wait_for_selector("text=Quantum Pro Laptop", timeout=10000)
        page.get_by_role("button", name="Add Quantum Pro Laptop to cart").click()
        page.wait_for_selector("text=Added Quantum Pro Laptop to cart!", timeout=5000)

        # 2. Navigate to cart
        page.goto(f"{techstore_server}/cart")
        page.wait_for_selector("text=Quantum Pro Laptop", timeout=10000)
        assert page.get_by_role("heading", name="Your Shopping Cart").is_visible()
        assert page.get_by_text("Quantum Pro Laptop").is_visible()

        # 3. Apply SAVE20 coupon
        coupon_input = page.get_by_role("textbox", name="Discount code")
        apply_btn = page.get_by_role("button", name="Apply Discount")

        coupon_input.fill("SAVE20")
        apply_btn.click()

        # Verify discount applied: 20% of 1299.00 = 259.80
        page.wait_for_selector("text=20% discount applied successfully!", timeout=5000)
        assert page.get_by_text("-$259.80").is_visible()
        browser.close()
