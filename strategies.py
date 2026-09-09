# Author: Maharshi Soni | License: MIT
"""Healing strategies that propose alternative locators for broken selectors."""

from difflib import SequenceMatcher
from typing import List

from bs4 import BeautifulSoup, Tag

from dom_analyzer import (
    compute_structural_similarity,
    extract_fingerprint,
    find_all_elements,
)
from models import (
    CandidateLocator,
    ElementFingerprint,
    LocatorType,
    StrategyName,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_css_selector(element: Tag) -> str:
    """Build the most specific CSS selector possible for *element*.

    Preference order: #id, tag.class1.class2, tag[attr=val], tag:nth-of-type.
    """
    eid = element.get("id")
    if eid:
        return f"#{eid}"

    parts: List[str] = [element.name]
    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    if classes:
        parts.append("." + ".".join(classes))
        return "".join(parts)

    # Fallback to a data attribute
    for attr in ("data-testid", "data-test", "data-cy", "name", "aria-label", "role"):
        val = element.get(attr)
        if val:
            return f'{element.name}[{attr}="{val}"]'

    # nth-of-type fallback
    if element.parent:
        same_tag = [
            c for c in element.parent.children if isinstance(c, Tag) and c.name == element.name
        ]
        if len(same_tag) > 1:
            idx = same_tag.index(element) + 1
            return f"{element.name}:nth-of-type({idx})"

    return element.name


def _build_xpath(element: Tag) -> str:
    """Build an XPath expression for *element*."""
    eid = element.get("id")
    if eid:
        return f'//{element.name}[@id="{eid}"]'

    for attr in ("data-testid", "data-test", "data-cy", "name", "aria-label"):
        val = element.get(attr)
        if val:
            return f'//{element.name}[@{attr}="{val}"]'

    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    if classes:
        condition = " and ".join(f'contains(@class, "{c}")' for c in classes)
        return f"//{element.name}[{condition}]"

    text = element.get_text(strip=True)
    if text and len(text) < 60:
        safe = text.replace('"', '\\"')
        return f'//{element.name}[text()="{safe}"]'

    return f"//{element.name}"


# ---------------------------------------------------------------------------
# Strategy 1 -- DOM Similarity Scoring
# ---------------------------------------------------------------------------

def dom_similarity_strategy(
    reference_fp: ElementFingerprint,
    soup: BeautifulSoup,
    top_n: int = 5,
) -> List[CandidateLocator]:
    """Score every element in *soup* against *reference_fp* using structural similarity.

    Args:
        reference_fp: Fingerprint of the element that the broken selector
            was expected to match.
        soup: Parsed HTML document.
        top_n: Maximum number of candidates to return.

    Returns:
        Sorted list of ``CandidateLocator`` instances (highest confidence first).
    """
    candidates: List[CandidateLocator] = []
    elements = find_all_elements(soup)

    for elem in elements:
        fp = extract_fingerprint(elem)
        sim = compute_structural_similarity(reference_fp, fp)
        if sim < 0.15:
            continue
        selector = _build_css_selector(elem)
        candidates.append(
            CandidateLocator(
                locator_type=LocatorType.CSS,
                value=selector,
                confidence=sim,
                strategy=StrategyName.DOM_SIMILARITY,
                explanation=f"Structural similarity {sim:.2%} with tag={fp.tag}, depth={fp.depth}",
            )
        )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Strategy 2 -- Attribute Fuzzy Matching
# ---------------------------------------------------------------------------

def attribute_fuzzy_strategy(
    reference_fp: ElementFingerprint,
    soup: BeautifulSoup,
    top_n: int = 5,
    threshold: float = 0.30,
) -> List[CandidateLocator]:
    """Find elements whose attributes are fuzzy-matches to *reference_fp*.

    Uses ``difflib.SequenceMatcher`` on attribute values and element text.

    Args:
        reference_fp: Reference fingerprint.
        soup: Parsed document.
        top_n: Max candidates.
        threshold: Minimum similarity ratio to consider.

    Returns:
        Sorted list of ``CandidateLocator`` instances.
    """
    candidates: List[CandidateLocator] = []
    elements = find_all_elements(soup)

    ref_attrs = dict(reference_fp.attributes)
    if reference_fp.element_id:
        ref_attrs["id"] = reference_fp.element_id
    if reference_fp.classes:
        ref_attrs["class"] = " ".join(reference_fp.classes)

    for elem in elements:
        best_ratio = 0.0
        matched_attr = ""

        # Compare attributes
        for ref_key, ref_val in ref_attrs.items():
            for attr_key, attr_val in elem.attrs.items():
                if isinstance(attr_val, list):
                    attr_val = " ".join(attr_val)
                key_ratio = SequenceMatcher(None, ref_key, attr_key).ratio()
                val_ratio = SequenceMatcher(None, str(ref_val), str(attr_val)).ratio()
                combined = 0.3 * key_ratio + 0.7 * val_ratio
                if combined > best_ratio:
                    best_ratio = combined
                    matched_attr = f"{attr_key}={attr_val}"

        # Compare text content
        if reference_fp.text_content:
            elem_text = elem.get_text(strip=True)
            if elem_text:
                text_ratio = SequenceMatcher(
                    None,
                    reference_fp.text_content.lower(),
                    elem_text.lower(),
                ).ratio()
                if text_ratio > best_ratio:
                    best_ratio = text_ratio
                    matched_attr = f"text={elem_text[:50]}"

        if best_ratio >= threshold:
            selector = _build_css_selector(elem)
            candidates.append(
                CandidateLocator(
                    locator_type=LocatorType.CSS,
                    value=selector,
                    confidence=best_ratio,
                    strategy=StrategyName.ATTRIBUTE_FUZZY,
                    explanation=f"Best fuzzy match {best_ratio:.2%} on {matched_attr}",
                )
            )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Strategy 3 -- Structural Position
# ---------------------------------------------------------------------------

def structural_position_strategy(
    reference_fp: ElementFingerprint,
    soup: BeautifulSoup,
    top_n: int = 5,
) -> List[CandidateLocator]:
    """Find elements at a similar structural position (depth, sibling index, parent).

    This is useful when element attributes have changed but the page layout
    is the same.

    Args:
        reference_fp: Reference fingerprint.
        soup: Parsed document.
        top_n: Max candidates.

    Returns:
        Sorted list of ``CandidateLocator`` instances.
    """
    candidates: List[CandidateLocator] = []
    elements = find_all_elements(soup)

    for elem in elements:
        fp = extract_fingerprint(elem)
        score = 0.0

        # Same tag
        if fp.tag == reference_fp.tag:
            score += 0.30

        # Same parent tag
        if fp.parent_tag == reference_fp.parent_tag:
            score += 0.20

        # Depth proximity
        depth_diff = abs(fp.depth - reference_fp.depth)
        score += 0.20 * max(0, 1 - depth_diff / max(reference_fp.depth, 1))

        # Sibling index proximity
        idx_diff = abs(fp.sibling_index - reference_fp.sibling_index)
        score += 0.15 * max(0, 1 - idx_diff / max(reference_fp.sibling_index, 1))

        # Child count similarity
        cc_diff = abs(fp.child_count - reference_fp.child_count)
        score += 0.15 * max(0, 1 - cc_diff / max(reference_fp.child_count, 1))

        if score < 0.25:
            continue

        selector = _build_css_selector(elem)
        candidates.append(
            CandidateLocator(
                locator_type=LocatorType.CSS,
                value=selector,
                confidence=score,
                strategy=StrategyName.STRUCTURAL_POSITION,
                explanation=(
                    f"Structural position score {score:.2%}: "
                    f"depth={fp.depth}, sibling_index={fp.sibling_index}"
                ),
            )
        )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Strategy 4 -- Text Content Matching
# ---------------------------------------------------------------------------

def text_content_strategy(
    reference_fp: ElementFingerprint,
    soup: BeautifulSoup,
    top_n: int = 5,
    threshold: float = 0.40,
) -> List[CandidateLocator]:
    """Find elements whose visible text is similar to *reference_fp*.

    Args:
        reference_fp: Reference fingerprint.
        soup: Parsed document.
        top_n: Max candidates.
        threshold: Minimum text similarity ratio.

    Returns:
        Sorted list of ``CandidateLocator`` instances.
    """
    if not reference_fp.text_content:
        return []

    candidates: List[CandidateLocator] = []
    ref_text = reference_fp.text_content.lower()
    elements = find_all_elements(soup)

    for elem in elements:
        elem_text = elem.get_text(strip=True)
        if not elem_text:
            continue
        ratio = SequenceMatcher(None, ref_text, elem_text.lower()).ratio()
        if ratio < threshold:
            continue

        # Boost if tag also matches
        tag_bonus = 0.10 if elem.name == reference_fp.tag else 0.0
        confidence = min(ratio + tag_bonus, 1.0)

        selector = _build_css_selector(elem)
        candidates.append(
            CandidateLocator(
                locator_type=LocatorType.CSS,
                value=selector,
                confidence=confidence,
                strategy=StrategyName.TEXT_CONTENT,
                explanation=f"Text similarity {ratio:.2%} for '{elem_text[:40]}'",
            )
        )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:top_n]
