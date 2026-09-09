# Author: Maharshi Soni | License: MIT
"""Tests for utils.py helper functions."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from bs4 import BeautifulSoup

from dom_analyzer import find_element_by_selector, parse_html
from utils import (
    format_result_json,
    format_result_table,
    get_sample_html_after,
    get_sample_html_before,
)


class TestGetSampleHtmlBefore:
    def test_returns_string(self):
        html = get_sample_html_before()
        assert isinstance(html, str)
        assert len(html) > 100

    def test_parseable(self):
        soup = parse_html(get_sample_html_before())
        assert soup.find("button", id="login-btn") is not None

    def test_contains_expected_elements(self):
        soup = parse_html(get_sample_html_before())
        assert soup.find("input", id="search-box") is not None
        assert soup.find("button", id="signup-btn") is not None
        assert soup.find("button", id="get-started-btn") is not None
        assert soup.find("form", id="contact-form") is not None
        assert soup.find("nav", attrs={"data-testid": "nav-menu"}) is not None


class TestGetSampleHtmlAfter:
    def test_returns_string(self):
        html = get_sample_html_after()
        assert isinstance(html, str)
        assert len(html) > 100

    def test_parseable(self):
        soup = parse_html(get_sample_html_after())
        assert soup.find("body") is not None

    def test_old_selectors_broken(self):
        soup = parse_html(get_sample_html_after())
        # These selectors from v1 should NOT exist in v2
        assert soup.find("button", id="login-btn") is None
        assert soup.find("input", id="search-box") is None
        assert soup.find("button", id="signup-btn") is None

    def test_new_selectors_exist(self):
        soup = parse_html(get_sample_html_after())
        assert soup.find("button", id="auth-login-btn") is not None
        assert soup.find("input", id="global-search") is not None
        assert soup.find("button", id="register-btn") is not None


class TestFormatResultTable:
    def test_basic_output(self):
        result = {
            "original_selector": "#test",
            "page_element_count": 10,
            "strategies_used": ["dom_similarity"],
            "best_candidate": {
                "value": "#found",
                "locator_type": "css",
                "confidence": 0.85,
                "strategy": "dom_similarity",
                "explanation": "Good match",
            },
            "candidates": [
                {
                    "value": "#found",
                    "locator_type": "css",
                    "confidence": 0.85,
                    "strategy": "dom_similarity",
                    "explanation": "Good match",
                }
            ],
        }
        output = format_result_table(result)
        assert "#test" in output
        assert "#found" in output
        assert "85.00%" in output
        assert "BEST MATCH" in output

    def test_no_candidates(self):
        result = {
            "original_selector": "#missing",
            "page_element_count": 5,
            "strategies_used": [],
            "best_candidate": None,
            "candidates": [],
        }
        output = format_result_table(result)
        assert "none found" in output.lower()
        assert "ALL CANDIDATES (0)" in output


class TestFormatResultJson:
    def test_valid_json(self):
        result = {"key": "value", "number": 42}
        output = format_result_json(result)
        parsed = json.loads(output)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_indent(self):
        result = {"a": 1}
        output = format_result_json(result, indent=4)
        assert "    " in output  # 4-space indent
