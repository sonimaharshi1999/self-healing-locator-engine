# Author: Maharshi Soni | License: MIT
"""DOM analysis utilities for parsing HTML and extracting element fingerprints."""

from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from models import ElementFingerprint


def parse_html(html: str) -> BeautifulSoup:
    """Parse an HTML string into a BeautifulSoup tree.

    Args:
        html: Raw HTML string.

    Returns:
        Parsed BeautifulSoup document.
    """
    return BeautifulSoup(html, "html.parser")


def get_element_depth(element: Tag) -> int:
    """Calculate the nesting depth of an element in the DOM tree.

    Args:
        element: A BeautifulSoup Tag.

    Returns:
        Integer depth (0 for root-level elements).
    """
    depth = 0
    parent = element.parent
    while parent and parent.name and parent.name != "[document]":
        depth += 1
        parent = parent.parent
    return depth


def get_element_path(element: Tag) -> str:
    """Build a simple CSS-like path from root to the element.

    Args:
        element: A BeautifulSoup Tag.

    Returns:
        Path string such as ``html > body > div > button``.
    """
    parts: List[str] = []
    current: Optional[Tag] = element
    while current and current.name and current.name != "[document]":
        parts.append(current.name)
        current = current.parent  # type: ignore[assignment]
    parts.reverse()
    return " > ".join(parts)


def get_sibling_index(element: Tag) -> int:
    """Return the zero-based index of *element* among its siblings of the same tag.

    Args:
        element: A BeautifulSoup Tag.

    Returns:
        Zero-based sibling index.
    """
    if not element.parent:
        return 0
    index = 0
    for sibling in element.parent.children:
        if isinstance(sibling, Tag):
            if sibling is element:
                return index
            if sibling.name == element.name:
                index += 1
    return 0


def extract_fingerprint(element: Tag) -> ElementFingerprint:
    """Extract a comprehensive fingerprint from a DOM element.

    The fingerprint captures tag name, id, classes, all attributes, text
    content, parent information, sibling position, child count, depth, and
    a structural path.

    Args:
        element: A BeautifulSoup Tag.

    Returns:
        An ``ElementFingerprint`` instance.
    """
    attrs: Dict[str, str] = {}
    for key, val in element.attrs.items():
        if key not in ("id", "class"):
            if isinstance(val, list):
                attrs[key] = " ".join(val)
            else:
                attrs[key] = str(val)

    classes: List[str] = element.get("class", [])  # type: ignore[assignment]
    if isinstance(classes, str):
        classes = classes.split()

    parent_tag = ""
    parent_id = ""
    parent_classes: List[str] = []
    if element.parent and isinstance(element.parent, Tag) and element.parent.name != "[document]":
        parent_tag = element.parent.name
        parent_id = element.parent.get("id", "") or ""
        pc = element.parent.get("class", [])
        parent_classes = pc if isinstance(pc, list) else pc.split()

    text = element.get_text(strip=True)
    # Truncate very long text
    if len(text) > 200:
        text = text[:200]

    return ElementFingerprint(
        tag=element.name,
        element_id=element.get("id", "") or "",
        classes=classes,
        attributes=attrs,
        text_content=text,
        parent_tag=parent_tag,
        parent_id=parent_id,
        parent_classes=parent_classes,
        sibling_index=get_sibling_index(element),
        child_count=len([c for c in element.children if isinstance(c, Tag)]),
        depth=get_element_depth(element),
        path=get_element_path(element),
    )


def find_all_elements(soup: BeautifulSoup) -> List[Tag]:
    """Return all Tag elements in the parsed document.

    Args:
        soup: A parsed BeautifulSoup document.

    Returns:
        List of Tag elements (excludes NavigableString, Comment, etc.).
    """
    return [tag for tag in soup.find_all(True)]


def find_element_by_selector(soup: BeautifulSoup, selector: str) -> Optional[Tag]:
    """Attempt to find a single element matching *selector*.

    Tries CSS selector first, falls back to XPath-like heuristics for
    simple ``//tag[@attr='value']`` patterns.

    Args:
        soup: Parsed document.
        selector: CSS selector or simple XPath expression.

    Returns:
        The first matching Tag, or ``None``.
    """
    # Try CSS selector
    try:
        result = soup.select_one(selector)
        if result:
            return result
    except Exception:
        pass

    # Try simple XPath-like patterns: //tag[@attr='value']
    if selector.startswith("//"):
        import re
        match = re.match(r"//(\w+)\[@(\w+)=['\"](.+?)['\"]\]", selector)
        if match:
            tag_name, attr_name, attr_value = match.groups()
            result = soup.find(tag_name, attrs={attr_name: attr_value})
            if result and isinstance(result, Tag):
                return result

    # Try by id
    if selector.startswith("#"):
        result = soup.find(id=selector[1:])
        if result and isinstance(result, Tag):
            return result

    return None


def compute_structural_similarity(fp1: ElementFingerprint, fp2: ElementFingerprint) -> float:
    """Compute a similarity score between two element fingerprints.

    The score is a weighted combination of tag match, attribute overlap,
    class overlap, text similarity, parent similarity, and positional
    closeness.  Returns a value in [0.0, 1.0].

    Args:
        fp1: Reference fingerprint.
        fp2: Candidate fingerprint.

    Returns:
        Similarity score between 0 and 1.
    """
    score = 0.0
    total_weight = 0.0

    # Tag match (weight 0.20)
    w = 0.20
    total_weight += w
    if fp1.tag == fp2.tag:
        score += w

    # ID match (weight 0.25)
    w = 0.25
    total_weight += w
    if fp1.element_id and fp1.element_id == fp2.element_id:
        score += w

    # Class overlap (weight 0.15)
    w = 0.15
    total_weight += w
    if fp1.classes and fp2.classes:
        s1 = set(fp1.classes)
        s2 = set(fp2.classes)
        if s1 or s2:
            overlap = len(s1 & s2) / len(s1 | s2)
            score += w * overlap

    # Attribute overlap (weight 0.15)
    w = 0.15
    total_weight += w
    if fp1.attributes and fp2.attributes:
        keys1 = set(fp1.attributes.keys())
        keys2 = set(fp2.attributes.keys())
        if keys1 or keys2:
            key_overlap = len(keys1 & keys2) / len(keys1 | keys2)
            val_matches = sum(
                1 for k in keys1 & keys2 if fp1.attributes[k] == fp2.attributes[k]
            )
            val_ratio = val_matches / max(len(keys1 & keys2), 1)
            score += w * (0.5 * key_overlap + 0.5 * val_ratio)

    # Text similarity (weight 0.10)
    w = 0.10
    total_weight += w
    if fp1.text_content and fp2.text_content:
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, fp1.text_content.lower(), fp2.text_content.lower()).ratio()
        score += w * ratio

    # Parent tag match (weight 0.10)
    w = 0.10
    total_weight += w
    if fp1.parent_tag and fp1.parent_tag == fp2.parent_tag:
        score += w * 0.5
        if fp1.parent_id and fp1.parent_id == fp2.parent_id:
            score += w * 0.5

    # Sibling index proximity (weight 0.05)
    w = 0.05
    total_weight += w
    max_index = max(fp1.sibling_index, fp2.sibling_index, 1)
    index_diff = abs(fp1.sibling_index - fp2.sibling_index)
    score += w * max(0, 1 - index_diff / max_index)

    return min(score / total_weight, 1.0) if total_weight > 0 else 0.0
