# Author: Maharshi Soni | License: MIT
"""Tests for ml_classifier.py ML-based element classification."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from dom_analyzer import extract_fingerprint, find_all_elements, find_element_by_selector, parse_html
from ml_classifier import (
    ElementClassifier,
    _create_mutations,
    compute_pair_features,
    fingerprint_to_vector,
    ml_classification_strategy,
)
from models import ElementFingerprint, StrategyName


SAMPLE_HTML = """
<html><body>
<div id="app">
  <button id="submit-btn" class="btn primary" data-testid="submit">Submit</button>
  <button class="btn secondary" data-testid="cancel">Cancel</button>
  <input type="text" id="username" name="user" />
  <a href="/link" class="nav-link">Link</a>
  <span class="badge">New</span>
</div>
</body></html>
"""


@pytest.fixture
def soup():
    return parse_html(SAMPLE_HTML)


@pytest.fixture
def submit_fp(soup):
    elem = find_element_by_selector(soup, "#submit-btn")
    return extract_fingerprint(elem)


@pytest.fixture
def all_fps(soup):
    return [extract_fingerprint(e) for e in find_all_elements(soup)]


class TestFingerprintToVector:
    def test_vector_shape(self, submit_fp):
        vec = fingerprint_to_vector(submit_fp)
        assert vec.shape == (11,)
        assert vec.dtype == np.float64

    def test_known_values(self, submit_fp):
        vec = fingerprint_to_vector(submit_fp)
        # tag "button" is in _COMMON_TAGS at index 3 -> value 4
        assert vec[0] == 4  # encoded tag
        assert vec[1] == 1  # has_id = True
        assert vec[2] == 2  # class_count: btn, primary

    def test_empty_fingerprint(self):
        fp = ElementFingerprint()
        vec = fingerprint_to_vector(fp)
        assert vec[0] == 0  # unknown tag
        assert vec[1] == 0  # no id
        assert vec[10] == 0  # no id hash


class TestComputePairFeatures:
    def test_identical_pair(self, submit_fp):
        features = compute_pair_features(submit_fp, submit_fp)
        assert features.shape == (12,)
        assert features[0] == 1.0  # tag_match
        assert features[1] == 1.0  # id_match
        assert features[2] == 1.0  # class_overlap
        assert features[8] == 1.0  # parent_tag_match

    def test_different_pair(self, submit_fp):
        other = ElementFingerprint(
            tag="span", element_id="badge", classes=["label"],
            text_content="New", parent_tag="section", depth=1,
        )
        features = compute_pair_features(submit_fp, other)
        assert features[0] == 0.0  # tag_match
        assert features[1] == 0.0  # id_match
        assert features[2] == 0.0  # class_overlap (no overlap)


class TestCreateMutations:
    def test_mutations_created(self, submit_fp):
        mutations = _create_mutations(submit_fp)
        assert len(mutations) >= 4  # at least several mutations

    def test_mutations_are_fingerprints(self, submit_fp):
        mutations = _create_mutations(submit_fp)
        for m in mutations:
            assert isinstance(m, ElementFingerprint)

    def test_id_mutation(self, submit_fp):
        mutations = _create_mutations(submit_fp)
        id_mutated = [m for m in mutations if m.element_id.endswith("-v2")]
        assert len(id_mutated) == 1
        assert id_mutated[0].element_id == "submit-btn-v2"

    def test_class_added_mutation(self, submit_fp):
        mutations = _create_mutations(submit_fp)
        class_added = [m for m in mutations if "new-modifier" in m.classes]
        assert len(class_added) == 1


class TestElementClassifier:
    def test_train_and_predict(self, submit_fp, all_fps):
        clf = ElementClassifier(n_estimators=20)
        assert not clf.is_trained

        info = clf.train(submit_fp, all_fps)
        assert clf.is_trained
        assert info["n_samples"] > 0

        # Predict on itself should be high
        prob = clf.predict(submit_fp, submit_fp)
        assert 0.0 <= prob <= 1.0
        assert prob > 0.5

    def test_predict_without_training_raises(self, submit_fp):
        clf = ElementClassifier()
        with pytest.raises(RuntimeError, match="not been trained"):
            clf.predict(submit_fp, submit_fp)

    def test_different_element_lower_score(self, submit_fp, all_fps):
        clf = ElementClassifier(n_estimators=20)
        clf.train(submit_fp, all_fps)

        different = ElementFingerprint(
            tag="span", classes=["badge"], text_content="New",
            parent_tag="div", depth=2,
        )
        prob_different = clf.predict(submit_fp, different)
        prob_self = clf.predict(submit_fp, submit_fp)
        # Self-match should score higher than a very different element
        assert prob_self >= prob_different


class TestMlClassificationStrategy:
    def test_returns_candidates(self, submit_fp, soup):
        candidates = ml_classification_strategy(submit_fp, soup, top_n=5)
        assert len(candidates) > 0

    def test_candidates_sorted(self, submit_fp, soup):
        candidates = ml_classification_strategy(submit_fp, soup, top_n=5)
        confidences = [c.confidence for c in candidates]
        assert confidences == sorted(confidences, reverse=True)

    def test_strategy_label(self, submit_fp, soup):
        candidates = ml_classification_strategy(submit_fp, soup, top_n=3)
        for c in candidates:
            assert c.strategy == StrategyName.ML_CLASSIFICATION

    def test_respects_threshold(self, submit_fp, soup):
        candidates = ml_classification_strategy(
            submit_fp, soup, top_n=10, threshold=0.90
        )
        for c in candidates:
            assert c.confidence >= 0.90
