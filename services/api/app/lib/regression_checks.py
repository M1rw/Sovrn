"""HTML regression testing and validation utilities."""

from __future__ import annotations

from typing import Any


def basic_html_checks(html: str) -> dict[str, Any]:
    """Run lightweight basic HTML structure checks."""
    return {
        "has_doctype": "<!DOCTYPE" in html.upper(),
        "has_html_tag": "<html" in html.lower(),
        "has_head_tag": "<head" in html.lower(),
        "has_body_tag": "<body" in html.lower(),
        "proper_closing": html.count("<") == html.count(">"),
        "has_meta_charset": "charset" in html.lower(),
        "has_title": "<title" in html.lower(),
    }


def accessibility_checks(html: str) -> dict[str, Any]:
    """Run lightweight accessibility heuristics."""
    lower_html = html.lower()
    return {
        "has_lang_attribute": 'lang=' in lower_html,
        "has_viewport_meta": "viewport" in lower_html,
        "has_alt_text": lower_html.count('alt=') >= lower_html.count("<img"),
        "has_main_landmark": "<main" in lower_html or "role='main'" in lower_html,
        "has_heading_hierarchy": all(f"<h{i}" in lower_html for i in range(1, 4)),
        "has_form_labels": lower_html.count("<label") >= lower_html.count("<input"),
    }


def summarize(checks: dict[str, Any]) -> list[str]:
    """Summarize failing checks into a list of issues."""
    failing = []

    for check_name, passed in checks.items():
        if isinstance(passed, bool) and not passed:
            failing.append(f"Failed: {check_name.replace('_', ' ')}")

    return failing
