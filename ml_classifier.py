# Author: Maharshi Soni | License: MIT
"""ML-based element classifier using scikit-learn.

Trains a Random Forest model on element fingerprints to predict whether a
candidate element is likely the same logical element as the broken selector's
target.  The classifier is trained on synthetic data generated from DOM
transformations (attribute renaming, class changes, structural shifts).
"""

import hashlib
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from bs4 import BeautifulSoup, Tag

from dom_analyzer import extract_fingerprint, find_all_elements
from models import (
    CandidateLocator,
    ElementFingerprint,
    LocatorType,
    StrategyName,
)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

# Tags we encode as integers for the model
_COMMON_TAGS = [
    "div", "span", "a", "button", "input", "select", "textarea", "label",
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table",
    "tr", "td", "th", "form", "img", "nav", "section", "article", "header",
    "footer", "main", "aside",
]
_TAG_ENCODER = {tag: idx + 1 for idx, tag in enumerate(_COMMON_TAGS)}


def _encode_tag(tag: str) -> int:
    return _TAG_ENCODER.get(tag, 0)


def fingerprint_to_vector(fp: ElementFingerprint) -> np.ndarray:
    """Convert an ``ElementFingerprint`` to a fixed-length numeric vector.

    Features (11):
        0  - encoded tag
        1  - has_id (0/1)
        2  - class_count
        3  - attr_count
        4  - text_length
        5  - encoded parent_tag
        6  - has_parent_id (0/1)
        7  - sibling_index
        8  - child_count
        9  - depth
        10 - id_hash (integer hash, 0 if no id)
    """
    id_hash = int(hashlib.md5(fp.element_id.encode()).hexdigest()[:8], 16) if fp.element_id else 0
    return np.array([
        _encode_tag(fp.tag),
        int(bool(fp.element_id)),
        len(fp.classes),
        len(fp.attributes),
        len(fp.text_content),
        _encode_tag(fp.parent_tag),
        int(bool(fp.parent_id)),
        fp.sibling_index,
        fp.child_count,
        fp.depth,
        id_hash % 100000,
    ], dtype=np.float64)


def compute_pair_features(ref: ElementFingerprint, cand: ElementFingerprint) -> np.ndarray:
    """Compute a pairwise feature vector comparing *ref* and *cand*.

    Features (12):
        0  - tag_match (0/1)
        1  - id_match (0/1)
        2  - class_overlap (Jaccard)
        3  - attr_key_overlap (Jaccard)
        4  - text_len_ratio
        5  - depth_diff
        6  - sibling_index_diff
        7  - child_count_diff
        8  - parent_tag_match (0/1)
        9  - parent_id_match (0/1)
        10 - ref_class_count
        11 - cand_class_count
    """
    def jaccard(a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        union = a | b
        return len(a & b) / len(union) if union else 0.0

    class_overlap = jaccard(set(ref.classes), set(cand.classes))
    attr_overlap = jaccard(set(ref.attributes.keys()), set(cand.attributes.keys()))

    max_text = max(len(ref.text_content), len(cand.text_content), 1)
    text_len_ratio = 1 - abs(len(ref.text_content) - len(cand.text_content)) / max_text

    return np.array([
        float(ref.tag == cand.tag),
        float(ref.element_id != "" and ref.element_id == cand.element_id),
        class_overlap,
        attr_overlap,
        text_len_ratio,
        abs(ref.depth - cand.depth),
        abs(ref.sibling_index - cand.sibling_index),
        abs(ref.child_count - cand.child_count),
        float(ref.parent_tag == cand.parent_tag),
        float(ref.parent_id != "" and ref.parent_id == cand.parent_id),
        len(ref.classes),
        len(cand.classes),
    ], dtype=np.float64)


# ---------------------------------------------------------------------------
# Synthetic training data
# ---------------------------------------------------------------------------

def _generate_training_data(
    reference_fp: ElementFingerprint,
    all_fingerprints: List[ElementFingerprint],
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate labeled pairwise training data from DOM elements.

    Positive samples: the reference paired with *modified* versions of itself
    (simulating attribute drift).  Negative samples: the reference paired with
    other elements.

    Returns:
        (X, y) where X has shape (n_samples, 12) and y is binary.
    """
    X_rows: List[np.ndarray] = []
    y_labels: List[int] = []

    # --- Positive pairs: synthetic mutations of the reference ---
    mutations = _create_mutations(reference_fp)
    for mutated in mutations:
        X_rows.append(compute_pair_features(reference_fp, mutated))
        y_labels.append(1)

    # Also treat exact match as positive
    X_rows.append(compute_pair_features(reference_fp, reference_fp))
    y_labels.append(1)

    # --- Negative pairs: other elements ---
    for fp in all_fingerprints:
        # Skip elements that look too similar (likely the same element)
        if (fp.element_id and fp.element_id == reference_fp.element_id) or (
            fp.tag == reference_fp.tag
            and fp.text_content == reference_fp.text_content
            and set(fp.classes) == set(reference_fp.classes)
        ):
            continue
        X_rows.append(compute_pair_features(reference_fp, fp))
        y_labels.append(0)

    return np.array(X_rows), np.array(y_labels)


def _create_mutations(fp: ElementFingerprint) -> List[ElementFingerprint]:
    """Create synthetic mutations of a fingerprint simulating UI changes."""
    mutations: List[ElementFingerprint] = []

    # Mutation 1: ID renamed
    if fp.element_id:
        m = ElementFingerprint(
            tag=fp.tag,
            element_id=fp.element_id + "-v2",
            classes=list(fp.classes),
            attributes=dict(fp.attributes),
            text_content=fp.text_content,
            parent_tag=fp.parent_tag,
            parent_id=fp.parent_id,
            parent_classes=list(fp.parent_classes),
            sibling_index=fp.sibling_index,
            child_count=fp.child_count,
            depth=fp.depth,
            path=fp.path,
        )
        mutations.append(m)

    # Mutation 2: class added
    m2 = ElementFingerprint(
        tag=fp.tag,
        element_id=fp.element_id,
        classes=fp.classes + ["new-modifier"],
        attributes=dict(fp.attributes),
        text_content=fp.text_content,
        parent_tag=fp.parent_tag,
        parent_id=fp.parent_id,
        parent_classes=list(fp.parent_classes),
        sibling_index=fp.sibling_index,
        child_count=fp.child_count,
        depth=fp.depth,
        path=fp.path,
    )
    mutations.append(m2)

    # Mutation 3: class removed
    if fp.classes:
        m3 = ElementFingerprint(
            tag=fp.tag,
            element_id=fp.element_id,
            classes=fp.classes[:-1],
            attributes=dict(fp.attributes),
            text_content=fp.text_content,
            parent_tag=fp.parent_tag,
            parent_id=fp.parent_id,
            parent_classes=list(fp.parent_classes),
            sibling_index=fp.sibling_index,
            child_count=fp.child_count,
            depth=fp.depth,
            path=fp.path,
        )
        mutations.append(m3)

    # Mutation 4: slightly different text
    if fp.text_content:
        m4 = ElementFingerprint(
            tag=fp.tag,
            element_id=fp.element_id,
            classes=list(fp.classes),
            attributes=dict(fp.attributes),
            text_content=fp.text_content + " ",
            parent_tag=fp.parent_tag,
            parent_id=fp.parent_id,
            parent_classes=list(fp.parent_classes),
            sibling_index=fp.sibling_index,
            child_count=fp.child_count,
            depth=fp.depth,
            path=fp.path,
        )
        mutations.append(m4)

    # Mutation 5: depth shifted by 1
    m5 = ElementFingerprint(
        tag=fp.tag,
        element_id=fp.element_id,
        classes=list(fp.classes),
        attributes=dict(fp.attributes),
        text_content=fp.text_content,
        parent_tag=fp.parent_tag,
        parent_id=fp.parent_id,
        parent_classes=list(fp.parent_classes),
        sibling_index=fp.sibling_index,
        child_count=fp.child_count,
        depth=fp.depth + 1,
        path=fp.path,
    )
    mutations.append(m5)

    # Mutation 6: attribute added
    new_attrs = dict(fp.attributes)
    new_attrs["data-new"] = "true"
    m6 = ElementFingerprint(
        tag=fp.tag,
        element_id=fp.element_id,
        classes=list(fp.classes),
        attributes=new_attrs,
        text_content=fp.text_content,
        parent_tag=fp.parent_tag,
        parent_id=fp.parent_id,
        parent_classes=list(fp.parent_classes),
        sibling_index=fp.sibling_index,
        child_count=fp.child_count,
        depth=fp.depth,
        path=fp.path,
    )
    mutations.append(m6)

    return mutations


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class ElementClassifier:
    """Random Forest classifier that predicts whether a candidate element
    matches a reference element despite DOM changes.

    The model is trained on-the-fly using synthetic mutations of the
    reference fingerprint as positive examples and the remaining page
    elements as negatives.
    """

    def __init__(self, n_estimators: int = 100, random_state: int = 42):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=8,
            random_state=random_state,
            class_weight="balanced",
        )
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def train(
        self,
        reference_fp: ElementFingerprint,
        all_fingerprints: List[ElementFingerprint],
    ) -> Dict[str, object]:
        """Train the classifier using synthetic pairs.

        Returns:
            Dict with ``n_samples``, ``n_positive``, ``n_negative``.
        """
        X, y = _generate_training_data(reference_fp, all_fingerprints)

        n_pos = int(y.sum())
        n_neg = len(y) - n_pos

        # Need at least one of each class
        if n_pos == 0 or n_neg == 0:
            # Fallback: add a dummy opposite-class sample
            if n_pos == 0:
                X = np.vstack([X, np.zeros((1, X.shape[1]))])
                y = np.append(y, 1)
            else:
                X = np.vstack([X, np.zeros((1, X.shape[1]))])
                y = np.append(y, 0)

        self.model.fit(X, y)
        self._is_trained = True

        return {"n_samples": len(y), "n_positive": n_pos, "n_negative": n_neg}

    def predict(
        self,
        reference_fp: ElementFingerprint,
        candidate_fp: ElementFingerprint,
    ) -> float:
        """Return the probability that *candidate_fp* matches the reference.

        Args:
            reference_fp: The original element's fingerprint.
            candidate_fp: A candidate element's fingerprint.

        Returns:
            Probability in [0, 1].
        """
        if not self._is_trained:
            raise RuntimeError("Classifier has not been trained. Call train() first.")
        features = compute_pair_features(reference_fp, candidate_fp).reshape(1, -1)
        proba = self.model.predict_proba(features)
        # Column index 1 = probability of class 1 (match)
        return float(proba[0][1])


def ml_classification_strategy(
    reference_fp: ElementFingerprint,
    soup: BeautifulSoup,
    top_n: int = 5,
    threshold: float = 0.30,
) -> List[CandidateLocator]:
    """Use an ML classifier to rank candidate elements.

    Trains a Random Forest on synthetic mutation pairs, then scores every
    element in *soup*.

    Args:
        reference_fp: Fingerprint of the expected element.
        soup: Parsed HTML document.
        top_n: Maximum candidates to return.
        threshold: Minimum prediction probability.

    Returns:
        Sorted list of ``CandidateLocator`` instances.
    """
    elements = find_all_elements(soup)
    all_fps = [extract_fingerprint(e) for e in elements]

    clf = ElementClassifier()
    clf.train(reference_fp, all_fps)

    candidates: List[CandidateLocator] = []
    for elem, fp in zip(elements, all_fps):
        prob = clf.predict(reference_fp, fp)
        if prob < threshold:
            continue

        # Build selector
        from strategies import _build_css_selector
        selector = _build_css_selector(elem)

        candidates.append(
            CandidateLocator(
                locator_type=LocatorType.CSS,
                value=selector,
                confidence=prob,
                strategy=StrategyName.ML_CLASSIFICATION,
                explanation=f"ML confidence {prob:.2%}, tag={fp.tag}, depth={fp.depth}",
            )
        )

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:top_n]
