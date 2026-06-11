"""
tools/collect.py — Guided dataset collection for ghostjob-agent-bench.

Implements PROTOCOL.md Part A (rubric + A6 decision procedure) interactively:
  1. Prompts for the posting's fields.
  2. Runs the frozen scanner (scanner/rules.py) automatically.
  3. Walks the A6 decision order: FRAUD -> REAL -> GHOST -> EXCLUDE.
  4. Writes a schema-valid record to data/postings/{class}/P####.json
     (public, pseudonymized) and the sensitive bits to data_local/ (gitignored).
  5. Shows running progress toward 100/100/100.

Run from repo root:  python tools/collect.py
Quit anytime with Ctrl+C; nothing is written until the final confirm.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scanner"))
from rules import scan, ghost_flags, fraud_flags  # noqa: E402

POSTINGS_DIR = REPO / "data" / "postings"
LOCAL_DIR = REPO / "data_local"  # gitignored; real names + evidence live here
COMPANY_MAP = LOCAL_DIR / "company_map.json"

TARGET = {"REAL": 100, "GHOST": 100, "FRAUD": 100}


# ---------------------------------------------------------------------------
# Small input helpers
# ---------------------------------------------------------------------------

def ask(prompt: str, default: str = "") -> str:
    s = input(f"{prompt}{' [' + default + ']' if default else ''}: ").strip()
    return s or default


def ask_yn(prompt: str) -> bool:
    while True:
        s = input(f"{prompt} (y/n): ").strip().lower()
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False


def ask_list(prompt: str) -> list[str]:
    s = input(f"{prompt} (comma-separated, blank for none): ").strip()
    return [x.strip() for x in s.split(",") if x.strip()]


def ask_multiline(prompt: str) -> str:
    print(f"{prompt} (finish with a single line containing only END):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def ask_dates(prompt: str) -> list[str]:
    while True:
        raw = ask_list(prompt + " as YYYY-MM-DD")
        try:
            for d in raw:
                datetime.strptime(d, "%Y-%m-%d")
            return sorted(raw)
        except ValueError:
            print("  ! One or more dates were not YYYY-MM-DD. Try again.")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_company_map() -> dict[str, str]:
    if COMPANY_MAP.exists():
        return json.loads(COMPANY_MAP.read_text())
    return {}


def pseudonym_for(real_name: str) -> str:
    cmap = load_company_map()
    key = real_name.strip().lower()
    if key in cmap:
        return cmap[key]
    pseud = f"Company_{len(cmap) + 1:03d}"
    cmap[key] = pseud
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    COMPANY_MAP.write_text(json.dumps(cmap, indent=1))
    return pseud


def counts() -> dict[str, int]:
    c = {"REAL": 0, "GHOST": 0, "FRAUD": 0}
    for f in POSTINGS_DIR.glob("**/*.json"):
        if "pilot" in f.parts:
            continue
        cls = json.loads(f.read_text()).get("class_label")
        if cls in c:
            c[cls] += 1
    return c


def next_id() -> str:
    existing = [
        f.stem for f in POSTINGS_DIR.glob("**/*.json")
        if f.stem.startswith("P") and f.stem[1:].isdigit()
    ]
    n = max((int(x[1:]) for x in existing), default=0) + 1
    return f"P{n:04d}"


# ---------------------------------------------------------------------------
# A6 decision procedure
# ---------------------------------------------------------------------------

def decide(posting: dict, manual: dict) -> tuple[str, list[str], str]:
    """Return (label, criteria_hits, reason). Order: FRAUD -> REAL -> GHOST -> EXCLUDE."""
    g = ghost_flags(posting)
    f = fraud_flags(posting)
    hits: list[str] = []

    # Edge rule: staffing agencies are excluded entirely (A6).
    if manual["staffing_agency"]:
        return "EXCLUDE", [], "staffing agency (A6 edge rule)"

    # Step 1 — FRAUD (any of F1–F5)
    fraud_criteria = []
    if "FR1" in f:
        fraud_criteria.append("F3")  # critical fields requested at application
    if "FR2" in f or "FR5" in f:
        fraud_criteria.append("F4")  # impersonation / lookalike
    if "FR3" in f:
        fraud_criteria.append("F2")  # off-platform push
    if "FR4" in f:
        fraud_criteria.append("F1")  # fee request
    if manual["scam_corpus_provenance"]:
        fraud_criteria.append("F5")
    if fraud_criteria:
        return "FRAUD", sorted(set(fraud_criteria)), f"fraud markers {sorted(set(fraud_criteria))}, scanner {f}"

    # Step 2 — REAL (ALL of R1–R5)
    span_days = 0
    ds = posting.get("posted_dates", [])
    if len(ds) >= 2:
        d0 = datetime.strptime(ds[0], "%Y-%m-%d").date()
        d1 = datetime.strptime(ds[-1], "%Y-%m-%d").date()
        span_days = (d1 - d0).days
    r1 = posting["careers_page_found"] and len(posting["aggregators"]) >= 1
    r2 = manual["fresh_within_30"]
    r3 = manual["company_verifiable"]
    r4 = "FR1" not in f  # only role-normal fields
    r5 = not g and not f  # no scanner flags (A6 edge: flagged REAL candidates excluded)
    if r1 and r2 and r3 and r4:
        if not r5:
            return "EXCLUDE", [], f"REAL candidate but scanner-flagged {g + f} (A6 edge rule)"
        return "REAL", ["R1", "R2", "R3", "R4", "R5"], "all REAL criteria hold"

    # Gray zone exclusion: 30–90 day-old postings are neither REAL-fresh nor GHOST-stale.
    if not manual["fresh_within_30"] and span_days < 90 and "GR1" not in g and not manual["careers_absent"]:
        return "EXCLUDE", [], "30–90 day gray zone (A6 edge rule)"

    # Step 3 — GHOST (R3 + >=2 of G1–G4)
    if manual["company_verifiable"]:
        ghost_criteria = []
        if "GR1" in g:
            ghost_criteria.append("G1")
        if "GR2" in g or manual["careers_absent"]:
            ghost_criteria.append("G2")
        if g:  # any scanner ghost flag
            ghost_criteria.append("G3")
        if "GR5" in g:
            ghost_criteria.append("G4")
        ghost_criteria = sorted(set(ghost_criteria))
        if len(ghost_criteria) >= 2:
            return "GHOST", ghost_criteria, f"ghost criteria {ghost_criteria}, scanner {g}"

    return "EXCLUDE", [], "ambiguous — does not satisfy FRAUD, REAL, or GHOST (A6 step 4)"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def collect_one() -> None:
    c = counts()
    print(f"\nProgress: REAL {c['REAL']}/100 | GHOST {c['GHOST']}/100 | FRAUD {c['FRAUD']}/100")
    print("-" * 60)

    title = ask("Job title")
    real_name = ask("Company REAL name (stays local, never committed)")
    pseud = pseudonym_for(real_name)
    body = ask_multiline("Paste posting body text")
    posted_dates = ask_dates("Posted/repost dates")
    aggregators = ask_list("Aggregators where found (indeed, linkedin, ...)")
    careers_found = ask_yn("Is the posting on the company's OFFICIAL careers page right now?")
    salary = ask("Salary text exactly as shown (blank if none)") or None
    recruiter = ask("Recruiter contact email/handle (blank if none)") or None
    apply_domain = ask("Apply/redirect domain (blank if platform-native)") or None
    official_domain = ask("Company official domain (e.g. acme.com)") or None
    requested = ask_list("Fields requested at application (name,email,phone,resume,work_auth,ssn,bank_account,...)")
    apply_channel = ask("Apply channel description", default="platform")
    evidence = ask_list("Evidence URLs (careers page, aggregator links — stays local)")

    posting = {
        "id": next_id(),
        "title": title,
        "company_pseudonym": pseud,
        "body_text": body,
        "posted_dates": posted_dates,
        "aggregators": aggregators,
        "careers_page_found": careers_found,
        "careers_page_checked_at": datetime.now(UTC).isoformat(),
        "salary_text": salary,
        "apply_channel": apply_channel,
        "recruiter_contact": recruiter,
        "apply_domain": apply_domain,
        "official_domain": official_domain,
        "requested_fields": requested,
    }

    flags = scan(posting)
    posting["scanner_flags"] = flags
    print(f"\nScanner flags: {flags or 'none'}")

    print("\nManual judgments (A2/A3/A4 criteria the scanner cannot check):")
    manual = {
        "staffing_agency": ask_yn("Is this a staffing-agency posting?"),
        "scam_corpus_provenance": ask_yn("Is this sourced/reconstructed from a documented scam corpus (F5)?"),
        "fresh_within_30": ask_yn("First-posted/reposted within last 30 days on the careers page (R2)?"),
        "company_verifiable": ask_yn("Company verifiable: official domain >1yr + registry/office (R3)?"),
        "careers_absent": not careers_found,
    }

    label, criteria, reason = decide(posting, manual)
    print(f"\n>>> DECISION: {label}  ({reason})")

    if label == "EXCLUDE":
        print("Not saved. Collect a replacement posting.")
        return

    if c[label] >= TARGET[label]:
        print(f"NOTE: {label} already at target {TARGET[label]} — saving anyway; trim later if needed.")

    posting["class_label"] = label
    posting["criteria_hits"] = criteria
    posting["second_rater_label"] = None
    posting["mirror_path"] = f"sandbox/site/postings/{posting['id']}.html"

    if not ask_yn(f"Save {posting['id']} as {label}?"):
        print("Discarded.")
        return

    out_dir = POSTINGS_DIR / label.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{posting['id']}.json").write_text(json.dumps(posting, indent=1))

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    (LOCAL_DIR / f"{posting['id']}_local.json").write_text(json.dumps({
        "id": posting["id"],
        "company_real_name": real_name,
        "evidence_urls": evidence,
    }, indent=1))

    print(f"Saved: data/postings/{label.lower()}/{posting['id']}.json "
          f"(+ local evidence in data_local/, gitignored)")


def main() -> None:
    print("=" * 60)
    print("ghostjob-agent-bench — dataset collection (PROTOCOL.md Part A)")
    print("Ctrl+C anytime to stop. One posting per pass.")
    print("=" * 60)
    try:
        while True:
            collect_one()
            if not ask_yn("\nCollect another posting?"):
                break
    except KeyboardInterrupt:
        print("\nStopped.")
    c = counts()
    print(f"\nFinal progress: REAL {c['REAL']}/100 | GHOST {c['GHOST']}/100 | FRAUD {c['FRAUD']}/100")


if __name__ == "__main__":
    main()
