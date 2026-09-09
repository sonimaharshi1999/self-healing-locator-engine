# Author: Maharshi Soni | License: MIT
"""Core engine that orchestrates all healing strategies to find alternative locators."""

import json
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from dom_analyzer import (
    extract_fingerprint,
    find_all_elements,
    find_element_by_selector,
    parse_html,
)
from ml_classifier import ml_classification_strategy
from models import (
    CandidateLocator,
    ElementFingerprint,
    HealingResult,
    StrategyName,
)
from strategies import (
    attribute_fuzzy_strategy,
    dom_similarity_strategy,
    structural_position_strategy,
    text_content_strategy,
)


# Default strategy weights used when merging candidates from different
# strategies into a single ranked list.
DEFAULT_WEIGHTS: Dict[str, float] = {
    StrategyName.DOM_SIMILARITY.value: 0.30,
    StrategyName.ATTRIBUTE_FUZZY.value: 0.25,
    StrategyName.ML_CLASSIFICATION.value: 0.25,
    StrategyName.STRUCTURAL_POSITION.value: 0.10,
    StrategyName.TEXT_CONTENT.value: 0.10,
}


def _merge_candidates(
    all_candidates: Dict[str, List[CandidateLocator]],
    weights: Dict[str, float],
    top_n: int = 10,
) -> List[CandidateLocator]:
    """Merge and re-score candidates from multiple strategies.

    When the same selector appears in more than one strategy's output, the
    weighted scores are combined.  Otherwise the candidate keeps its
    strategy-weighted score.

    Args:
        all_candidates: Mapping of strategy name to candidate list.
        weights: Strategy weight mapping.
        top_n: Maximum number of merged candidates to return.

    Returns:
        De-duplicated, re-scored, and sorted candidate list.
    """
    selector_map: Dict[str, CandidateLocator] = {}
    selector_scores: Dict[str, float] = {}
    selector_explanations: Dict[str, List[str]] = {}

    for strategy_name, candidates in all_candidates.items():
        w = weights.get(strategy_name, 0.10)
        for cand in candidates:
            key = cand.value
            weighted = cand.confidence * w
            if key in selector_scores:
                selector_scores[key] += weighted
                selector_explanations[key].append(cand.explanation)
            else:
                selector_map[key] = cand
                selector_scores[key] = weighted
                selector_explanations[key] = [cand.explanation]

    # Normalize scores to [0, 1]
    max_score = max(selector_scores.values()) if selector_scores else 1.0
    if max_score == 0:
        max_score = 1.0

    merged: List[CandidateLocator] = []
    for key, base_cand in selector_map.items():
        normalized = selector_scores[key] / max_score
        explanation = " | ".join(selector_explanations[key])
        merged.append(
            CandidateLocator(
                locator_type=base_cand.locator_type,
                value=key,
                confidence=normalized,
                strategy=base_cand.strategy,
                explanation=explanation,
            )
        )

    merged.sort(key=lambda c: c.confidence, reverse=True)
    return merged[:top_n]


class SelfHealingLocatorEngine:
    """Orchestrates multiple healing strategies to propose alternative locators.

    Usage::

        engine = SelfHealingLocatorEngine()
        result = engine.heal(broken_selector, page_html)
        print(result.best_candidate)

    Attributes:
        weights: Per-strategy weight dictionary used during merging.
        top_n: Maximum number of candidates to return.
        enable_ml: Whether to run the (slower) ML classification strategy.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        top_n: int = 10,
        enable_ml: bool = True,
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.top_n = top_n
        self.enable_ml = enable_ml

    def heal(
        self,
        broken_selector: str,
        page_html: str,
        reference_fingerprint: Optional[ElementFingerprint] = None,
    ) -> HealingResult:
        """Run all healing strategies and return ranked alternative locators.

        Args:
            broken_selector: The CSS/XPath selector that no longer matches.
            page_html: Full HTML of the current page.
            reference_fingerprint: Optional pre-computed fingerprint of the
                element the selector was *supposed* to match.  If ``None``,
                the engine will attempt to infer one from the selector string.

        Returns:
            A ``HealingResult`` with ranked candidates.
        """
        soup = parse_html(page_html)
        all_elements = find_all_elements(soup)

        # Try to build a reference fingerprint from the selector itself
        if reference_fingerprint is None:
            reference_fingerprint = self._infer_fingerprint(broken_selector, soup)

        strategies_used: List[str] = []
        all_candidates: Dict[str, List[CandidateLocator]] = {}

        # Strategy 1 -- DOM Similarity
        try:
            dom_cands = dom_similarity_strategy(reference_fingerprint, soup, top_n=self.top_n)
            all_candidates[StrategyName.DOM_SIMILARITY.value] = dom_cands
            strategies_used.append(StrategyName.DOM_SIMILARITY.value)
        except Exception:
            pass

        # Strategy 2 -- Attribute Fuzzy Matching
        try:
            fuzzy_cands = attribute_fuzzy_strategy(reference_fingerprint, soup, top_n=self.top_n)
            all_candidates[StrategyName.ATTRIBUTE_FUZZY.value] = fuzzy_cands
            strategies_used.append(StrategyName.ATTRIBUTE_FUZZY.value)
        except Exception:
            pass

        # Strategy 3 -- ML Classification
        if self.enable_ml:
            try:
                ml_cands = ml_classification_strategy(reference_fingerprint, soup, top_n=self.top_n)
                all_candidates[StrategyName.ML_CLASSIFICATION.value] = ml_cands
                strategies_used.append(StrategyName.ML_CLASSIFICATION.value)
            except Exception:
                pass

        # Strategy 4 -- Structural Position
        try:
            struct_cands = structural_position_strategy(reference_fingerprint, soup, top_n=self.top_n)
            all_candidates[StrategyName.STRUCTURAL_POSITION.value] = struct_cands
            strategies_used.append(StrategyName.STRUCTURAL_POSITION.value)
        except Exception:
            pass

        # Strategy 5 -- Text Content
        try:
            text_cands = text_content_strategy(reference_fingerprint, soup, top_n=self.top_n)
            all_candidates[StrategyName.TEXT_CONTENT.value] = text_cands
            strategies_used.append(StrategyName.TEXT_CONTENT.value)
        except Exception:
            pass

        # Merge
        merged = _merge_candidates(all_candidates, self.weights, top_n=self.top_n)
        best = merged[0] if merged else None

        return HealingResult(
            original_selector=broken_selector,
            candidates=merged,
            best_candidate=best,
            page_element_count=len(all_elements),
            strategies_used=strategies_used,
        )

    def heal_json(
        self,
        broken_selector: str,
        page_html: str,
        reference_fingerprint: Optional[ElementFingerprint] = None,
    ) -> str:
        """Convenience wrapper that returns the healing result as a JSON string."""
        result = self.heal(broken_selector, page_html, reference_fingerprint)
        return json.dumps(result.to_dict(), indent=2)

    # ----- internal helpers -----

    @staticmethod
    def _infer_fingerprint(selector: str, soup: BeautifulSoup) -> ElementFingerprint:
        """Try to infer a reference fingerprint from the selector string.

        If the selector looks like ``#some-id``, we construct a fingerprint
        with that id.  If it looks like ``.cls1.cls2``, we use those classes.
        We also attempt to find the element in *soup* (it may exist if the
        selector is partially broken).
        """
        fp = ElementFingerprint()

        # Try to find the element in the current page
        found = find_element_by_selector(soup, selector)
        if found:
            fp = extract_fingerprint(found)
            return fp

        # Parse the selector for hints
        sel = selector.strip()

        # ID selector
        if sel.startswith("#"):
            fp.element_id = sel[1:].split(".")[0].split("[")[0].split(":")[0]

        # Class selectors
        import re
        class_matches = re.findall(r"\.([a-zA-Z_][\w-]*)", sel)
        if class_matches:
            fp.classes = class_matches

        # Tag
        tag_match = re.match(r"^([a-zA-Z][\w-]*)", sel)
        if tag_match:
            fp.tag = tag_match.group(1)

        # XPath patterns
        if sel.startswith("//"):
            xpath_tag = re.match(r"//(\w+)", sel)
            if xpath_tag:
                fp.tag = xpath_tag.group(1)
            id_match = re.search(r"@id=['\"](.+?)['\"]", sel)
            if id_match:
                fp.element_id = id_match.group(1)
            class_match = re.search(r"@class=['\"](.+?)['\"]", sel)
            if class_match:
                fp.classes = class_match.group(1).split()

        # Attribute selectors [attr="value"]
        attr_matches = re.findall(r'\[(\w[\w-]*)=["\'](.+?)["\']\]', sel)
        for attr_name, attr_val in attr_matches:
            if attr_name == "id":
                fp.element_id = attr_val
            elif attr_name == "class":
                fp.classes = attr_val.split()
            else:
                fp.attributes[attr_name] = attr_val

        return fp
