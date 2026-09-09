# Author: Maharshi Soni | License: MIT
"""Self-Healing Locator Engine -- automatically find alternative selectors when UI tests break."""

from locator_engine import SelfHealingLocatorEngine
from models import CandidateLocator, ElementFingerprint, HealingResult, LocatorType, StrategyName

__version__ = "1.0.0"
__author__ = "Maharshi Soni"

__all__ = [
    "SelfHealingLocatorEngine",
    "CandidateLocator",
    "ElementFingerprint",
    "HealingResult",
    "LocatorType",
    "StrategyName",
]
