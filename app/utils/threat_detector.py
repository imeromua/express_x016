"""Детектор підозрілого тексту: SQL-інӂекції, XSS, патерни команд shell.

Принцип: регексп за патернами атак — не машинне навчання,
отже завжди будуть хибні позитиви. Використовуємо для інформування адміна,
не для автоматичного видалення.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ThreatMatch:
    category: str
    pattern:  str
    snippet:  str   # фрагмент тексту до 60 символів


# (назва, флаги, [патерни])
_RULES: list[tuple[str, int, list[str]]] = [
    (
        "SQL Injection",
        re.IGNORECASE,
        [
            r"(\bSELECT\b.+\bFROM\b)",
            r"(\bUNION\b.{0,20}\bSELECT\b)",
            r"(\bDROP\b.{0,10}\b(TABLE|DATABASE|SCHEMA)\b)",
            r"(\bINSERT\b.+\bINTO\b)",
            r"(\bUPDATE\b.+\bSET\b.+\bWHERE\b)",
            r"(\bDELETE\b.+\bFROM\b)",
            r"('\s*(OR|AND)\s*'?\d+|\"\s*(OR|AND)\s*\"?\d+)",   # ' OR 1=1
            r"(;\s*--\s|--\s*$)",          # SQL комент
            r"(\bEXEC(UTE)?\s*\()",        # EXEC(
            r"(\bxp_\w+)",                 # xp_cmdshell і под.
            r"(SLEEP\s*\(\s*\d+)",         # time-based blind
            r"(WAITFOR\s+DELAY)",
            r"(\bINFORMATION_SCHEMA\b)",
        ],
    ),
    (
        "XSS",
        re.IGNORECASE | re.DOTALL,
        [
            r"<script[\s>]",
            r"javascript\s*:",
            r"on(load|error|click|mouseover|focus)\s*=",
            r"<\s*iframe[\s>]",
            r"<\s*img[^>]+src\s*=\s*['"]?javascript",
            r"document\.(cookie|write|location)",
            r"eval\s*\(",
        ],
    ),
    (
        "Shell Injection",
        re.IGNORECASE,
        [
            r"(;\s*rm\s+-rf)",
            r"(\|\s*(bash|sh|cmd|powershell))",
            r"(&&\s*(wget|curl)\s+http)",
            r"(\$\(.*\))",                 # $(command)
            r"(`[^`]+`)",                  # backtick execution
            r"(/etc/passwd)",
            r"(\.\./\.\./)",               # path traversal
        ],
    ),
]

# Прекомпільовані патерни
_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (cat, [re.compile(p, flags) for p in patterns])
    for cat, flags, patterns in _RULES
]


def detect_threats(text: str) -> List[ThreatMatch]:
    """Повертає список ThreatMatch для всіх знайдених патернів."""
    if not text or len(text) < 8:
        return []

    found: List[ThreatMatch] = []
    for category, patterns in _COMPILED:
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                snippet = text[max(0, m.start()-10): m.end()+10].strip()[:60]
                found.append(ThreatMatch(
                    category=category,
                    pattern=pattern.pattern,
                    snippet=snippet,
                ))
                break  # одне спрацювання на категорію
    return found
