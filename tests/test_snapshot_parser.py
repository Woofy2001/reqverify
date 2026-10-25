"""Tests verifying the tolerant ARIA snapshot parser on synthetic and real TechStore 5-page snapshots (Step 5.2)."""

from __future__ import annotations

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = REPO_ROOT / "tests" / "fixtures" / "snapshots"


def test_snapshot_parser_importable():
    """Verify snapshot_parser exports parse_aria_snapshot and ParsedAriaNode."""
    from reqverify.agents.snapshot_parser import parse_aria_snapshot, ParsedAriaNode
    assert callable(parse_aria_snapshot)
    assert ParsedAriaNode is not None


def test_parse_standard_roles_and_attributes():
    """Verify parsing of standard ARIA roles and bracketed state attributes."""
    from reqverify.agents.snapshot_parser import parse_aria_snapshot

    raw_tree = """
- heading "Sign in to TechStore" [level=1]
- textbox "Email address"
- checkbox "Remember me" [checked]
- combobox "Country" [expanded]
- button "Submit" [disabled]
- link "Reset Password"
"""
    nodes = parse_aria_snapshot(raw_tree)
    assert len(nodes) == 6

    by_role = {n.role: n for n in nodes}
    assert by_role["heading"].accessible_name == "Sign in to TechStore"
    assert by_role["heading"].attributes.get("level") == "1"

    assert by_role["checkbox"].accessible_name == "Remember me"
    assert by_role["checkbox"].attributes.get("checked") is True

    assert by_role["button"].accessible_name == "Submit"
    assert by_role["button"].attributes.get("disabled") is True
    assert by_role["button"].is_interactive is True
    assert by_role["heading"].is_interactive is False


def test_parse_nested_hierarchy():
    """Verify indentation-based parent-child hierarchy and semantic context resolution."""
    from reqverify.agents.snapshot_parser import parse_aria_snapshot

    raw_tree = """
- list:
  - listitem:
    - heading "Quantum Pro Laptop" [level=3]
    - button "Add to cart"
  - listitem:
    - heading "Wireless Mouse" [level=3]
    - button "Add to cart"
"""
    nodes = parse_aria_snapshot(raw_tree)
    buttons = [n for n in nodes if n.role == "button"]
    assert len(buttons) == 2

    # Each button should recognize its parent listitem and the sibling/contextual heading inside the container
    assert buttons[0].parent_role == "listitem"
    assert buttons[0].parent_name == "Quantum Pro Laptop"
    assert buttons[1].parent_role == "listitem"
    assert buttons[1].parent_name == "Wireless Mouse"


def test_parse_real_techstore_snapshots():
    """Verify parser succeeds across all 5 TechStore page snapshot fixtures."""
    from reqverify.agents.snapshot_parser import parse_aria_snapshot

    expected_files = [
        ("techstore_login.yaml", "Sign in"),
        ("techstore_products.yaml", "Product Catalog"),
        ("techstore_cart.yaml", "Your Shopping Cart"),
        ("techstore_checkout.yaml", "Checkout"),
        ("techstore_admin.yaml", "Admin Order Fulfillment"),
    ]

    for filename, expected_heading_substr in expected_files:
        fpath = SNAPSHOTS_DIR / filename
        assert fpath.exists(), f"Missing fixture {fpath}"
        raw = fpath.read_text(encoding="utf-8")
        nodes = parse_aria_snapshot(raw)
        assert len(nodes) > 0, f"No nodes parsed from {filename}"

        headings = [n.accessible_name for n in nodes if n.role == "heading"]
        assert any(expected_heading_substr in h for h in headings), (
            f"Expected heading '{expected_heading_substr}' not found in {filename}: {headings}"
        )


def test_parse_malformed_lines_gracefully():
    """Verify parser ignores comments, blank lines, and malformed text without crashing."""
    from reqverify.agents.snapshot_parser import parse_aria_snapshot

    raw_tree = """
# Comment header
   
::: invalid_token :::
- button "Valid Button"
random unprefixed line
- link "Valid Link" [invalid_attr
"""
    nodes = parse_aria_snapshot(raw_tree)
    roles = [n.role for n in nodes]
    assert "button" in roles
    assert "link" in roles
