# Author: Maharshi Soni | License: MIT
"""CLI entry point for the Self-Healing Locator Engine.

Examples::

    # Heal a broken selector using an HTML file
    python main.py --selector "#login-btn" --html-file page.html

    # Heal with inline HTML (piped)
    echo "<html>...</html>" | python main.py --selector ".my-class" --html-stdin

    # Run the built-in demo with synthetic HTML
    python main.py --demo

    # Output as JSON
    python main.py --selector "#login-btn" --html-file page.html --json

    # Disable ML strategy for speed
    python main.py --selector "#login-btn" --html-file page.html --no-ml
"""

import argparse
import json
import sys
from pathlib import Path

from dom_analyzer import extract_fingerprint, find_element_by_selector, parse_html
from locator_engine import SelfHealingLocatorEngine
from models import ElementFingerprint
from utils import (
    format_result_json,
    format_result_table,
    get_sample_html_after,
    get_sample_html_before,
)


def run_demo() -> None:
    """Run a built-in demo with synthetic before/after HTML pages."""
    print()
    print("=" * 78)
    print("  SELF-HEALING LOCATOR ENGINE -- DEMO")
    print("  Demonstrating automatic selector healing on synthetic HTML")
    print("=" * 78)
    print()

    html_before = get_sample_html_before()
    html_after = get_sample_html_after()

    soup_before = parse_html(html_before)
    engine = SelfHealingLocatorEngine()

    broken_selectors = [
        "#login-btn",
        "#search-box",
        "#signup-btn",
        "#get-started-btn",
        ".feature-card[data-testid='feature-1']",
        "#contact-form",
    ]

    for selector in broken_selectors:
        # Build reference fingerprint from old HTML
        elem = find_element_by_selector(soup_before, selector)
        ref_fp = extract_fingerprint(elem) if elem else None

        result = engine.heal(selector, html_after, reference_fingerprint=ref_fp)
        print(format_result_table(result.to_dict()))
        print()


def run_heal(
    selector: str,
    html: str,
    output_json: bool = False,
    enable_ml: bool = True,
    ref_html: str = "",
) -> None:
    """Run the healing engine on the given selector and HTML."""
    engine = SelfHealingLocatorEngine(enable_ml=enable_ml)

    # If reference HTML is provided, extract fingerprint from it
    ref_fp = None
    if ref_html:
        soup_ref = parse_html(ref_html)
        elem = find_element_by_selector(soup_ref, selector)
        if elem:
            ref_fp = extract_fingerprint(elem)

    result = engine.heal(selector, html, reference_fingerprint=ref_fp)

    if output_json:
        print(format_result_json(result.to_dict()))
    else:
        print(format_result_table(result.to_dict()))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="self-healing-locator-engine",
        description=(
            "Self-Healing Locator Engine: automatically find alternative "
            "selectors when UI automation tests break."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --demo\n"
            '  python main.py --selector "#login-btn" --html-file page.html\n'
            '  python main.py --selector ".btn-primary" --html-file page.html --json\n'
            '  python main.py --selector "#old-id" --html-file new.html --ref-html-file old.html\n'
        ),
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the built-in demo with synthetic HTML data.",
    )
    parser.add_argument(
        "--selector", "-s",
        type=str,
        help="The broken CSS or XPath selector to heal.",
    )
    parser.add_argument(
        "--html-file", "-f",
        type=str,
        help="Path to an HTML file containing the current page.",
    )
    parser.add_argument(
        "--html-stdin",
        action="store_true",
        help="Read HTML from stdin instead of a file.",
    )
    parser.add_argument(
        "--ref-html-file",
        type=str,
        help="Path to a reference HTML file (original page before changes) "
             "for more accurate fingerprinting.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output result as JSON.",
    )
    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable the ML classification strategy for faster execution.",
    )

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.selector:
        parser.error("--selector is required (or use --demo)")

    # Load HTML
    html = ""
    if args.html_stdin:
        html = sys.stdin.read()
    elif args.html_file:
        path = Path(args.html_file)
        if not path.exists():
            print(f"Error: file not found: {args.html_file}", file=sys.stderr)
            sys.exit(1)
        html = path.read_text(encoding="utf-8")
    else:
        parser.error("Provide --html-file or --html-stdin")

    # Load reference HTML (optional)
    ref_html = ""
    if args.ref_html_file:
        ref_path = Path(args.ref_html_file)
        if ref_path.exists():
            ref_html = ref_path.read_text(encoding="utf-8")

    run_heal(
        selector=args.selector,
        html=html,
        output_json=args.output_json,
        enable_ml=not args.no_ml,
        ref_html=ref_html,
    )


if __name__ == "__main__":
    main()
