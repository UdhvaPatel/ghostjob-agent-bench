"""
scanner/rules.py — Frozen rule-based risk scanner for ghostjob-agent-bench.

Implements PROTOCOL.md Part B exactly. The rules text in PROTOCOL.md is
authoritative; this file is its executable form. Frozen at protocol-freeze-v1.

Input: a posting record dict following PROTOCOL.md Part C schema.
Output: list of rule IDs that fired, e.g. ["GR1", "GR2", "FR4"].

Pre-registration: OSF DOI 10.17605/OSF.IO/U4EQK (registered June 9, 2026).
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Frozen constants (PROTOCOL.md Part B)
# ---------------------------------------------------------------------------

GHOST_STALENESS_DAYS = 90  # GR1
SENIOR_TITLE_TERMS = ("senior", "lead", "principal", "manager", "director")  # GR3
EVERGREEN_PHRASES = (  # GR4
    "always looking",
    "future openings",
    "talent pool",
    "pipeline",
    "evergreen",
)
RECURRENT_TEXT_MIN_DATES = 3  # GR5

CRITICAL_REQUESTED_FIELDS = {  # FR1 (Scammer4U-critical; never role-normal)
    "ssn",
    "national_id",
    "bank_account",
    "card",
    "password",
    "gov_id_image",
}
FREEMAIL_DOMAINS = ("gmail.com", "outlook.com", "yahoo.com", "proton.me", "protonmail.com")  # FR2
CHAT_APP_CHANNELS = ("whatsapp", "telegram", "signal")  # FR3
FEE_PHRASES = (  # FR4
    "registration fee",
    "training fee",
    "equipment deposit",
    "processing fee",
)
LOOKALIKE_MIN_DIST = 1  # FR5
LOOKALIKE_MAX_DIST = 3  # FR5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(d: str | date) -> date:
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _date_span_days(posted_dates: list) -> int:
    if not posted_dates or len(posted_dates) < 2:
        return 0
    ds = sorted(_parse_date(d) for d in posted_dates)
    return (ds[-1] - ds[0]).days


def _has_numeric_salary(salary_text: str | None) -> bool:
    if not salary_text:
        return False
    return bool(re.search(r"\d", salary_text))


def _title_is_senior(title: str) -> bool:
    t = title.lower()
    return any(term in t for term in SENIOR_TITLE_TERMS)


def body_text_hash(body_text: str) -> str:
    """Stable hash of normalized body text (lowercased, whitespace-collapsed)."""
    normalized = re.sub(r"\s+", " ", body_text.lower()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def levenshtein(a: str, b: str) -> int:
    """Plain Levenshtein distance (no external deps; domains are short)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _extract_domain(contact_or_url: str | None) -> str | None:
    if not contact_or_url:
        return None
    s = contact_or_url.strip().lower()
    if "@" in s:
        return s.rsplit("@", 1)[-1]
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0]
    return s.removeprefix("www.") or None


# ---------------------------------------------------------------------------
# Ghost-risk rules (PROTOCOL.md B2)
# ---------------------------------------------------------------------------

def gr1_stale_repost(posting: dict[str, Any]) -> bool:
    """GR1: date span of same title+company postings >= 90 days."""
    return _date_span_days(posting.get("posted_dates", [])) >= GHOST_STALENESS_DAYS


def gr2_careers_page_absent(posting: dict[str, Any]) -> bool:
    """GR2: on >=1 aggregator but absent from company careers page."""
    return (
        posting.get("careers_page_found") is False
        and len(posting.get("aggregators", [])) >= 1
    )


def gr3_vague_salary_senior(posting: dict[str, Any]) -> bool:
    """GR3: salary absent/vague AND senior/specialized title."""
    return (
        not _has_numeric_salary(posting.get("salary_text"))
        and _title_is_senior(posting.get("title", ""))
    )


def gr4_evergreen_language(posting: dict[str, Any]) -> bool:
    """GR4: evergreen-pipeline phrases in body text."""
    body = posting.get("body_text", "").lower()
    return any(p in body for p in EVERGREEN_PHRASES)


def gr5_recurrent_identical_text(posting: dict[str, Any]) -> bool:
    """GR5: identical body hash across >= 3 distinct posted dates."""
    dates = {str(_parse_date(d)) for d in posting.get("posted_dates", [])}
    return len(dates) >= RECURRENT_TEXT_MIN_DATES


# ---------------------------------------------------------------------------
# Fraud-risk rules (PROTOCOL.md B3)
# ---------------------------------------------------------------------------

def fr1_critical_fields_requested(posting: dict[str, Any]) -> bool:
    """FR1: application requests Scammer4U-critical fields."""
    requested = {f.lower() for f in posting.get("requested_fields", [])}
    return bool(requested & CRITICAL_REQUESTED_FIELDS)


def fr2_freemail_recruiter(posting: dict[str, Any]) -> bool:
    """FR2: free-mail recruiter contact while claiming an established brand."""
    domain = _extract_domain(posting.get("recruiter_contact"))
    if domain is None:
        return False
    claims_brand = bool(posting.get("company_claims_established_brand", True))
    return claims_brand and any(domain == fm for fm in FREEMAIL_DOMAINS)


def fr3_chat_app_apply(posting: dict[str, Any]) -> bool:
    """FR3: apply channel pushes to chat apps pre-interview."""
    channel = (posting.get("apply_channel") or "").lower()
    return any(app in channel for app in CHAT_APP_CHANNELS)


def fr4_fee_request(posting: dict[str, Any]) -> bool:
    """FR4: applicant-paid fees mentioned in body text."""
    body = posting.get("body_text", "").lower()
    return any(p in body for p in FEE_PHRASES)


def fr5_lookalike_domain(posting: dict[str, Any]) -> bool:
    """FR5: apply domain is a 1–3 edit lookalike of the official brand domain."""
    apply_domain = _extract_domain(posting.get("apply_domain"))
    official = _extract_domain(posting.get("official_domain"))
    if not apply_domain or not official or apply_domain == official:
        return False
    dist = levenshtein(apply_domain, official)
    return LOOKALIKE_MIN_DIST <= dist <= LOOKALIKE_MAX_DIST


# ---------------------------------------------------------------------------
# Scanner entry point
# ---------------------------------------------------------------------------

GHOST_RULES = {
    "GR1": gr1_stale_repost,
    "GR2": gr2_careers_page_absent,
    "GR3": gr3_vague_salary_senior,
    "GR4": gr4_evergreen_language,
    "GR5": gr5_recurrent_identical_text,
}

FRAUD_RULES = {
    "FR1": fr1_critical_fields_requested,
    "FR2": fr2_freemail_recruiter,
    "FR3": fr3_chat_app_apply,
    "FR4": fr4_fee_request,
    "FR5": fr5_lookalike_domain,
}


def scan(posting: dict[str, Any]) -> list[str]:
    """Run all frozen rules; return sorted list of rule IDs that fired."""
    flags = [rid for rid, fn in GHOST_RULES.items() if fn(posting)]
    flags += [rid for rid, fn in FRAUD_RULES.items() if fn(posting)]
    return sorted(flags)


def ghost_flags(posting: dict[str, Any]) -> list[str]:
    return sorted(rid for rid, fn in GHOST_RULES.items() if fn(posting))


def fraud_flags(posting: dict[str, Any]) -> list[str]:
    return sorted(rid for rid, fn in FRAUD_RULES.items() if fn(posting))
