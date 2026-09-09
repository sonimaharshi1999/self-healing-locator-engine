# Author: Maharshi Soni | License: MIT
"""Tests for models.py data classes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    CandidateLocator,
    ElementFingerprint,
    HealingResult,
    LocatorType,
    StrategyName,
)


class TestElementFingerprint:
    def test_default_values(self):
        fp = ElementFingerprint()
        assert fp.tag == ""
        assert fp.element_id == ""
        assert fp.classes == []
        assert fp.attributes == {}
        assert fp.text_content == ""
        assert fp.depth == 0

    def test_to_feature_dict(self):
        fp = ElementFingerprint(
            tag="button",
            element_id="submit",
            classes=["btn", "primary"],
            attributes={"type": "submit", "data-testid": "submit-btn"},
            text_content="Submit",
            depth=3,
        )
        fd = fp.to_feature_dict()
        assert fd["tag"] == "button"
        assert fd["has_id"] == 1
        assert fd["class_count"] == 2
        assert fd["attr_count"] == 2
        assert fd["text_length"] == 6
        assert fd["depth"] == 3

    def test_to_feature_dict_empty(self):
        fp = ElementFingerprint()
        fd = fp.to_feature_dict()
        assert fd["has_id"] == 0
        assert fd["class_count"] == 0
        assert fd["attr_count"] == 0
        assert fd["text_length"] == 0


class TestCandidateLocator:
    def test_to_dict(self):
        cand = CandidateLocator(
            locator_type=LocatorType.CSS,
            value="#my-btn",
            confidence=0.9512,
            strategy=StrategyName.DOM_SIMILARITY,
            explanation="High match",
        )
        d = cand.to_dict()
        assert d["locator_type"] == "css"
        assert d["value"] == "#my-btn"
        assert d["confidence"] == 0.9512
        assert d["strategy"] == "dom_similarity"
        assert d["explanation"] == "High match"

    def test_confidence_rounding(self):
        cand = CandidateLocator(
            locator_type=LocatorType.XPATH,
            value="//div",
            confidence=0.123456789,
            strategy=StrategyName.ATTRIBUTE_FUZZY,
        )
        d = cand.to_dict()
        assert d["confidence"] == 0.1235


class TestHealingResult:
    def test_to_dict_empty(self):
        result = HealingResult(original_selector="#gone")
        d = result.to_dict()
        assert d["original_selector"] == "#gone"
        assert d["best_candidate"] is None
        assert d["candidates"] == []
        assert d["page_element_count"] == 0

    def test_to_dict_with_candidates(self):
        best = CandidateLocator(
            locator_type=LocatorType.CSS,
            value="#found",
            confidence=0.85,
            strategy=StrategyName.ML_CLASSIFICATION,
        )
        result = HealingResult(
            original_selector="#missing",
            candidates=[best],
            best_candidate=best,
            page_element_count=42,
            strategies_used=["dom_similarity", "ml_classification"],
        )
        d = result.to_dict()
        assert d["best_candidate"]["value"] == "#found"
        assert len(d["candidates"]) == 1
        assert d["page_element_count"] == 42


class TestEnums:
    def test_locator_type_values(self):
        assert LocatorType.CSS.value == "css"
        assert LocatorType.XPATH.value == "xpath"
        assert LocatorType.ID.value == "id"

    def test_strategy_name_values(self):
        assert StrategyName.DOM_SIMILARITY.value == "dom_similarity"
        assert StrategyName.ML_CLASSIFICATION.value == "ml_classification"
