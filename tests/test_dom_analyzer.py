# Author: Maharshi Soni | License: MIT
"""Tests for dom_analyzer.py functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from bs4 import Tag

from dom_analyzer import (
    compute_structural_similarity,
    extract_fingerprint,
    find_all_elements,
    find_element_by_selector,
    get_element_depth,
    get_element_path,
    get_sibling_index,
    parse_html,
)
from models import ElementFingerprint


SIMPLE_HTML = """
<html>
<body>
  <div id="container" class="wrapper main">
    <h1>Title</h1>
    <p class="intro">Hello world</p>
    <button id="btn" class="btn primary" data-testid="action-btn" name="action">Click Me</button>
    <button class="btn secondary">Cancel</button>
  </div>
</body>
</html>
"""


class TestParseHtml:
    def test_returns_soup(self):
        soup = parse_html(SIMPLE_HTML)
        assert soup is not None
        assert soup.find("button") is not None

    def test_empty_html(self):
        soup = parse_html("")
        assert soup is not None


class TestGetElementDepth:
    def test_body_depth(self):
        soup = parse_html(SIMPLE_HTML)
        body = soup.find("body")
        assert get_element_depth(body) == 1

    def test_nested_depth(self):
        soup = parse_html(SIMPLE_HTML)
        btn = soup.find("button", id="btn")
        # html > body > div > button = depth 3
        assert get_element_depth(btn) == 3


class TestGetElementPath:
    def test_path_for_button(self):
        soup = parse_html(SIMPLE_HTML)
        btn = soup.find("button", id="btn")
        path = get_element_path(btn)
        assert "button" in path
        assert "div" in path

    def test_path_for_body(self):
        soup = parse_html(SIMPLE_HTML)
        body = soup.find("body")
        path = get_element_path(body)
        assert path.startswith("html")


class TestGetSiblingIndex:
    def test_first_button(self):
        soup = parse_html(SIMPLE_HTML)
        btn = soup.find("button", id="btn")
        assert get_sibling_index(btn) == 0

    def test_second_button(self):
        soup = parse_html(SIMPLE_HTML)
        buttons = soup.find_all("button")
        assert get_sibling_index(buttons[1]) == 1


class TestExtractFingerprint:
    def test_basic_fingerprint(self):
        soup = parse_html(SIMPLE_HTML)
        btn = soup.find("button", id="btn")
        fp = extract_fingerprint(btn)
        assert fp.tag == "button"
        assert fp.element_id == "btn"
        assert "btn" in fp.classes
        assert "primary" in fp.classes
        assert fp.text_content == "Click Me"
        assert fp.attributes.get("data-testid") == "action-btn"
        assert fp.parent_tag == "div"
        assert fp.parent_id == "container"

    def test_element_without_id(self):
        soup = parse_html(SIMPLE_HTML)
        p = soup.find("p", class_="intro")
        fp = extract_fingerprint(p)
        assert fp.tag == "p"
        assert fp.element_id == ""
        assert "intro" in fp.classes
        assert fp.text_content == "Hello world"

    def test_long_text_truncated(self):
        long_text = "A" * 300
        html = f"<div><p>{long_text}</p></div>"
        soup = parse_html(html)
        p = soup.find("p")
        fp = extract_fingerprint(p)
        assert len(fp.text_content) == 200


class TestFindAllElements:
    def test_finds_elements(self):
        soup = parse_html(SIMPLE_HTML)
        elements = find_all_elements(soup)
        tags = [e.name for e in elements]
        assert "button" in tags
        assert "div" in tags
        assert "h1" in tags

    def test_count(self):
        soup = parse_html(SIMPLE_HTML)
        elements = find_all_elements(soup)
        # html, body, div, h1, p, button, button = 7
        assert len(elements) >= 7


class TestFindElementBySelector:
    def test_css_id(self):
        soup = parse_html(SIMPLE_HTML)
        elem = find_element_by_selector(soup, "#btn")
        assert elem is not None
        assert elem.name == "button"

    def test_css_class(self):
        soup = parse_html(SIMPLE_HTML)
        elem = find_element_by_selector(soup, ".intro")
        assert elem is not None
        assert elem.name == "p"

    def test_css_attribute(self):
        soup = parse_html(SIMPLE_HTML)
        elem = find_element_by_selector(soup, '[data-testid="action-btn"]')
        assert elem is not None
        assert elem.name == "button"

    def test_xpath_simple(self):
        soup = parse_html(SIMPLE_HTML)
        elem = find_element_by_selector(soup, '//button[@id="btn"]')
        assert elem is not None
        assert elem.name == "button"

    def test_not_found(self):
        soup = parse_html(SIMPLE_HTML)
        elem = find_element_by_selector(soup, "#nonexistent")
        assert elem is None


class TestComputeStructuralSimilarity:
    def test_identical_fingerprints(self):
        fp = ElementFingerprint(
            tag="button",
            element_id="btn",
            classes=["primary"],
            attributes={"type": "submit"},
            text_content="Click",
            parent_tag="div",
            parent_id="form",
            depth=3,
            sibling_index=0,
        )
        sim = compute_structural_similarity(fp, fp)
        assert sim >= 0.9

    def test_completely_different(self):
        fp1 = ElementFingerprint(
            tag="button", element_id="btn", classes=["primary"],
            text_content="Click", parent_tag="div", depth=3,
        )
        fp2 = ElementFingerprint(
            tag="span", element_id="", classes=["badge"],
            text_content="New", parent_tag="li", depth=1,
        )
        sim = compute_structural_similarity(fp1, fp2)
        assert sim < 0.5

    def test_partially_similar(self):
        fp1 = ElementFingerprint(
            tag="button", element_id="old-btn", classes=["btn", "primary"],
            text_content="Submit", parent_tag="form", depth=3,
        )
        fp2 = ElementFingerprint(
            tag="button", element_id="new-btn", classes=["btn", "accent"],
            text_content="Submit", parent_tag="form", depth=3,
        )
        sim = compute_structural_similarity(fp1, fp2)
        assert 0.3 < sim < 0.9

    def test_score_in_range(self):
        fp1 = ElementFingerprint(tag="div")
        fp2 = ElementFingerprint(tag="span")
        sim = compute_structural_similarity(fp1, fp2)
        assert 0.0 <= sim <= 1.0
