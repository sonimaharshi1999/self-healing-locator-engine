# Author: Maharshi Soni | License: MIT
"""Utility functions: sample HTML generation, formatting, and helpers."""

import json
from typing import Dict


def get_sample_html_before() -> str:
    """Return a synthetic HTML page representing the *original* state.

    This page has well-defined selectors that tests or automation scripts
    would rely on (``#login-btn``, ``.search-input``, ``[data-testid="nav-menu"]``, etc.).
    """
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Sample App v1</title></head>
<body>
  <header id="main-header" class="header-bar dark-theme">
    <nav data-testid="nav-menu" class="primary-nav">
      <a href="/" class="logo-link" id="home-link">Home</a>
      <a href="/about" class="nav-item" id="about-link">About</a>
      <a href="/contact" class="nav-item" id="contact-link">Contact</a>
    </nav>
    <div class="header-actions">
      <input type="text" id="search-box" class="search-input" placeholder="Search..." name="q" />
      <button id="login-btn" class="btn btn-primary" data-testid="login-button">Log In</button>
      <button id="signup-btn" class="btn btn-secondary" data-testid="signup-button">Sign Up</button>
    </div>
  </header>

  <main id="content" class="main-content">
    <section class="hero-section" id="hero">
      <h1 class="hero-title">Welcome to Our App</h1>
      <p class="hero-subtitle">Build amazing things with our platform.</p>
      <button class="btn btn-large btn-cta" id="get-started-btn" data-testid="cta-button">Get Started</button>
    </section>

    <section class="features-section" id="features">
      <div class="feature-card" data-testid="feature-1">
        <h3 class="feature-title">Fast Performance</h3>
        <p class="feature-desc">Lightning-fast load times for your users.</p>
      </div>
      <div class="feature-card" data-testid="feature-2">
        <h3 class="feature-title">Secure</h3>
        <p class="feature-desc">Enterprise-grade security built in.</p>
      </div>
      <div class="feature-card" data-testid="feature-3">
        <h3 class="feature-title">Scalable</h3>
        <p class="feature-desc">Grow from prototype to production seamlessly.</p>
      </div>
    </section>

    <form id="contact-form" class="contact-form" action="/submit" method="post">
      <label for="email-input" class="form-label">Email</label>
      <input type="email" id="email-input" class="form-control" name="email" placeholder="you@example.com" />
      <label for="message-input" class="form-label">Message</label>
      <textarea id="message-input" class="form-control" name="message" rows="4"></textarea>
      <button type="submit" id="submit-btn" class="btn btn-primary">Send Message</button>
    </form>
  </main>

  <footer id="main-footer" class="footer-bar">
    <p class="copyright">&copy; 2024 Sample App. All rights reserved.</p>
    <a href="/privacy" class="footer-link" id="privacy-link">Privacy Policy</a>
    <a href="/terms" class="footer-link" id="terms-link">Terms of Service</a>
  </footer>
</body>
</html>"""


def get_sample_html_after() -> str:
    """Return a synthetic HTML page representing the *updated* state.

    Compared to ``get_sample_html_before``, several selectors have changed:

    - ``#login-btn`` -> ``#auth-login-btn`` with different classes
    - ``#search-box`` -> ``#global-search`` with renamed class
    - ``[data-testid="nav-menu"]`` -> ``[data-testid="navigation"]``
    - ``#get-started-btn`` -> removed id, now uses ``data-action="cta"``
    - ``#signup-btn`` -> ``#register-btn`` with changed text
    - ``.feature-card[data-testid="feature-1"]`` -> ``[data-testid="feat-performance"]``
    - ``#contact-form`` -> ``#inquiry-form``
    """
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Sample App v2</title></head>
<body>
  <header id="app-header" class="header-bar light-theme">
    <nav data-testid="navigation" class="main-nav" role="navigation">
      <a href="/" class="brand-link" id="home-link">Home</a>
      <a href="/about" class="nav-link" id="about-link">About Us</a>
      <a href="/contact" class="nav-link" id="contact-link">Contact Us</a>
    </nav>
    <div class="header-controls">
      <input type="search" id="global-search" class="search-field" placeholder="Search anything..." name="query" aria-label="Search" />
      <button id="auth-login-btn" class="btn btn-outline" data-testid="login-button" aria-label="Log In">Log In</button>
      <button id="register-btn" class="btn btn-accent" data-testid="register-button">Register</button>
    </div>
  </header>

  <main id="app-content" class="page-content">
    <section class="hero-banner" id="hero">
      <h1 class="hero-heading">Welcome to Our App</h1>
      <p class="hero-text">Build amazing things with our platform.</p>
      <button class="btn btn-xl btn-primary" data-action="cta" data-testid="cta-button">Get Started Free</button>
    </section>

    <section class="features-grid" id="features">
      <div class="feature-item" data-testid="feat-performance">
        <h3 class="feature-name">Fast Performance</h3>
        <p class="feature-description">Lightning-fast load times for your users.</p>
      </div>
      <div class="feature-item" data-testid="feat-security">
        <h3 class="feature-name">Secure</h3>
        <p class="feature-description">Enterprise-grade security built in.</p>
      </div>
      <div class="feature-item" data-testid="feat-scale">
        <h3 class="feature-name">Scalable</h3>
        <p class="feature-description">Grow from prototype to production seamlessly.</p>
      </div>
    </section>

    <form id="inquiry-form" class="inquiry-form" action="/api/submit" method="post">
      <label for="user-email" class="input-label">Email Address</label>
      <input type="email" id="user-email" class="input-field" name="email" placeholder="you@example.com" />
      <label for="user-message" class="input-label">Your Message</label>
      <textarea id="user-message" class="input-field" name="message" rows="5"></textarea>
      <button type="submit" id="send-btn" class="btn btn-primary">Send Inquiry</button>
    </form>
  </main>

  <footer id="app-footer" class="footer-section">
    <p class="copyright-text">&copy; 2024 Sample App. All rights reserved.</p>
    <a href="/privacy" class="footer-nav-link" id="privacy-link">Privacy Policy</a>
    <a href="/terms" class="footer-nav-link" id="terms-link">Terms of Service</a>
  </footer>
</body>
</html>"""


def format_result_table(result_dict: Dict) -> str:
    """Format a healing result dictionary as a readable text table.

    Args:
        result_dict: Output of ``HealingResult.to_dict()``.

    Returns:
        Multi-line formatted string.
    """
    lines = []
    lines.append("=" * 78)
    lines.append("SELF-HEALING LOCATOR ENGINE -- RESULT")
    lines.append("=" * 78)
    lines.append(f"Original Selector : {result_dict['original_selector']}")
    lines.append(f"Page Elements      : {result_dict['page_element_count']}")
    lines.append(f"Strategies Used    : {', '.join(result_dict['strategies_used'])}")
    lines.append("-" * 78)

    best = result_dict.get("best_candidate")
    if best:
        lines.append("BEST MATCH:")
        lines.append(f"  Selector   : {best['value']}")
        lines.append(f"  Type       : {best['locator_type']}")
        lines.append(f"  Confidence : {best['confidence']:.2%}")
        lines.append(f"  Strategy   : {best['strategy']}")
        lines.append(f"  Reason     : {best['explanation']}")
    else:
        lines.append("BEST MATCH: (none found)")

    lines.append("-" * 78)
    candidates = result_dict.get("candidates", [])
    lines.append(f"ALL CANDIDATES ({len(candidates)}):")
    for i, cand in enumerate(candidates, 1):
        lines.append(f"  {i:>2}. [{cand['confidence']:>7.2%}] {cand['value']}")
        lines.append(f"      Strategy: {cand['strategy']} -- {cand['explanation']}")

    lines.append("=" * 78)
    return "\n".join(lines)


def format_result_json(result_dict: Dict, indent: int = 2) -> str:
    """Format a healing result as pretty-printed JSON."""
    return json.dumps(result_dict, indent=indent)
