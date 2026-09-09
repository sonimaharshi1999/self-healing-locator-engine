# Author: Maharshi Soni | License: MIT
"""Tests for strategies.py healing strategies."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from dom_analyzer import extract_fingerprint, find_element_by_selector, parse_html
from models import ElementFingerprint, LocatorType, StrategyName
from strategies import (
    _build_css_selector,
    _build_xpath,
    attribute_fuzzy_strategy,
    dom_similarity_strategy,
    structural_position_strategy,
    text_content_strategy,
)


SAMPLE_HTML = """
<html><body>
<div id="app">
  <nav class="nav-bar">
    <a href="/" id="home" class="link active">Home</a>
    <a href="/about" class="link">About</a>
  </nav>
  <main>
    <button id="submit-btn" class="btn primary" data-testid="submit">Submit Form</button>
    <button class="btn secondary" data-testid="cancel">Cancel</button>
    <input type="text" id="username" class="input-field" name="user" placeholder="Username" />
    <p class="message">Welcome back, user!</p>
  </main>
</div>
</body></html>
"""


@pytest.fixture
def soup():
    return parse_html(SAMPLE_HTML)


@pytest.fixture
def submit_btn_fp(soup):
    elem = find_element_by_selector(soup, "#submit-btn")
    return extract_fingerprint(elem)


@pytest.fixture
def username_fp(soup):
    elem = find_element_by_selector(soup, "#username")
    return extract_fingerprint(elem)


# --- _build_css_selector ---

class TestBuildCssSelector:
    def test_id_selector(self, soup):
        elem = soup.find("button", id="submit-btn")
        assert _build_css_selector(elem) == "#submit-btn"

    def test_class_selector(self, soup):
        elem = soup.find("p", class_="message")
        assert _build_css_selector(elem) == "p.message"

    def test_data_attr_fallback(self, soup):
        elem = soup.find("button", attrs={"data-testid": "cancel"})
        sel = _build_css_selector(elem)
        # Should use class since it has classes
        assert "btn" in sel or "cancel" in sel


# --- _build_xpath ---

class TestBuildXpath:
    def test_id_xpath(self, soup):
        elem = soup.find("button", id="submit-btn")
        xpath = _build_xpath(elem)
        assert xpath == '//button[@id="submit-btn"]'

    def test_data_testid_xpath(self, soup):
        elem = soup.find("button", attrs={"data-testid": "cancel"})
        xpath = _build_xpath(elem)
        assert "cancel" in xpath


# --- dom_similarity_strategy ---

class TestDomSimilarityStrategy:
    def test_returns_candidates(self, submit_btn_fp, soup):
        candidates = dom_similarity_strategy(submit_btn_fp, soup, top_n=5)
        assert len(candidates) > 0

    def test_candidates_sorted(self, submit_btn_fp, soup):
        candidates = dom_similarity_strategy(submit_btn_fp, soup, top_n=5)
        confidences = [c.confidence for c in candidates]
        assert confidences == sorted(confidences, reverse=True)

    def test_strategy_label(self, submit_btn_fp, soup):
        candidates = dom_similarity_strategy(submit_btn_fp, soup, top_n=3)
        for c in candidates:
            assert c.strategy == StrategyName.DOM_SIMILARITY

    def test_top_match_is_exact_element(self, submit_btn_fp, soup):
        candidates = dom_similarity_strategy(submit_btn_fp, soup, top_n=1)
        assert candidates[0].value == "#submit-btn"


# --- attribute_fuzzy_strategy ---

class TestAttributeFuzzyStrategy:
    def test_returns_candidates(self, submit_btn_fp, soup):
        candidates = attribute_fuzzy_strategy(submit_btn_fp, soup, top_n=5)
        assert len(candidates) > 0

    def test_finds_similar_attributes(self, soup):
        # Create a reference with slightly different attribute
        ref = ElementFingerprint(
            tag="button",
            element_id="submit-button",  # similar to "submit-btn"
            classes=["btn"],
            attributes={"data-testid": "submit"},
            text_content="Submit Form",
        )
        candidates = attribute_fuzzy_strategy(ref, soup, top_n=5)
        assert len(candidates) > 0
        values = [c.value for c in candidates]
        assert any("submit" in v.lower() for v in values)

    def test_strategy_label(self, submit_btn_fp, soup):
        candidates = attribute_fuzzy_strategy(submit_btn_fp, soup, top_n=3)
        for c in candidates:
            assert c.strategy == StrategyName.ATTRIBUTE_FUZZY


# --- structural_position_strategy ---

class TestStructuralPositionStrategy:
    def test_returns_candidates(self, submit_btn_fp, soup):
        candidates = structural_position_strategy(submit_btn_fp, soup, top_n=5)
        assert len(candidates) > 0

    def test_prefers_same_tag(self, submit_btn_fp, soup):
        candidates = structural_position_strategy(submit_btn_fp, soup, top_n=3)
        # Top candidate should likely be a button
        top_selector = candidates[0].value
        assert "button" in top_selector or "btn" in top_selector or "#submit" in top_selector

    def test_strategy_label(self, submit_btn_fp, soup):
        candidates = structural_position_strategy(submit_btn_fp, soup, top_n=3)
        for c in candidates:
            assert c.strategy == StrategyName.STRUCTURAL_POSITION


# --- text_content_strategy ---

class TestTextContentStrategy:
    def test_returns_candidates(self, submit_btn_fp, soup):
        candidates = text_content_strategy(submit_btn_fp, soup, top_n=5)
        assert len(candidates) > 0

    def test_empty_for_no_text(self, soup):
        ref = ElementFingerprint(tag="div", text_content="")
        candidates = text_content_strategy(ref, soup)
        assert candidates == []

    def test_finds_matching_text(self, soup):
        ref = ElementFingerprint(tag="p", text_content="Welcome back, user!")
        candidates = text_content_strategy(ref, soup, top_n=3)
        assert len(candidates) > 0
        assert candidates[0].confidence > 0.5

    def test_strategy_label(self, submit_btn_fp, soup):
        candidates = text_content_strategy(submit_btn_fp, soup, top_n=3)
        for c in candidates:
            assert c.strategy == StrategyName.TEXT_CONTENT
