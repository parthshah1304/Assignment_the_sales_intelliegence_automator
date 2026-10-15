import pytest
from app.analyzer.llm_client import enforce_evidence_grounding

SAMPLE_TEXT = """
Lone Star Roofing is a premier commercial roofing contractor in Houston TX.
We install and repair flat roofs for warehouses, office parks and property managers across Harris County.
Our crews handle TPO, EPDM and metal roof systems with 24/7 emergency response for facility managers.
"""

def test_enforce_evidence_keeps_valid_quotes():
    brief = {
        "b2b_decision": "Yes",
        "confidence": "high",
        "b2b_confidence": 90.0,
        "evidence": ["flat roofs for warehouses, office parks and property managers"],
        "validation_flags": []
    }
    grounded = enforce_evidence_grounding(brief, SAMPLE_TEXT)
    assert grounded["b2b_decision"] == "Yes"
    assert len(grounded["evidence"]) == 1

def test_enforce_evidence_downgrades_hallucinated_quotes():
    brief = {
        "b2b_decision": "Yes",
        "confidence": "high",
        "b2b_confidence": 90.0,
        "b2b_reasoning": "Serves Fortune 500 tech companies.",
        "evidence": ["We proudly serve Fortune 500 aerospace companies in New York"],
        "validation_flags": []
    }
    grounded = enforce_evidence_grounding(brief, SAMPLE_TEXT)
    # The quote does not appear in SAMPLE_TEXT, so it must be discarded and downgraded to No
    assert grounded["b2b_decision"] == "No"
    assert grounded["confidence"] == "low"
    assert grounded["needs_review"] is True
    assert any("downgraded" in flag.lower() for flag in grounded["validation_flags"])

def test_enforce_evidence_empty_content():
    brief = {
        "b2b_decision": "No",
        "confidence": "high",
        "b2b_confidence": 80.0,
        "evidence": [],
        "validation_flags": []
    }
    grounded = enforce_evidence_grounding(brief, "")
    assert grounded["confidence"] == "low"
    assert grounded["needs_review"] is True
