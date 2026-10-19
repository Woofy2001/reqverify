from pathlib import Path
import re
import pytest

def parse_aria_snapshot_line(line: str) -> dict | None:
    """Tolerant parser for a single line in a Playwright ARIA snapshot YAML-like tree."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    # Matches: - role "accessible name" [attrs] or - role [attrs] or - role:
    match = re.match(r"^-\s+([a-zA-Z0-9_-]+)(?:\s+\"([^\"]+)\")?(?:\s+\[(.*)\])?(?::)?$", stripped)
    if not match:
        # Check text lines: - text: "..." or - text: ...
        text_match = re.match(r"^-\s+text:\s*(?:\"([^\"]+)\"|(.*))$", stripped)
        if text_match:
            text_val = text_match.group(1) or text_match.group(2)
            return {"role": "text", "name": text_val.strip(), "attrs": {}}
        return None

    role = match.group(1)
    name = match.group(2) or ""
    attrs_raw = match.group(3) or ""

    attrs = {}
    if attrs_raw:
        for item in attrs_raw.split():
            if "=" in item:
                k, v = item.split("=", 1)
                attrs[k] = v.strip("\"'")
            else:
                attrs[item] = True

    indent = len(line) - len(line.lstrip(" "))
    return {
        "role": role,
        "name": name,
        "attrs": attrs,
        "indent": indent
    }

def test_spike_s2_login_snapshot_parsing():
    fixture_path = Path("tests/fixtures/snapshots/techstore_login.yaml")
    assert fixture_path.exists(), "Login snapshot fixture missing"
    
    lines = fixture_path.read_text(encoding="utf-8").splitlines()
    elements = [parse_aria_snapshot_line(l) for l in lines]
    elements = [e for e in elements if e is not None]

    roles = [e["role"] for e in elements]
    names = [e["name"] for e in elements]

    assert "heading" in roles
    assert "Sign in to TechStore" in names
    assert "textbox" in roles
    assert "Email address" in names
    assert "Password" in names
    assert "button" in roles
    assert "Sign in" in names
    assert "link" in roles
    assert "Forgot your password?" in names

def test_spike_s2_cart_snapshot_parsing():
    fixture_path = Path("tests/fixtures/snapshots/techstore_cart.yaml")
    assert fixture_path.exists(), "Cart snapshot fixture missing"
    
    lines = fixture_path.read_text(encoding="utf-8").splitlines()
    elements = [parse_aria_snapshot_line(l) for l in lines]
    elements = [e for e in elements if e is not None]

    roles_and_names = {(e["role"], e["name"]) for e in elements}
    assert ("heading", "Your Shopping Cart") in roles_and_names
    assert ("button", "Apply Discount") in roles_and_names
    assert ("button", "Proceed to Checkout") in roles_and_names
    assert ("textbox", "Discount code") in roles_and_names

def test_spike_s2_checkout_snapshot_parsing():
    fixture_path = Path("tests/fixtures/snapshots/techstore_checkout.yaml")
    assert fixture_path.exists(), "Checkout snapshot fixture missing"
    
    lines = fixture_path.read_text(encoding="utf-8").splitlines()
    elements = [parse_aria_snapshot_line(l) for l in lines]
    elements = [e for e in elements if e is not None]

    roles_and_names = {(e["role"], e["name"]) for e in elements}
    assert ("heading", "Shipping Address") in roles_and_names
    assert ("combobox", "State / Province") in roles_and_names
    assert ("checkbox", "Billing address matches shipping address") in roles_and_names
    assert ("button", "Continue to Payment") in roles_and_names
