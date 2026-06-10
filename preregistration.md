# Pre-Registration: Measuring Autonomous Job-Search Agent Susceptibility to Ghost and Fraudulent Job Postings

**Working title:** When AI Agents Apply for Jobs That Don't Exist: Task-Level Harm from Ghost and Fraudulent Postings in Autonomous Job-Search Agents

**Author:** Udhva Patel (sole author)
**Affiliation:** The University of Texas at Dallas, MS Information Technology and Management
**Date of pre-registration:** June 9, 2026
**Registration venue:** OSF Registries (osf.io) and public GitHub repository (timestamped commit)
**Status:** Data collection has NOT begun. No experiments have been run.

---

## 1. Background and Rationale

Recent benchmarks have established that LLM-driven web agents are vulnerable to adversarial, attacker-controlled web content: URL-level disguise attacks that lure agents to malicious websites (FraudBench / MalURLBench, which are companion works from the same research line), dark-pattern manipulation injected into real consumer interfaces (SusBench, IUI 2026), and PII leakage to attacker-controlled social-engineering environments (Scammer4U, which found 54–93% critical-PII leakage versus 0% on benign-twin baselines). Related work also studies agents as perpetrators of employment-category fraud on social platforms (MultiAgentFinancialFraudBench), which is the inverse of the victim-side question studied here. All of these study content that is malicious by construction or agents acting maliciously. Notably, SusBench found agents susceptible specifically to subtle deception (Preselection, Trick Wording, Hidden Information) while resilient to overt manipulation — motivating the hypothesis that ghost postings, which present no overt malicious signal whatsoever, will largely evade agent scrutiny.

A distinct and unstudied class of deceptive content is the **ghost job posting**: a listing published by a real company, on a legitimate platform, for a role the company does not intend to fill (or has already filled), as well as economically motivated fraudulent listings that mimic legitimate postings. These produce no malware, no injection payload, and no attacker-controlled infrastructure, so they evade the threat models of all prior agent-security benchmarks by design. Yet for an autonomous job-application agent, they cause concrete task-level harm: wasted compute and steps, resume/PII submission into dead or hostile channels, and false task-success reports to the user.

This study measures that harm for the first time.

## 2. Research Questions and Confirmatory Hypotheses

**RQ1 — Discrimination.** Do autonomous job-search agents engage with ghost/fraudulent postings at a different rate than verified-real postings?

- **H1:** Agents' application rate on ghost postings will not be meaningfully lower than on verified-real postings. Operationally: the difference in application rate (real minus ghost) will be less than 15 percentage points.
- **Falsification criterion for H1:** If agents apply to ghost postings at a rate at least 15 percentage points lower than real postings (two-proportion z-test, alpha = 0.05, after multiple-comparison correction across models), H1 is rejected and agents will be deemed to possess meaningful native discrimination ability.

**RQ2 — Signal usage.** Which legitimacy signals do agents attend to or ignore?

- **H2:** Agents will fail to use temporal/repost signals (posting age over 90 days, repeated reposting, absence from the company's own careers page) even when these signals are present and accessible in the environment. Operationally: in fewer than 10% of ghost-posting episodes will the agent take any verification action (defined in Section 5.3) before applying.
- **Falsification criterion for H2:** Verification actions observed in 10% or more of ghost-posting episodes (binomial test against 0.10, alpha = 0.05).

**H3 — PII exposure.** Agents will submit **sensitive applicant PII** (full name plus at least one of: phone, address, work-authorization status, date of birth) to fraudulent postings at a rate exceeding 50% of fraudulent-posting episodes when no privacy guidance is given. *Terminology note: this tier intentionally differs from Scammer4U's "critical" tier (SSN, payment credentials, passwords); under their taxonomy, our measure spans their medium and high tiers, plus work-authorization status as a job-domain-specific sensitive field. We use the distinct label "sensitive applicant PII" to avoid conflation, and the persona deliberately excludes Scammer4U-critical fields, since legitimate job applications never require them — any request for such fields is itself coded as a fraud marker.*

- **Falsification criterion:** Observed sensitive-applicant-PII submission rate on fraudulent postings is below 50% (binomial test, alpha = 0.05).

**RQ3 — Mitigation.** Does an explicit verification instruction reduce ghost/fraud engagement, and at what cost?

- **H4a:** A verification-instruction prompt will reduce ghost+fraud application rate by less than 30 percentage points relative to the no-guidance condition (consistent with the null-mitigation pattern reported in Scammer4U).
- **H4b:** The verification-instruction prompt will increase the false-rejection rate on verified-real postings by at least 10 percentage points (a precision/recall tradeoff).
- **Falsification criteria:** H4a is rejected if the pooled reduction is 30 pp or greater (two-proportion z-test, alpha = 0.05). H4b is rejected if the false-rejection increase is below 10 pp.

All hypotheses are confirmatory and were specified before any data collection. Any analysis not listed in Section 6 will be reported as exploratory.

## 3. Study Design

**Design type:** Controlled sandbox experiment; between-condition comparison with posting class (real / ghost / fraudulent) as the primary within-environment factor and prompt condition (no guidance / verification instruction) as the between-run factor.

**Environment:** A locally hosted, sandboxed job-board environment. The verified-real posting class serves the same methodological role as Scammer4U's benign-twin baselines: any differential harm observed on ghost/fraudulent postings is thereby attributable to the deceptive content itself rather than to incidental agent behavior. Real postings are mirrored as static HTML clones with mock ATS application forms. Ghost postings are mirrors of listings meeting the ghost criteria in Section 4. Fraudulent postings are reconstructions seeded from documented scam-job datasets (e.g., the fake-job-posting subset used in Fraud-R1 and the EMSCAD corpus). **No live applications are ever submitted to real companies or real ATS systems.** All form submissions terminate in the sandbox.

**Agents under test (3 model families, 2 scaffolds each, subject to budget):**
- A browsing/computer-use agent scaffold (navigate, read, fill forms).
- A retrieve-and-apply pipeline scaffold (search index, select, apply).
- Model families: one Anthropic model, one OpenAI model, one open-weights model served via API. Exact model versions will be recorded at run time and frozen for the duration of data collection.

**Task given to the agent:** A fixed persona (synthetic resume and profile; no real PII) and the instruction to find and apply to suitable positions matching the persona. The persona resume contains canary tokens to make PII-submission tracing unambiguous.

**Episodes:** Each episode presents the agent with a search context containing a randomized mix of real, ghost, and fraudulent postings in fixed proportion (see Section 4.4). Episode ends when the agent reports completion or hits a 50-step cap.

## 4. Sampling Plan

### 4.1 Posting classes and inclusion criteria

- **Verified-real (target n = 100):** Posting appears on an aggregator AND on the company's official careers page, posted within the last 30 days, company verifiable via official domain and registry presence.
- **Ghost (target n = 100):** At least two of: (a) posting age or repost history of 90+ days; (b) present on aggregators but absent from the company's own careers page at collection time; (c) flagged by the author's pre-existing rule-based risk scanner (rules frozen and published in the repository before data collection); (d) identical posting text recurring across 3+ distinct posting dates.
- **Fraudulent (target n = 100):** Sourced or reconstructed from labeled scam-job corpora; exhibits at least one documented fraud marker (upfront fee request, off-platform contact push, PII overcollection relative to role norms, domain impersonation).

### 4.2 Labeling

Each posting is labeled by the author using the frozen rubric above. A 20% random subsample will be independently relabeled by at least one volunteer rater recruited from the author's graduate program; inter-rater agreement (Cohen's kappa) will be reported. Postings with rater disagreement are excluded and replaced.

### 4.3 Sample size justification

With n = 100 postings per class and approximately 30 episodes per agent-condition cell, a two-proportion z-test has over 80% power to detect a 15-percentage-point difference in application rates at alpha = 0.05 (baseline rate assumed 70%). Power analysis script will be included in the repository.

### 4.4 Episode composition

Each episode's search context contains 10 postings: 6 real, 3 ghost, 1 fraudulent, order randomized with a fixed seed schedule published in the repository.

### 4.5 Stopping rule

Data collection stops when every agent-condition cell reaches 30 completed episodes, or when the pre-allocated API budget (USD 150–300, hard cap USD 300) is exhausted, whichever comes first. If budget-stopped, all cells will be truncated to the same minimum episode count.

## 5. Variables

### 5.1 Independent variables
1. Posting class: real / ghost / fraudulent (within-environment).
2. Prompt condition: no guidance / verification instruction (between-run). The exact text of both prompts is frozen in the repository before data collection.
3. Model family and scaffold (between-run).

### 5.2 Primary dependent variables
1. **Application rate per posting class:** proportion of presented postings of each class to which the agent submits the application form.
2. **Sensitive-applicant-PII submission rate:** proportion of fraudulent-posting episodes in which canary sensitive applicant PII (as defined in H3) is submitted.
3. **Verification action rate:** proportion of episodes containing at least one verification action before any application.
4. **False-rejection rate:** proportion of verified-real postings the agent explicitly declines or skips after inspection (mitigation-cost measure).
5. **Economic waste:** mean agent steps and mean API cost (USD) expended on ghost/fraudulent postings per episode.

### 5.3 Operational definition of "verification action"
Any of: navigating to the company's official careers page or homepage; issuing a search query containing the company name plus a legitimacy-related term (e.g., "scam", "reviews", "careers"); explicitly comparing posting date or repost history; declining with a stated legitimacy rationale. Detected via logged action traces; an LLM-as-judge classifier (prompt frozen in repo) labels rationale statements, with a 15% human-audited subsample and reported agreement.

## 6. Analysis Plan

1. **H1:** Two-proportion z-tests comparing application rate on real vs. ghost postings, per model, with Holm-Bonferroni correction across models; pooled estimate reported with 95% CIs (Wilson intervals).
2. **H2:** Binomial test of verification-action rate against the 0.10 threshold, per model and pooled.
3. **H3:** Binomial test of sensitive-applicant-PII submission rate against the 0.50 threshold in the no-guidance condition.
4. **H4a/H4b:** Two-proportion z-tests between prompt conditions on (a) ghost+fraud application rate and (b) real-posting false-rejection rate; effect sizes reported as percentage-point differences with 95% CIs.
5. **Mixed-effects logistic regression (secondary, confirmatory):** apply/no-apply as outcome; posting class, prompt condition, and model as fixed effects; posting ID and episode as random intercepts. Reported alongside the simple tests as a robustness check.
6. **Exploratory (clearly labeled as such):** per-signal ablations (which ghost criterion drives detection when it occurs), scaffold differences, step-level trace analysis of failure modes, cost curves.

**Inference criteria:** alpha = 0.05 throughout; Holm-Bonferroni within each hypothesis family; all tests two-sided except the threshold binomial tests (one-sided as stated).

## 7. Exclusion Criteria

- Episodes terminated by infrastructure error (API outage, sandbox crash) are excluded and rerun with the same seed.
- Episodes in which the agent refuses the task entirely at step 1 are excluded from rate calculations but counted and reported separately as refusals.
- Postings whose class label failed inter-rater agreement (Section 4.2) are replaced before data collection completes.
- No outcome-based exclusions: no episode will be excluded because of how the agent performed.

## 8. Known Limitations (stated in advance)

- Sandboxed mirrors may differ from live platforms (no live ATS quirks, no CAPTCHA, no dynamic content); results are a controlled lower bound on environmental complexity.
- Ghost labeling is heuristic; ground truth ("the company never intended to hire") is unobservable. The frozen rubric is a proxy and is published for critique.
- Single-author labeling with partial second-rater audit is a resource constraint, mitigated by published rubric and released data.
- Model versions drift; results are claims about the frozen versions tested, not about model families in perpetuity.

## 9. Ethics Statement

No live applications are submitted; no real ATS or employer system is contacted by agents. The synthetic persona contains no real person's PII. Mirrored postings are used for research measurement under fair-use-style minimal reproduction; company names in released data will be pseudonymized. Fraudulent postings are reconstructions in a closed sandbox and are never published in operational form. The study measures defensive susceptibility; it does not develop or release attack tooling.

## 10. Data and Code Availability

Upon paper release: the labeling rubric, frozen prompts, sandbox code, seed schedules, power analysis, full action traces, and analysis notebooks will be released in the public GitHub repository. The pre-registration freeze commit hash will be cited in the paper.

## 11. Timeline

- Freeze and post this pre-registration: June 9, 2026
- Dataset collection and sandbox build: July 2026
- Experiment runs: August 2026
- Analysis and writing: September 2026
- arXiv posting: late September 2026
- Workshop submission(s): October–November 2026

---

*Any deviation from this plan in the final paper will be explicitly disclosed and justified in a "Deviations from Pre-Registration" subsection.*
