"""
FRONTLINE — Tests for Triage Engine
Tests core logic without needing API keys: validation, fallback, schema enforcement.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.triage.engine import validate_triage, VALID_CATEGORIES, VALID_PRIORITIES


def test_validate_valid_result():
    """Well-formed result should pass through unchanged."""
    result = {
        "category": "billing",
        "priority": "P1",
        "summary": "Customer was charged twice.",
        "suggested_action": "Initiate refund for duplicate charge.",
        "needs_human": True,
        "confidence": 0.95,
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result.copy())
    assert validated["category"] == "billing"
    assert validated["priority"] == "P1"
    assert validated["needs_human"] is True
    assert validated["confidence"] == 0.95


def test_low_confidence_forces_human():
    """Confidence < 0.6 must set needs_human=True regardless."""
    result = {
        "category": "unclear",
        "priority": "P3",
        "summary": "Unclear message.",
        "suggested_action": "Route to human.",
        "needs_human": False,
        "confidence": 0.4,
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result)
    assert validated["needs_human"] is True, "Low confidence must force needs_human=True"


def test_p0_forces_human():
    """P0 priority must always set needs_human=True."""
    result = {
        "category": "technical_outage",
        "priority": "P0",
        "summary": "Production system is down.",
        "suggested_action": "Escalate immediately.",
        "needs_human": False,  # Even if set to False
        "confidence": 0.99,
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result)
    assert validated["needs_human"] is True, "P0 must always need human"


def test_invalid_category_corrected():
    """Invalid category should be corrected to 'unclear'."""
    result = {
        "category": "invented_category",
        "priority": "P2",
        "summary": "Some issue.",
        "suggested_action": "Check it.",
        "needs_human": False,
        "confidence": 0.85,
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result)
    assert validated["category"] == "unclear"
    assert "invalid_category_corrected" in validated["flags"]


def test_invalid_priority_corrected():
    """Invalid priority should default to P3."""
    result = {
        "category": "general_inquiry",
        "priority": "P99",
        "summary": "Random.",
        "suggested_action": "Do something.",
        "needs_human": False,
        "confidence": 0.9,
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result)
    assert validated["priority"] == "P3"


def test_confidence_clamped():
    """Confidence must be clamped to [0.0, 1.0]."""
    result = {
        "category": "billing",
        "priority": "P1",
        "summary": "Test.",
        "suggested_action": "Test.",
        "needs_human": True,
        "confidence": 999,  # Out of range
        "detected_language": "en",
        "flags": [],
    }
    validated = validate_triage(result)
    assert validated["confidence"] == 1.0


def test_messages_dataset_exists():
    """Dataset file must exist and contain at least 30 messages."""
    path = Path(__file__).parent.parent / "data" / "messages.json"
    assert path.exists(), "messages.json not found"
    with open(path) as f:
        data = json.load(f)
    assert len(data) >= 30, f"Expected ≥30 messages, got {len(data)}"
    for msg in data:
        assert "id" in msg
        assert "text" in msg


def test_ground_truth_exists():
    """Ground truth must exist with at least 10 entries."""
    path = Path(__file__).parent.parent / "evaluation" / "ground_truth.json"
    assert path.exists(), "ground_truth.json not found"
    with open(path) as f:
        data = json.load(f)
    assert len(data) >= 10, f"Expected ≥10 ground truth entries, got {len(data)}"


def test_all_valid_categories():
    """Sanity check: all expected categories are defined."""
    expected = [
        "billing", "order_issue", "technical_bug", "technical_outage",
        "account_support", "security", "feature_request", "general_inquiry",
        "out_of_scope", "adversarial", "unclear", "positive_feedback", "complaint",
    ]
    for cat in expected:
        assert cat in VALID_CATEGORIES, f"'{cat}' missing from VALID_CATEGORIES"


if __name__ == "__main__":
    tests = [
        test_validate_valid_result,
        test_low_confidence_forces_human,
        test_p0_forces_human,
        test_invalid_category_corrected,
        test_invalid_priority_corrected,
        test_confidence_clamped,
        test_messages_dataset_exists,
        test_ground_truth_exists,
        test_all_valid_categories,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed.")
