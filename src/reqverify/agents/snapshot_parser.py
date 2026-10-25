"""Tolerant parser for Playwright page.aria_snapshot() YAML-like accessibility trees (Step 5.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional

INTERACTIVE_ROLES = {
    "button",
    "link",
    "textbox",
    "checkbox",
    "combobox",
    "spinbutton",
    "option",
    "radio",
    "switch",
    "tab",
    "menuitem",
    "searchbox",
    "slider",
}

SEMANTIC_CONTAINER_ROLES = {
    "listitem",
    "row",
    "region",
    "article",
    "form",
    "navigation",
    "table",
    "dialog",
    "section",
    "group",
}


@dataclass
class ParsedAriaNode:
    """Structured node parsed from a single line of an ARIA accessibility snapshot."""

    role: str
    accessible_name: str
    indent: int
    is_interactive: bool
    attributes: Dict[str, Any] = field(default_factory=dict)
    parent_role: Optional[str] = None
    parent_name: Optional[str] = None
    line_number: int = 0


def _parse_attributes(attrs_raw: str) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    if not attrs_raw:
        return attrs
    for item in attrs_raw.strip().split():
        if "=" in item:
            k, v = item.split("=", 1)
            attrs[k.strip()] = v.strip("\"'")
        else:
            attrs[item.strip()] = True
    return attrs


def parse_aria_snapshot_line(line: str, line_number: int = 0) -> Optional[Dict[str, Any]]:
    """Tolerantly parse a single line of a Playwright ARIA snapshot."""
    if not line or not line.strip():
        return None

    stripped = line.strip()
    if stripped.startswith("#"):
        return None

    indent = len(line.expandtabs(2)) - len(line.expandtabs(2).lstrip(" "))

    # Check text lines: - text: "..." or - text: ...
    text_match = re.match(r"^-\s+text:\s*(?:\"([^\"]*)\"|(.*?))\s*$", stripped)
    if text_match:
        text_val = text_match.group(1) if text_match.group(1) is not None else (text_match.group(2) or "")
        return {
            "role": "text",
            "name": text_val.strip(),
            "attrs": {},
            "indent": indent,
            "line_number": line_number,
        }

    # Standard ARIA role line: - role "accessible name" [attrs]:
    # Tolerant to unclosed bracket or trailing colon
    role_match = re.match(
        r"^-\s+([a-zA-Z0-9_-]+)(?:\s+\"([^\"]*)\")?(?:\s+\[([^\]]*)\]?)?(?:\s*:.*)?$",
        stripped,
    )
    if not role_match:
        return None

    role = role_match.group(1).lower()
    name = (role_match.group(2) or "").strip()
    attrs_raw = role_match.group(3) or ""
    attrs = _parse_attributes(attrs_raw)

    return {
        "role": role,
        "name": name,
        "attrs": attrs,
        "indent": indent,
        "line_number": line_number,
    }


def parse_aria_snapshot(raw_tree: str) -> List[ParsedAriaNode]:
    """Parse a complete Playwright ARIA snapshot tree into structured nodes with parent context.

    Preserves indentation hierarchy so child controls (e.g. duplicate 'Add to cart' buttons)
    inherit the role and accessible/heading name of their enclosing semantic container.
    """
    if not raw_tree:
        return []

    nodes: List[ParsedAriaNode] = []
    # Stack items: {"indent": int, "role": str, "name": str}
    stack: List[Dict[str, Any]] = []

    for idx, line in enumerate(raw_tree.splitlines(), start=1):
        parsed = parse_aria_snapshot_line(line, line_number=idx)
        if parsed is None:
            continue

        indent = parsed["indent"]
        role = parsed["role"]
        name = parsed["name"]
        attrs = parsed["attrs"]

        # Pop stack frames at the same or deeper indentation level
        while stack and stack[-1]["indent"] >= indent:
            stack.pop()

        # If this node is a heading or cell with a name inside an unnamed semantic container,
        # enrich the immediate semantic container on the stack with this contextual label.
        if role in {"heading", "cell"} and name and stack:
            for frame in reversed(stack):
                if frame["role"] in SEMANTIC_CONTAINER_ROLES and not frame["name"]:
                    frame["name"] = name
                    break

        # Resolve enclosing parent context (prefer nearest semantic container or immediate parent)
        parent_role: Optional[str] = None
        parent_name: Optional[str] = None
        if stack:
            # Look for nearest semantic container with or without name, fallback to immediate parent
            semantic_frames = [f for f in stack if f["role"] in SEMANTIC_CONTAINER_ROLES]
            chosen = semantic_frames[-1] if semantic_frames else stack[-1]
            parent_role = chosen["role"]
            parent_name = chosen["name"] or None

        node = ParsedAriaNode(
            role=role,
            accessible_name=name,
            indent=indent,
            is_interactive=(role in INTERACTIVE_ROLES),
            attributes=attrs,
            parent_role=parent_role,
            parent_name=parent_name,
            line_number=idx,
        )
        nodes.append(node)

        # Push current node onto stack as potential parent for deeper lines
        stack.append({
            "indent": indent,
            "role": role,
            "name": name,
        })

    return nodes
