"""Escalation patterns and scanning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EscalationPattern:
    """Pattern that triggers escalation."""
    keywords: list[str]
    min_tier: int
    label: str


DEFAULT_PATTERNS: list[EscalationPattern] = [
    EscalationPattern(
        keywords=["deploy", "production", "release", "prod", "live"],
        min_tier=0,  # critical
        label="production deployment",
    ),
    EscalationPattern(
        keywords=["security", "auth", "password", "secret", "token", "key"],
        min_tier=0,  # critical
        label="security sensitive",
    ),
    EscalationPattern(
        keywords=["database", "migration", "schema", "migrate"],
        min_tier=1,  # high
        label="database changes",
    ),
    EscalationPattern(
        keywords=["payment", "billing", "transaction", "charge"],
        min_tier=0,  # critical
        label="financial transaction",
    ),
    EscalationPattern(
        keywords=["refactor", "rewrite", "architecture", "migrate"],
        min_tier=1,  # high
        label="major refactor",
    ),
]


def scan(text: str, patterns: list[EscalationPattern] | None = None) -> tuple[int, str] | None:
    """Scan text for escalation triggers.
    
    Returns (min_tier, label) if any pattern matches, else None.
    """
    patterns = patterns or DEFAULT_PATTERNS
    text_lower = text.lower()
    
    best_match: tuple[int, str] | None = None
    for pattern in patterns:
        if any(kw in text_lower for kw in pattern.keywords):
            if best_match is None or pattern.min_tier < best_match[0]:
                best_match = (pattern.min_tier, pattern.label)
    
    return best_match
