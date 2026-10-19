"""Tests for evaluation ground truth data integrity.

Verifies:
1. Requirements formatting (REQ-01 .. REQ-nn)
2. 100% verbatim substring match of source_span in requirements.md
3. REQ-09 backend-only designation (ui_observable=False, expected_clean=UNTESTED)
4. Consistency across requirements.md, conditions.csv, and mutants_expected.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GROUND_TRUTH_DIR = REPO_ROOT / "eval" / "ground_truth"
REQS_PATH = GROUND_TRUTH_DIR / "requirements.md"
CONDITIONS_PATH = GROUND_TRUTH_DIR / "conditions.csv"
MUTANTS_EXPECTED_PATH = GROUND_TRUTH_DIR / "mutants_expected.csv"


def test_ground_truth_files_exist():
    assert REQS_PATH.exists(), f"Missing {REQS_PATH}"
    assert CONDITIONS_PATH.exists(), f"Missing {CONDITIONS_PATH}"
    assert MUTANTS_EXPECTED_PATH.exists(), f"Missing {MUTANTS_EXPECTED_PATH}"


def test_requirements_id_format():
    content = REQS_PATH.read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,3}\s+(REQ-\d{2}):?\s+(.*)$", content, re.MULTILINE)
    assert len(headings) >= 15, f"Expected at least 15 requirements, found {len(headings)}"
    assert len(headings) <= 25, f"Expected at most 25 requirements, found {len(headings)}"

    # Check contiguous numbering or unique valid IDs
    req_ids = [h[0] for h in headings]
    assert len(req_ids) == len(set(req_ids)), "Duplicate requirement IDs detected"
    for req_id in req_ids:
        assert re.match(r"^REQ-\d{2}$", req_id), f"Invalid ID format: {req_id}"


def test_source_spans_exist_in_document():
    req_text = REQS_PATH.read_text(encoding="utf-8")

    with open(CONDITIONS_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 20, f"Expected at least 20 conditions in conditions.csv, found {len(rows)}"

    for row in rows:
        span = row["source_span"]
        assert span, f"Condition {row['condition_id']} has empty source_span"
        assert (
            span in req_text
        ), f"source_span for condition {row['condition_id']} is not an exact verbatim substring of requirements.md:\n{span}"


def test_untested_ground_truth_case():
    with open(CONDITIONS_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    req09_rows = [r for r in rows if r["req_id"] == "REQ-09"]
    assert len(req09_rows) >= 1, "Expected at least one condition for REQ-09"

    for r in req09_rows:
        assert r["ui_observable"].strip().lower() in (
            "false",
            "0",
            "no",
        ), f"REQ-09 condition {r['condition_id']} must have ui_observable=False"
        assert (
            r["expected_clean"] == "UNTESTED"
        ), f"REQ-09 condition {r['condition_id']} must have expected_clean=UNTESTED"


def test_mutants_expected_csv_integrity():
    with open(CONDITIONS_PATH, mode="r", encoding="utf-8") as f:
        cond_reader = csv.DictReader(f)
        cond_rows = list(cond_reader)

    with open(MUTANTS_EXPECTED_PATH, mode="r", encoding="utf-8") as f:
        mut_reader = csv.DictReader(f)
        mut_rows = list(mut_reader)

    cond_ids = [r["condition_id"] for r in cond_rows]
    mut_cond_ids = [r["condition_id"] for r in mut_rows]

    assert set(cond_ids) == set(
        mut_cond_ids
    ), "Mismatch between condition IDs in conditions.csv and mutants_expected.csv"

    mutant_columns = [f"M{i:02d}" for i in range(1, 11)]
    for col in mutant_columns:
        assert (
            col in mut_reader.fieldnames
        ), f"Missing mutant column {col} in mutants_expected.csv"

    # Verify that clean matches expected_clean and each mutant causes at least one FAIL
    cond_map = {r["condition_id"]: r for r in cond_rows}
    mutants_with_failure = {m: 0 for m in mutant_columns}

    valid_verdicts = {"PASS", "FAIL", "ERROR", "UNTESTED"}

    for r in mut_rows:
        cid = r["condition_id"]
        clean_exp = cond_map[cid]["expected_clean"]
        assert (
            r["clean"] == clean_exp
        ), f"Clean verdict mismatch for {cid}: expected {clean_exp}, got {r['clean']}"

        for m in mutant_columns:
            verdict = r[m]
            assert (
                verdict in valid_verdicts
            ), f"Invalid verdict '{verdict}' for {cid} under {m}"
            if verdict == "FAIL":
                mutants_with_failure[m] += 1

    for m, count in mutants_with_failure.items():
        assert (
            count >= 1
        ), f"Mutant {m} has 0 expected FAIL conditions in mutants_expected.csv"
