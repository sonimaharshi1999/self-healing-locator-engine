# Author: Maharshi Soni | License: MIT
"""Data models for the Self-Healing Locator Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class LocatorType(Enum):
    """Supported locator types."""
    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    CLASS = "class"
    NAME = "name"
    TAG = "tag"
    TEXT = "text"
    DATA_ATTR = "data-attr"


class StrategyName(Enum):
    """Names of healing strategies."""
    DOM_SIMILARITY = "dom_similarity"
    ATTRIBUTE_FUZZY = "attribute_fuzzy"
    ML_CLASSIFICATION = "ml_classification"
    STRUCTURAL_POSITION = "structural_position"
    TEXT_CONTENT = "text_content"


@dataclass
class ElementFingerprint:
    """Fingerprint capturing an element's identifying characteristics."""
    tag: str = ""
    element_id: str = ""
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    text_content: str = ""
    parent_tag: str = ""
    parent_id: str = ""
    parent_classes: List[str] = field(default_factory=list)
    sibling_index: int = 0
    child_count: int = 0
    depth: int = 0
    path: str = ""

    def to_feature_dict(self) -> Dict[str, object]:
        """Convert fingerprint to a flat dictionary suitable for ML features."""
        return {
            "tag": self.tag,
            "has_id": int(bool(self.element_id)),
            "class_count": len(self.classes),
            "attr_count": len(self.attributes),
            "text_length": len(self.text_content),
            "parent_tag": self.parent_tag,
            "has_parent_id": int(bool(self.parent_id)),
            "sibling_index": self.sibling_index,
            "child_count": self.child_count,
            "depth": self.depth,
        }


@dataclass
class CandidateLocator:
    """A candidate locator suggestion with scoring metadata."""
    locator_type: LocatorType
    value: str
    confidence: float
    strategy: StrategyName
    explanation: str = ""

    def to_dict(self) -> Dict[str, object]:
        """Serialize to a plain dictionary."""
        return {
            "locator_type": self.locator_type.value,
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "strategy": self.strategy.value,
            "explanation": self.explanation,
        }


@dataclass
class HealingResult:
    """Full result of a healing operation."""
    original_selector: str
    candidates: List[CandidateLocator] = field(default_factory=list)
    best_candidate: Optional[CandidateLocator] = None
    page_element_count: int = 0
    strategies_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Serialize to a plain dictionary."""
        return {
            "original_selector": self.original_selector,
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "page_element_count": self.page_element_count,
            "strategies_used": self.strategies_used,
        }
