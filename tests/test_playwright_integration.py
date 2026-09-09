# Author: Maharshi Soni | License: MIT
"""Tests for playwright_integration.py (concept-level, no browser needed)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from playwright_integration import demo_integration_concept


class TestDemoIntegrationConcept:
    def test_demo_runs_without_error(self, capsys):
        """The concept demo should print output without raising exceptions."""
        demo_integration_concept()
        captured = capsys.readouterr()
        assert "PLAYWRIGHT INTEGRATION DEMO" in captured.out
        assert "Selector healed" in captured.out or "BEST MATCH" in captured.out

    def test_demo_covers_multiple_selectors(self, capsys):
        demo_integration_concept()
        captured = capsys.readouterr()
        assert "#login-btn" in captured.out
        assert "#search-box" in captured.out
        assert "#signup-btn" in captured.out
