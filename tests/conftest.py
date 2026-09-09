# Author: Maharshi Soni | License: MIT
"""Shared fixtures for pytest."""

import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so imports work without installation.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dom_analyzer import extract_fingerprint, find_element_by_selector, parse_html
from utils import get_sample_html_before, get_sample_html_after


@pytest.fixture
def html_before() -> str:
    """Return the synthetic 'before' HTML page."""
    return get_sample_html_before()


@pytest.fixture
def html_after() -> str:
    """Return the synthetic 'after' HTML page."""
    return get_sample_html_after()


@pytest.fixture
def soup_before(html_before):
    return parse_html(html_before)


@pytest.fixture
def soup_after(html_after):
    return parse_html(html_after)


@pytest.fixture
def login_btn_fingerprint(soup_before):
    """Fingerprint of #login-btn from the v1 page."""
    elem = find_element_by_selector(soup_before, "#login-btn")
    assert elem is not None
    return extract_fingerprint(elem)


@pytest.fixture
def search_box_fingerprint(soup_before):
    """Fingerprint of #search-box from the v1 page."""
    elem = find_element_by_selector(soup_before, "#search-box")
    assert elem is not None
    return extract_fingerprint(elem)
