# Author: Maharshi Soni | License: MIT
"""Tests for locator_engine.py -- the main orchestrator."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from dom_analyzer import extract_fingerprint, find_element_by_selector, parse_html
from locator_engine import SelfHealingLocatorEngine, _merge_candidates
from models import CandidateLocator, HealingResult, LocatorType, StrategyName
from utils import get_sample_html_after, get_sample_html_before


@pytest.fixture
def engine():
    return SelfHealingLocatorEngine()


@pytest.fixture
def engine_no_ml():
    return SelfHealingLocatorEngine(enable_ml=False)


@pytest.fixture
def html_before():
    return get_sample_html_before()


@pytest.fixture
def html_after():
    return get_sample_html_after()


class TestMergeCandidates:
    def test_deduplicates(self):
        cands = {
            "dom_similarity": [
                CandidateLocator(LocatorType.CSS, "#btn", 0.9, StrategyName.DOM_SIMILARITY),
            ],
            "attribute_fuzzy": [
                CandidateLocator(LocatorType.CSS, "#btn", 0.8, StrategyName.ATTRIBUTE_FUZZY),
            ],
        }
        weights = {"dom_similarity": 0.5, "attribute_fuzzy": 0.5}
        merged = _merge_candidates(cands, weights, top_n=5)
        # #btn should appear only once
        values = [c.value for c in merged]
        assert values.count("#btn") == 1

    def test_combined_score_higher(self):
        cands = {
            "dom_similarity": [
                CandidateLocator(LocatorType.CSS, "#btn", 0.8, StrategyName.DOM_SIMILARITY),
                CandidateLocator(LocatorType.CSS, "#other", 0.6, StrategyName.DOM_SIMILARITY),
            ],
            "attribute_fuzzy": [
                CandidateLocator(LocatorType.CSS, "#btn", 0.7, StrategyName.ATTRIBUTE_FUZZY),
            ],
        }
        weights = {"dom_similarity": 0.5, "attribute_fuzzy": 0.5}
        merged = _merge_candidates(cands, weights, top_n=5)
        # #btn gets contributions from both strategies, should rank first
        assert merged[0].value == "#btn"

    def test_empty_candidates(self):
        merged = _merge_candidates({}, {}, top_n=5)
        assert merged == []

    def test_respects_top_n(self):
        cands = {
            "dom_similarity": [
                CandidateLocator(LocatorType.CSS, f"#btn{i}", 0.5, StrategyName.DOM_SIMILARITY)
                for i in range(20)
            ],
        }
        merged = _merge_candidates(cands, {"dom_similarity": 1.0}, top_n=3)
        assert len(merged) == 3


class TestSelfHealingLocatorEngine:
    def test_heal_returns_result(self, engine, html_after):
        result = engine.heal("#login-btn", html_after)
        assert isinstance(result, HealingResult)
        assert result.original_selector == "#login-btn"
        assert result.page_element_count > 0
        assert len(result.strategies_used) > 0

    def test_heal_finds_candidates(self, engine, html_before, html_after):
        soup_before = parse_html(html_before)
        elem = find_element_by_selector(soup_before, "#login-btn")
        ref_fp = extract_fingerprint(elem)

        result = engine.heal("#login-btn", html_after, reference_fingerprint=ref_fp)
        assert len(result.candidates) > 0
        assert result.best_candidate is not None

    def test_heal_login_btn(self, engine, html_before, html_after):
        """#login-btn was renamed to #auth-login-btn."""
        soup = parse_html(html_before)
        elem = find_element_by_selector(soup, "#login-btn")
        ref_fp = extract_fingerprint(elem)

        result = engine.heal("#login-btn", html_after, reference_fingerprint=ref_fp)
        best = result.best_candidate
        assert best is not None
        assert best.confidence > 0.3
        # The best candidate should reference the login button
        candidate_values = [c.value for c in result.candidates]
        assert any("login" in v.lower() or "auth" in v.lower() for v in candidate_values)

    def test_heal_search_box(self, engine, html_before, html_after):
        """#search-box was renamed to #global-search."""
        soup = parse_html(html_before)
        elem = find_element_by_selector(soup, "#search-box")
        ref_fp = extract_fingerprint(elem)

        result = engine.heal("#search-box", html_after, reference_fingerprint=ref_fp)
        assert result.best_candidate is not None
        candidate_values = [c.value for c in result.candidates]
        assert any("search" in v.lower() for v in candidate_values)

    def test_heal_without_reference(self, engine, html_after):
        """Engine should still work without a pre-computed reference fingerprint."""
        result = engine.heal("#login-btn", html_after)
        assert isinstance(result, HealingResult)
        # May or may not find candidates, but should not crash
        assert result.page_element_count > 0

    def test_heal_no_ml(self, engine_no_ml, html_after):
        result = engine_no_ml.heal("#login-btn", html_after)
        assert "ml_classification" not in result.strategies_used

    def test_heal_json(self, engine, html_after):
        json_str = engine.heal_json("#login-btn", html_after)
        parsed = json.loads(json_str)
        assert "original_selector" in parsed
        assert "candidates" in parsed
        assert "best_candidate" in parsed

    def test_infer_fingerprint_id(self, engine, html_after):
        soup = parse_html(html_after)
        fp = engine._infer_fingerprint("#some-id", soup)
        assert fp.element_id == "some-id"

    def test_infer_fingerprint_classes(self, engine, html_after):
        soup = parse_html(html_after)
        fp = engine._infer_fingerprint("div.cls1.cls2", soup)
        assert "cls1" in fp.classes
        assert "cls2" in fp.classes
        assert fp.tag == "div"

    def test_infer_fingerprint_xpath(self, engine, html_after):
        soup = parse_html(html_after)
        fp = engine._infer_fingerprint('//button[@id="login"]', soup)
        assert fp.tag == "button"
        assert fp.element_id == "login"

    def test_infer_fingerprint_attribute(self, engine, html_after):
        soup = parse_html(html_after)
        fp = engine._infer_fingerprint('button[data-testid="login-button"]', soup)
        assert fp.attributes.get("data-testid") == "login-button"

    def test_custom_weights(self, html_after):
        custom = {"dom_similarity": 1.0, "attribute_fuzzy": 0.0}
        engine = SelfHealingLocatorEngine(weights=custom)
        result = engine.heal("#login-btn", html_after)
        assert isinstance(result, HealingResult)

    def test_heal_contact_form(self, engine, html_before, html_after):
        """#contact-form was renamed to #inquiry-form."""
        soup = parse_html(html_before)
        elem = find_element_by_selector(soup, "#contact-form")
        ref_fp = extract_fingerprint(elem)

        result = engine.heal("#contact-form", html_after, reference_fingerprint=ref_fp)
        assert result.best_candidate is not None
        candidate_values = [c.value for c in result.candidates]
        assert any("form" in v.lower() or "inquiry" in v.lower() for v in candidate_values)
