"""Severity ranking and CI exit-code helpers."""

from __future__ import annotations

import re
from typing import Optional

SEVERITY_ORDER = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0,
    "NONE": -1,
}

SEVERITY_ALIASES = {
    "CRIT": "CRITICAL",
    "ERROR": "CRITICAL",
    "WARN": "MEDIUM",
    "WARNING": "MEDIUM",
    "INFORMATIONAL": "INFO",
}

FINDING_RE = re.compile(
    r"\*\*\[(?P<sev>[A-Za-z]+)\]\*\*",
    re.IGNORECASE,
)
HIGHEST_RE = re.compile(
    r"Highest severity:\s*(?P<sev>[A-Za-z]+)",
    re.IGNORECASE,
)


def normalize_severity(value: str) -> str:
    key = value.strip().upper()
    key = SEVERITY_ALIASES.get(key, key)
    return key if key in SEVERITY_ORDER else "INFO"


def extract_highest_severity(review: str) -> str:
    """Infer the highest severity mentioned in a review."""
    highest = "NONE"
    highest_rank = SEVERITY_ORDER["NONE"]

    explicit = HIGHEST_RE.search(review)
    if explicit:
        sev = normalize_severity(explicit.group("sev"))
        if SEVERITY_ORDER[sev] > highest_rank:
            highest = sev
            highest_rank = SEVERITY_ORDER[sev]

    for match in FINDING_RE.finditer(review):
        sev = normalize_severity(match.group("sev"))
        if SEVERITY_ORDER[sev] > highest_rank:
            highest = sev
            highest_rank = SEVERITY_ORDER[sev]

    return highest


def should_fail(highest: str, fail_on: str) -> bool:
    """Return True if CI should fail based on fail_on threshold."""
    threshold = normalize_severity(fail_on)
    if threshold == "NONE" or fail_on.strip().lower() == "none":
        return False
    return SEVERITY_ORDER[normalize_severity(highest)] >= SEVERITY_ORDER[threshold]


def exit_code_for(highest: str, fail_on: str) -> int:
    return 2 if should_fail(highest, fail_on) else 0


def severity_badge(severity: Optional[str]) -> str:
    if not severity:
        return "NONE"
    return normalize_severity(severity)
