"""
scanner/test_rules.py — Unit tests for the frozen risk scanner.
Run: python -m pytest scanner/test_rules.py -q
Every rule gets at least one firing case and one non-firing case.
"""

from rules import (
    scan,
    ghost_flags,
    fraud_flags,
    levenshtein,
    body_text_hash,
)


def base_posting(**overrides):
    p = {
        "id": "TEST",
        "title": "Data Analyst",
        "company_pseudonym": "Company_001",
        "body_text": "We are hiring a data analyst to join our team.",
        "posted_dates": ["2026-06-01"],
        "aggregators": ["indeed"],
        "careers_page_found": True,
        "salary_text": "$70,000 - $85,000",
        "apply_channel": "mock_ats",
        "recruiter_contact": None,
        "requested_fields": ["name", "email", "phone", "resume", "work_auth"],
        "apply_domain": None,
        "official_domain": "company001.com",
    }
    p.update(overrides)
    return p


# ---------------- Ghost rules ----------------

def test_gr1_fires_on_90_day_span():
    p = base_posting(posted_dates=["2026-01-01", "2026-04-15"])
    assert "GR1" in ghost_flags(p)


def test_gr1_silent_under_90_days():
    p = base_posting(posted_dates=["2026-04-01", "2026-05-15"])
    assert "GR1" not in ghost_flags(p)


def test_gr2_fires_when_absent_from_careers_page():
    p = base_posting(careers_page_found=False)
    assert "GR2" in ghost_flags(p)


def test_gr2_silent_when_on_careers_page():
    p = base_posting(careers_page_found=True)
    assert "GR2" not in ghost_flags(p)


def test_gr3_fires_vague_salary_senior_title():
    p = base_posting(title="Senior Machine Learning Engineer", salary_text=None)
    assert "GR3" in ghost_flags(p)


def test_gr3_silent_with_numeric_salary():
    p = base_posting(title="Senior Machine Learning Engineer", salary_text="$150k-$180k")
    assert "GR3" not in ghost_flags(p)


def test_gr3_silent_for_junior_title():
    p = base_posting(title="Data Analyst", salary_text=None)
    assert "GR3" not in ghost_flags(p)


def test_gr4_fires_on_evergreen_language():
    p = base_posting(body_text="We are always looking for great talent for our pipeline.")
    assert "GR4" in ghost_flags(p)


def test_gr4_silent_on_normal_text():
    p = base_posting()
    assert "GR4" not in ghost_flags(p)


def test_gr5_fires_on_three_distinct_dates():
    p = base_posting(posted_dates=["2026-03-01", "2026-04-01", "2026-05-01"])
    assert "GR5" in ghost_flags(p)


def test_gr5_silent_on_two_dates():
    p = base_posting(posted_dates=["2026-03-01", "2026-04-01"])
    assert "GR5" not in ghost_flags(p)


# ---------------- Fraud rules ----------------

def test_fr1_fires_on_ssn_request():
    p = base_posting(requested_fields=["name", "email", "ssn"])
    assert "FR1" in fraud_flags(p)


def test_fr1_silent_on_role_normal_fields():
    p = base_posting()
    assert "FR1" not in fraud_flags(p)


def test_fr2_fires_on_freemail_recruiter():
    p = base_posting(recruiter_contact="hiring.manager@gmail.com")
    assert "FR2" in fraud_flags(p)


def test_fr2_silent_on_corporate_domain():
    p = base_posting(recruiter_contact="recruiter@company001.com")
    assert "FR2" not in fraud_flags(p)


def test_fr3_fires_on_whatsapp_channel():
    p = base_posting(apply_channel="whatsapp +1-555-0000")
    assert "FR3" in fraud_flags(p)


def test_fr3_silent_on_ats():
    p = base_posting(apply_channel="mock_ats")
    assert "FR3" not in fraud_flags(p)


def test_fr4_fires_on_training_fee():
    p = base_posting(body_text="A small training fee is required before onboarding.")
    assert "FR4" in fraud_flags(p)


def test_fr4_silent_on_normal_text():
    p = base_posting()
    assert "FR4" not in fraud_flags(p)


def test_fr5_fires_on_lookalike_domain():
    p = base_posting(apply_domain="cornpany001.com", official_domain="company001.com")
    assert "FR5" in fraud_flags(p)


def test_fr5_silent_on_official_domain():
    p = base_posting(apply_domain="company001.com", official_domain="company001.com")
    assert "FR5" not in fraud_flags(p)


def test_fr5_silent_on_unrelated_domain():
    p = base_posting(apply_domain="totallydifferent.org", official_domain="company001.com")
    assert "FR5" not in fraud_flags(p)


# ---------------- Integration ----------------

def test_scan_combines_ghost_and_fraud():
    p = base_posting(
        careers_page_found=False,
        posted_dates=["2026-01-01", "2026-02-01", "2026-05-01"],
        body_text="Join our talent pool. A processing fee applies.",
    )
    flags = scan(p)
    assert "GR1" in flags and "GR2" in flags and "GR4" in flags and "GR5" in flags
    assert "FR4" in flags


def test_clean_real_posting_has_no_flags():
    assert scan(base_posting()) == []


def test_levenshtein_basics():
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("abc", "abd") == 1
    assert levenshtein("", "abc") == 3


def test_body_text_hash_normalizes_whitespace_and_case():
    assert body_text_hash("Hello   World") == body_text_hash("hello world")
