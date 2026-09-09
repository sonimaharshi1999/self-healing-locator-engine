# Self-Healing Locator Engine

**Automatically find alternative selectors when UI automation tests break due to changed selectors.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](tests/)

---

## Overview

Modern web applications evolve rapidly. UI automation tests -- whether written with Playwright, Selenium, Cypress, or any other framework -- rely on CSS selectors, XPath expressions, and element IDs to locate elements on a page. When the front-end team renames an ID, refactors CSS class names, or restructures the DOM, those selectors break, and entire test suites start failing. Manually updating hundreds of selectors across dozens of test files is tedious, error-prone, and time-consuming.

The **Self-Healing Locator Engine** solves this problem by automatically finding the best alternative locator when a selector stops matching. Given a broken selector and the current page HTML, the engine applies multiple independent strategies -- DOM structural similarity scoring, attribute fuzzy matching, structural position analysis, text content matching, and ML-based element classification -- to produce a ranked list of candidate selectors, each with a confidence score and a human-readable explanation of why it was chosen.

The engine is designed to be framework-agnostic at its core: it operates on raw HTML strings, so it works with any testing framework or scraping tool. For convenience, the project ships with a Playwright integration wrapper that intercepts selector failures at runtime and transparently retries with a healed selector, turning brittle tests into self-repairing ones. The same pattern can be adapted to Selenium, Puppeteer, or any automation library.

All strategies run on synthetic data and use only open-source, locally-executed models (scikit-learn Random Forest). There are no paid API calls, no cloud dependencies, and no data leaves your machine. The engine is fast enough to run inline during test execution -- typical healing operations complete in under 200 milliseconds on a modern laptop.

Whether you are a QA engineer maintaining a large end-to-end test suite, a developer working on a rapidly-changing front end, or a scraping engineer dealing with shifting page layouts, the Self-Healing Locator Engine gives you a reliable safety net that keeps your automation working even when the DOM shifts under your feet.

---

## Features

- **Multi-strategy healing** -- Five independent strategies vote on the best alternative selector, producing robust results even when individual strategies disagree.
- **DOM Similarity Scoring** -- Compares element fingerprints (tag, id, classes, attributes, text, parent, depth, sibling position) using a weighted similarity function.
- **Attribute Fuzzy Matching** -- Uses `difflib.SequenceMatcher` to find elements whose attribute names and values are close to the original, catching renamed IDs and refactored class names.
- **ML-Based Classification** -- Trains a Random Forest classifier on-the-fly using synthetic mutations of the reference element, then scores every candidate on the page.
- **Structural Position Analysis** -- Finds elements at the same DOM depth, sibling index, and parent structure, useful when attributes change but layout stays the same.
- **Text Content Matching** -- Locates elements by their visible text, ideal for buttons, links, and labels whose text remains stable across redesigns.
- **Confidence scores** -- Every candidate comes with a normalized confidence score in [0, 1] and a plain-English explanation.
- **Framework-agnostic core** -- Operates on raw HTML strings; works with Playwright, Selenium, Puppeteer, Scrapy, or any tool that can provide page HTML.
- **Playwright integration** -- Drop-in `SelfHealingPage` wrapper that auto-heals `click()`, `fill()`, `type()`, and other actions.
- **CLI interface** -- Heal selectors from the command line, pipe HTML via stdin, or run the built-in demo.
- **JSON output** -- Machine-readable output for CI/CD integration and reporting.
- **No paid APIs** -- Everything runs locally using scikit-learn and BeautifulSoup.
- **Fully tested** -- Comprehensive pytest suite covering all public functions.

---

## Architecture / How It Works

```
                         +-------------------+
                         |   Broken Selector |
                         |   + Page HTML     |
                         +---------+---------+
                                   |
                                   v
                    +------------------------------+
                    |  SelfHealingLocatorEngine     |
                    |  (locator_engine.py)          |
                    +------------------------------+
                    |  1. Parse HTML (BeautifulSoup)|
                    |  2. Infer reference           |
                    |     fingerprint from selector |
                    |  3. Run all strategies        |
                    |  4. Merge & rank candidates   |
                    +------+---------+---------+----+
                           |         |         |
              +------------+    +----+----+    +------------+
              |                 |         |                  |
    +---------v-------+ +------v------+ +-v-----------+ +---v-----------+
    | DOM Similarity   | | Attribute   | | ML          | | Structural    |
    | (strategies.py)  | | Fuzzy Match | | Classifier  | | Position +    |
    |                  | | (strat.py)  | | (ml_class.) | | Text Content  |
    +------------------+ +-------------+ +-------------+ +---------------+
              |                 |                |               |
              +--------+--------+--------+-------+               |
                       |                 |                       |
                       v                 v                       v
              +--------------------------------------------------+
              |          Merged Candidate List                   |
              |  (de-duplicated, weighted, normalized)           |
              +--------------------------------------------------+
                                   |
                                   v
                    +------------------------------+
                    |       HealingResult           |
                    |  - best_candidate             |
                    |  - ranked candidates[]        |
                    |  - strategies_used             |
                    +------------------------------+
```

### Strategy Pipeline

1. **Fingerprint Extraction** (`dom_analyzer.py`): Each element is converted to an `ElementFingerprint` capturing tag, ID, classes, all attributes, text content, parent info, sibling index, child count, and DOM depth.

2. **DOM Similarity** (`strategies.py`): Every element on the page is scored against the reference fingerprint using a weighted similarity function (ID match 25%, tag match 20%, class overlap 15%, attribute overlap 15%, text similarity 10%, parent match 10%, sibling proximity 5%).

3. **Attribute Fuzzy Matching** (`strategies.py`): Each element's attributes and text are compared to the reference using `SequenceMatcher` ratios. This catches renames like `#login-btn` to `#auth-login-btn` or `class="search-input"` to `class="search-field"`.

4. **ML Classification** (`ml_classifier.py`): A Random Forest is trained on-the-fly. Positive examples are synthetic mutations of the reference (renamed ID, added/removed classes, shifted depth, changed text). Negative examples are the other page elements. The model then predicts match probability for every candidate.

5. **Structural Position** (`strategies.py`): Scores elements by matching tag, parent tag, DOM depth, sibling index, and child count -- useful when element attributes change but the page layout is preserved.

6. **Text Content** (`strategies.py`): Finds elements whose visible text is similar to the reference, with a tag-match bonus. Particularly effective for buttons, links, and headings.

7. **Merging** (`locator_engine.py`): Candidates from all strategies are de-duplicated by selector value. When the same selector appears in multiple strategies, its weighted scores are summed. The final list is normalized to [0, 1] and sorted by confidence.

---

## Tech Stack

| Component          | Technology                                          |
|--------------------|-----------------------------------------------------|
| Language           | Python 3.9+                                         |
| HTML Parsing       | BeautifulSoup 4 (`html.parser`)                     |
| ML Classification  | scikit-learn (Random Forest)                        |
| Numeric Processing | NumPy                                               |
| Fuzzy Matching     | `difflib.SequenceMatcher` (stdlib)                  |
| Testing            | pytest                                              |
| CLI                | argparse (stdlib)                                   |
| Browser Integration| Playwright (optional)                               |

---

## Getting Started

### Prerequisites

- **Python 3.9 or higher** installed on your system.
- **pip** package manager.
- (Optional) A virtual environment manager like `venv` or `conda`.

### Installation

```bash
# Clone the repository
git clone https://github.com/sonimaharshi1999/self-healing-locator-engine.git
cd self-healing-locator-engine

# (Recommended) Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

The engine works out of the box with sensible defaults. You can customize strategy weights by passing a dictionary when creating the engine:

```python
from locator_engine import SelfHealingLocatorEngine

custom_weights = {
    "dom_similarity": 0.40,
    "attribute_fuzzy": 0.20,
    "ml_classification": 0.20,
    "structural_position": 0.10,
    "text_content": 0.10,
}

engine = SelfHealingLocatorEngine(weights=custom_weights, top_n=5)
```

To disable the ML strategy (faster execution for simple cases):

```python
engine = SelfHealingLocatorEngine(enable_ml=False)
```

---

## Usage

### 1. Run the Built-in Demo

The fastest way to see the engine in action:

```bash
python main.py --demo
```

This runs the engine on synthetic HTML data, showing how six different broken selectors are healed when the page is updated from v1 to v2.

### 2. Heal a Selector from an HTML File

```bash
python main.py --selector "#login-btn" --html-file page.html
```

### 3. Heal with a Reference HTML (Before + After)

Providing the original HTML lets the engine build a more accurate reference fingerprint:

```bash
python main.py --selector "#login-btn" --html-file page_v2.html --ref-html-file page_v1.html
```

### 4. JSON Output for CI/CD

```bash
python main.py --selector "#login-btn" --html-file page.html --json
```

### 5. Pipe HTML via Stdin

```bash
cat page.html | python main.py --selector ".submit-button" --html-stdin
```

### 6. Disable ML for Speed

```bash
python main.py --selector "#login-btn" --html-file page.html --no-ml
```

### 7. Use as a Python Library

```python
from locator_engine import SelfHealingLocatorEngine

engine = SelfHealingLocatorEngine()

html = open("page.html").read()
result = engine.heal("#login-btn", html)

print(f"Best match: {result.best_candidate.value}")
print(f"Confidence: {result.best_candidate.confidence:.2%}")
print(f"Strategy:   {result.best_candidate.strategy.value}")

for i, cand in enumerate(result.candidates, 1):
    print(f"  {i}. [{cand.confidence:.2%}] {cand.value} -- {cand.explanation}")
```

### 8. Playwright Integration

```python
from playwright.sync_api import sync_playwright
from playwright_integration import SelfHealingPage

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")

    healer = SelfHealingPage(page)

    # If "#old-btn" no longer exists, the engine auto-heals:
    healer.click("#old-btn")
    healer.fill("#old-input", "hello@example.com")

    # Review what was healed during the session:
    for event in healer.get_healing_report():
        print(f"  {event['original']} -> {event['healed']} ({event['confidence']:.0%})")

    browser.close()
```

---

## Sample Input / Output

### Demo Run

```
$ python main.py --demo

==============================================================================
  SELF-HEALING LOCATOR ENGINE -- DEMO
  Demonstrating automatic selector healing on synthetic HTML
==============================================================================

==============================================================================
SELF-HEALING LOCATOR ENGINE -- RESULT
==============================================================================
Original Selector : #login-btn
Page Elements      : 28
Strategies Used    : dom_similarity, attribute_fuzzy, ml_classification, structural_position, text_content
------------------------------------------------------------------------------
BEST MATCH:
  Selector   : #auth-login-btn
  Type       : css
  Confidence : 100.00%
  Strategy   : dom_similarity
  Reason     : Structural similarity 73.93% with tag=button, depth=3 | Best fuzzy match 81.82% on id=auth-login-btn | ML confidence 97.00%, tag=button, depth=3
------------------------------------------------------------------------------
ALL CANDIDATES (10):
   1. [100.00%] #auth-login-btn
      Strategy: dom_similarity -- Structural similarity 73.93% with tag=button, depth=3 | Best fuzzy match 81.82% on id=auth-login-btn | ML confidence 97.00%, tag=button, depth=3
   2. [ 64.38%] button[data-testid="cta-button"]
      Strategy: dom_similarity -- Structural similarity 55.67% with tag=button, depth=3 | Best fuzzy match 67.25% on data-testid=cta-button | ML confidence 68.00%, tag=button, depth=3
   3. [ 59.42%] #register-btn
      Strategy: dom_similarity -- Structural similarity 52.10% with tag=button, depth=3 | Best fuzzy match 61.54% on id=register-btn | ML confidence 62.00%, tag=button, depth=3
   4. [ 44.76%] #send-btn
      Strategy: attribute_fuzzy -- Best fuzzy match 57.14% on id=send-btn
   5. [ 35.21%] input[name="query"]
      Strategy: structural_position -- Structural position score 58.33%: depth=3, sibling_index=0
==============================================================================

==============================================================================
SELF-HEALING LOCATOR ENGINE -- RESULT
==============================================================================
Original Selector : #search-box
Page Elements      : 28
Strategies Used    : dom_similarity, attribute_fuzzy, ml_classification, structural_position, text_content
------------------------------------------------------------------------------
BEST MATCH:
  Selector   : #global-search
  Type       : css
  Confidence : 100.00%
  Strategy   : dom_similarity
  Reason     : Structural similarity 70.48% with tag=input, depth=3 | Best fuzzy match 72.73% on id=global-search | ML confidence 95.00%, tag=input, depth=3
------------------------------------------------------------------------------
ALL CANDIDATES (8):
   1. [100.00%] #global-search
      Strategy: dom_similarity -- Structural similarity 70.48% with tag=input, depth=3 | Best fuzzy match 72.73% on id=global-search | ML confidence 95.00%, tag=input, depth=3
   2. [ 58.13%] #user-email
      Strategy: dom_similarity -- Structural similarity 49.20% with tag=input, depth=3
   3. [ 42.85%] #user-message
      Strategy: attribute_fuzzy -- Best fuzzy match 55.12% on name=message
==============================================================================
```

### JSON Output

```
$ python main.py --selector "#login-btn" --html-file page_v2.html --json

{
  "original_selector": "#login-btn",
  "best_candidate": {
    "locator_type": "css",
    "value": "#auth-login-btn",
    "confidence": 1.0,
    "strategy": "dom_similarity",
    "explanation": "Structural similarity 73.93% with tag=button, depth=3 | Best fuzzy match 81.82% on id=auth-login-btn"
  },
  "candidates": [
    {
      "locator_type": "css",
      "value": "#auth-login-btn",
      "confidence": 1.0,
      "strategy": "dom_similarity",
      "explanation": "Structural similarity 73.93% with tag=button, depth=3 | Best fuzzy match 81.82% on id=auth-login-btn"
    },
    {
      "locator_type": "css",
      "value": "#register-btn",
      "confidence": 0.5942,
      "strategy": "dom_similarity",
      "explanation": "Structural similarity 52.10% with tag=button, depth=3"
    }
  ],
  "page_element_count": 28,
  "strategies_used": [
    "dom_similarity",
    "attribute_fuzzy",
    "ml_classification",
    "structural_position",
    "text_content"
  ]
}
```

---

## Project Structure

```
self-healing-locator-engine/
├── main.py                      # CLI entry point
├── locator_engine.py            # Core engine -- orchestrates all strategies
├── dom_analyzer.py              # HTML parsing, fingerprinting, similarity scoring
├── strategies.py                # DOM similarity, fuzzy matching, structural, text strategies
├── ml_classifier.py             # ML-based element classification (scikit-learn)
├── models.py                    # Data models (ElementFingerprint, CandidateLocator, etc.)
├── utils.py                     # Sample HTML data, formatting helpers
├── playwright_integration.py    # Playwright SelfHealingPage wrapper + demo
├── __init__.py                  # Package exports
├── requirements.txt             # Pinned dependencies
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
├── README.md                    # This file
└── tests/
    ├── __init__.py
    ├── conftest.py              # Shared pytest fixtures
    ├── test_models.py           # Tests for data models
    ├── test_dom_analyzer.py     # Tests for DOM analysis functions
    ├── test_strategies.py       # Tests for healing strategies
    ├── test_ml_classifier.py    # Tests for ML classifier
    ├── test_locator_engine.py   # Tests for the main engine
    ├── test_utils.py            # Tests for utility functions
    └── test_playwright_integration.py  # Tests for Playwright integration
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_locator_engine.py -v

# Run with coverage (install pytest-cov first)
pip install pytest-cov
pytest tests/ -v --cov=. --cov-report=term-missing

# Run only fast tests (skip ML)
pytest tests/ -v -k "not ml_classifier"
```

Expected output:

```
$ pytest tests/ -v

========================= test session starts ==========================
collected 58 items

tests/test_models.py::TestElementFingerprint::test_default_values      PASSED
tests/test_models.py::TestElementFingerprint::test_to_feature_dict     PASSED
tests/test_models.py::TestElementFingerprint::test_to_feature_dict_empty PASSED
tests/test_models.py::TestCandidateLocator::test_to_dict               PASSED
tests/test_models.py::TestCandidateLocator::test_confidence_rounding   PASSED
tests/test_models.py::TestHealingResult::test_to_dict_empty            PASSED
tests/test_models.py::TestHealingResult::test_to_dict_with_candidates  PASSED
tests/test_models.py::TestEnums::test_locator_type_values              PASSED
tests/test_models.py::TestEnums::test_strategy_name_values             PASSED
tests/test_dom_analyzer.py::TestParseHtml::test_returns_soup           PASSED
tests/test_dom_analyzer.py::TestParseHtml::test_empty_html             PASSED
tests/test_dom_analyzer.py::TestGetElementDepth::test_body_depth       PASSED
tests/test_dom_analyzer.py::TestGetElementDepth::test_nested_depth     PASSED
tests/test_dom_analyzer.py::TestGetElementPath::test_path_for_button   PASSED
tests/test_dom_analyzer.py::TestGetElementPath::test_path_for_body     PASSED
...
========================= 58 passed in 3.42s ===========================
```

---

## Contributing

Contributions are welcome! Here is how you can help:

1. **Fork** the repository.
2. **Create a branch** for your feature or fix: `git checkout -b feature/my-feature`.
3. **Write tests** for any new functionality.
4. **Run the test suite** to make sure nothing is broken: `pytest tests/ -v`.
5. **Submit a pull request** with a clear description of your changes.

### Development Setup

```bash
git clone https://github.com/sonimaharshi1999/self-healing-locator-engine.git
cd self-healing-locator-engine
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
pytest tests/ -v
```

### Areas Where Help Is Appreciated

- Additional healing strategies (e.g., visual similarity, ARIA-based matching).
- Selenium and Puppeteer integration wrappers.
- Performance benchmarks on large real-world pages.
- Browser extension for interactive healing.
- Persistent model caching across test runs.

---

## Roadmap

- [x] Core healing engine with five strategies
- [x] CLI interface with JSON output
- [x] Playwright integration wrapper
- [x] Comprehensive pytest suite
- [ ] Selenium integration wrapper
- [ ] Persistent model caching (save/load trained classifiers)
- [ ] Visual similarity strategy using element screenshots
- [ ] ARIA and accessibility-attribute-aware matching
- [ ] Healing history database for trend analysis
- [ ] VS Code extension for interactive selector repair
- [ ] CI/CD plugin (GitHub Actions, Jenkins) for automatic test repair
- [ ] Support for Shadow DOM and iframe elements
- [ ] Web dashboard for healing analytics

---

## Author

**Maharshi Soni**

- GitHub: [github.com/sonimaharshi1999](https://github.com/sonimaharshi1999)
- LinkedIn: [linkedin.com/in/maharshi-soni-b56736170](https://linkedin.com/in/maharshi-soni-b56736170)

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)** -- Robust HTML parsing that handles real-world messy markup gracefully.
- **[scikit-learn](https://scikit-learn.org/)** -- Industry-standard machine learning library; the Random Forest classifier at the heart of the ML strategy.
- **[NumPy](https://numpy.org/)** -- Efficient numerical computing for feature vector operations.
- **[Playwright](https://playwright.dev/)** -- Modern browser automation framework; the integration example demonstrates self-healing in action.
- **[pytest](https://pytest.org/)** -- Clean, powerful testing framework that makes writing and running tests a pleasure.
- The QA and test automation community for continuously pushing the boundaries of reliable end-to-end testing.
