# Author: Maharshi Soni | License: MIT
"""Playwright integration examples for the Self-Healing Locator Engine.

This module shows how to wrap Playwright page actions so that broken
selectors are automatically healed at runtime.  Playwright is an *optional*
dependency -- the rest of the engine works without it.

Usage example (requires ``playwright`` to be installed)::

    from playwright.sync_api import sync_playwright
    from playwright_integration import SelfHealingPage

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com")

        healer = SelfHealingPage(page)
        # This will auto-heal if "#old-btn" no longer exists:
        healer.click("#old-btn")
        browser.close()

If Playwright is not installed, calling ``SelfHealingPage`` will raise a
clear error message.  The rest of the project's functionality (CLI, library
API) does not depend on this module.
"""

from typing import Any, Dict, List, Optional

from locator_engine import SelfHealingLocatorEngine
from models import CandidateLocator, HealingResult


def _require_playwright():
    """Raise a helpful error if playwright is not installed."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        raise ImportError(
            "Playwright is required for browser integration. "
            "Install it with: pip install playwright && python -m playwright install"
        )


class SelfHealingPage:
    """A wrapper around a Playwright ``Page`` that auto-heals broken selectors.

    When an action (click, fill, etc.) fails because the selector does not
    match any element, the engine fetches the current page HTML, runs the
    healing pipeline, and retries with the best alternative selector.

    Attributes:
        page: The underlying Playwright Page object.
        engine: The locator engine instance.
        healing_log: List of healing events that occurred during the session.
    """

    def __init__(self, page: Any, enable_ml: bool = True, timeout: int = 3000):
        _require_playwright()
        self.page = page
        self.engine = SelfHealingLocatorEngine(enable_ml=enable_ml)
        self.timeout = timeout
        self.healing_log: List[Dict[str, Any]] = []

    def _try_selector(self, selector: str) -> bool:
        """Return True if the selector matches at least one visible element."""
        try:
            locator = self.page.locator(selector)
            locator.wait_for(state="visible", timeout=self.timeout)
            return True
        except Exception:
            return False

    def _heal(self, broken_selector: str) -> Optional[CandidateLocator]:
        """Run the healing pipeline and return the best candidate."""
        html = self.page.content()
        result: HealingResult = self.engine.heal(broken_selector, html)

        if result.best_candidate:
            self.healing_log.append({
                "original": broken_selector,
                "healed": result.best_candidate.value,
                "confidence": result.best_candidate.confidence,
                "strategy": result.best_candidate.strategy.value,
            })
        return result.best_candidate

    def _resolve_selector(self, selector: str) -> str:
        """Return *selector* if it works, otherwise heal and return the alternative."""
        if self._try_selector(selector):
            return selector
        candidate = self._heal(selector)
        if candidate:
            print(
                f"[SelfHeal] Selector healed: '{selector}' -> '{candidate.value}' "
                f"(confidence={candidate.confidence:.2%}, strategy={candidate.strategy.value})"
            )
            return candidate.value
        raise ValueError(
            f"Could not heal selector '{selector}'. "
            "No suitable alternative found on the current page."
        )

    # ---- Wrapped Playwright actions ----

    def click(self, selector: str, **kwargs: Any) -> None:
        """Click an element, auto-healing the selector if necessary."""
        resolved = self._resolve_selector(selector)
        self.page.locator(resolved).click(**kwargs)

    def fill(self, selector: str, value: str, **kwargs: Any) -> None:
        """Fill an input element, auto-healing the selector if necessary."""
        resolved = self._resolve_selector(selector)
        self.page.locator(resolved).fill(value, **kwargs)

    def type(self, selector: str, text: str, **kwargs: Any) -> None:
        """Type into an element, auto-healing the selector if necessary."""
        resolved = self._resolve_selector(selector)
        self.page.locator(resolved).type(text, **kwargs)

    def inner_text(self, selector: str) -> str:
        """Get the inner text of an element, auto-healing if necessary."""
        resolved = self._resolve_selector(selector)
        return self.page.locator(resolved).inner_text()

    def is_visible(self, selector: str) -> bool:
        """Check if an element is visible, auto-healing if necessary."""
        resolved = self._resolve_selector(selector)
        return self.page.locator(resolved).is_visible()

    def get_attribute(self, selector: str, name: str) -> Optional[str]:
        """Get an attribute value, auto-healing if necessary."""
        resolved = self._resolve_selector(selector)
        return self.page.locator(resolved).get_attribute(name)

    def wait_for(self, selector: str, **kwargs: Any) -> None:
        """Wait for an element, auto-healing if necessary."""
        resolved = self._resolve_selector(selector)
        self.page.locator(resolved).wait_for(**kwargs)

    def get_healing_report(self) -> List[Dict[str, Any]]:
        """Return a summary of all healing events during this session."""
        return list(self.healing_log)


# ---------------------------------------------------------------------------
# Standalone demo (does NOT require a running browser)
# ---------------------------------------------------------------------------

def demo_integration_concept() -> None:
    """Print a demonstration of how the integration would work.

    This demo uses synthetic HTML and does *not* launch a browser.
    """
    from utils import get_sample_html_before, get_sample_html_after, format_result_table

    print("=" * 70)
    print("PLAYWRIGHT INTEGRATION DEMO (concept -- no browser required)")
    print("=" * 70)
    print()
    print("Scenario: Your Playwright test uses these selectors from v1:")
    print("  - #login-btn")
    print("  - #search-box")
    print("  - #signup-btn")
    print()
    print("The app was updated to v2 and those selectors broke.")
    print("The Self-Healing Engine finds alternatives automatically:")
    print()

    engine = SelfHealingLocatorEngine()
    html_after = get_sample_html_after()

    # Build reference fingerprints from the old HTML
    from dom_analyzer import parse_html, find_element_by_selector, extract_fingerprint

    html_before = get_sample_html_before()
    soup_before = parse_html(html_before)

    broken_selectors = ["#login-btn", "#search-box", "#signup-btn"]
    for sel in broken_selectors:
        elem = find_element_by_selector(soup_before, sel)
        ref_fp = extract_fingerprint(elem) if elem else None
        result = engine.heal(sel, html_after, reference_fingerprint=ref_fp)
        print(format_result_table(result.to_dict()))
        print()


if __name__ == "__main__":
    demo_integration_concept()
