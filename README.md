# ghostjob-agent-bench

A benchmark measuring how autonomous job-search agents engage with ghost
and fraudulent job postings — task-level harm from organic, non-attack web deception.

> **Status:** Pre-registered June 9, 2026. Data collection has NOT begun.
> No experiments have been run.

## What this is

A controlled, sandboxed benchmark testing whether autonomous job-search
agents can distinguish verified-real job postings from ghost postings
(real companies, roles never intended to be filled) and fraudulent
postings, and measuring the harm when they cannot: wasted effort,
PII submission, and false success reports.

## Research questions

1. Do agents engage with ghost/fraudulent postings at a different rate
   than verified-real ones?
2. Which legitimacy signals do agents use or ignore?
3. Does an explicit verification instruction reduce engagement, and at
   what cost in falsely rejecting real jobs?

## Pre-registration

The full frozen plan is in [`preregistration.md`](./preregistration.md).
 OSF registration DOI: [10.17605/OSF.IO/U4EQK](https://doi.org/10.17605/OSF.IO/U4EQK) — registered June 9, 2026, before data collection.

## Licenses

- **Code:** MIT (see `LICENSE`)
- **Data & documents:** CC BY 4.0

## Ethics

No live applications are ever submitted to real employers. Operational
fraudulent posting content is withheld from this public repository;
only the rubric, taxonomy, and pseudonymized examples are released.
