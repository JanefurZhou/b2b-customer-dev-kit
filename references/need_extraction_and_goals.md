# Design principles and action goals (universal-edition charter)

> Method: this skill was not built by "fixing whatever came up"; it distils **every recurring class of need / lesson** from real
> B2B customer development (merged where synonymous) into **executable rules and script behaviour**.
> **Core demand: no repeated work, a more efficient AI, and no fabrication.**
> Mission of the universal edition: teach users in any industry "how to think while using AI for customer development" and let them use the method directly
> — so the **methodology worth thinking about** is preserved;
> the skill itself: **comprehensive, yet simple to use** (complexity goes into scripts / process, simplicity stays with the user).
>
> Note: this is an internal design memo. Every industry-specific fact has been abstracted into "profile configuration",
> filled in by the user in `config/company_profile.json` at first install.

---

## 1. Core rules (distilled from field lessons, synonyms merged)

| # | Rule | Action goal | Where it lands |
|---|------|----------|------|
| **R1 Low search conversion** | over-aggressive automatic scope gates kill targets; hard truncation loses results; too high an e-mail bar loses good brands | widen across customer tiers + narrow the competitor test (must hit both manufacturing country and manufacturing semantics) + full domain de-dup without truncation + grade entries by e-mail quality | search script / process |
| **R2 No repeated work** (core) | searching for new customers without checking the existing DB first: "all three were already in the DB, half a day wasted" | **mandatory DB lookup before search**; skip on hit | `--against` DB comparison; SOP pre-step |
| **R3 Tables iterate over time into an accumulating DB** | one master table keeps appending, sorted by `added_date`; search compares only the last N months (incremental) instead of reading the whole table | one master table + time window | `--since` window; csv_guide iteration rules |
| **R4 Mis-tagged needs** | judging what a customer does from the company / category name alone is always wrong; tags must come from research evidence such as the website | need_tag / category **decided by research evidence, never by the brand name**; a self-check script that only flags, never edits | iron rule; `audit-category` self-check; research_guide |
| **R5 Duplicate rows in the table** | several rows for one brand (named e-mail / free e-mail / empty) must be merged | in-DB de-dup: merge rows per brand by "named e-mail > free e-mail > empty" | csv_guide de-dup rules |
| **R6 Generic mailboxes bounce** | in real bulk tests generic mailboxes (info@/sales@ etc., guessed / role addresses) bounced at a very high rate; named mailboxes did markedly better | never send cold e-mail straight to a generic mailbox (iron rule); grade B (find a named decision-maker mailbox first) | iron rule; grading logic |
| **R7 Decision makers across channels** | decision makers do not live in one or two channels; rank channels by market | 12-channel panorama + per-region if/else priority | SOP_search_workflow |
| **R8 Reserve pool continuity** | the pool needs lead time, no scrambling for customers every day | sendable-pool floor and reserve days; periodic replenish check | SKILL / SOP recurring tasks |
| **R9 Three pre-send checks + compliance** | e-mail validation → de-dup → notes check; word limit; banned words; no tracking pixels; credentials never stored | three pre-send checks; compliance check | SOP sending step |
| **R10 Multi-level follow-up cooldown** | progressive follow-up + stepped cooldown + final stop and switch channel (LinkedIn / WhatsApp) | multi-level closed loop | SOP follow-up step |
| **R11 Win review** | reply → AI analyses pain points → **recorded only after the user confirms**; review before starting | Step 0 review; the AI only suggests pain points, the human decides | SOP Step 0 |
| **R12 Dashboard reads one table** | dashboards read the master customer table to avoid inconsistent figures across tables | dashboard source = master customer table | dashboard_guide |
| **R13 Shipping safety and compliance** | standard library only, no third-party dependencies; credentials only via environment variables, clear-text SMTP refused, STARTTLS/SSL enforced, IMAP certificate verification | universal-edition code compliance: **high risk = 0, medium risk = 0** | scripts + compliance statement |
| **R14 Universal edition fully de-identified** | the universal edition **contains no** real product database / phone numbers / domains / contacts; placeholders + profile configuration throughout | real information exists only in the user's own private profile; the package can be distributed publicly | packaging separation |

---

## 2. The two missions

**A. Universal edition + SOP = teach "how to think while using AI"**
- Give not only "how" but "why" (the field lesson behind every if/else, e.g. high bounce rates of generic mailboxes, aggressive gates killing targets)
- Distil a **transferable methodology**: customer-spectrum thinking, research decides need, grading instead of one-size-fits-all, incremental instead of full reads, data-driven review
- Users in another industry can think and act the same way

**B. The skill itself = comprehensive but simple**
- Comprehensive: scripts encapsulate the complex logic (de-dup / grading / time window / compliance)
- Simple: the user needs only a few commands (generate queries → search → filter with DB lookup and grading → get candidates) and never needs the internals

---

## 3. Efficiency points (serving "no repetition + efficiency")

1. Automatic DB lookup before search (R2) → `--against`
2. Read only recent data by time (R3) → `--since`
3. Full domain de-dup (R1)
4. Need-tag self-check and correction (R4)
5. Iron rule: check the DB before any search / outreach

---

## 4. Acceptance criteria

- [ ] R1 search: customer-spectrum tiers + relaxed filtering + full de-dup + e-mail quality grading
- [ ] R2 no repetition: DB lookup before search; skip on hit
- [ ] R3 time iteration: master table append + `--since` incremental
- [ ] R4/R5 data quality: need_tag self-check + in-table de-dup rules
- [ ] R6–R12 the whole SOP loop reflects the latest logic
- [x] R13 universal-edition compliance (high risk = 0, medium risk = 0; credentials via environment variables + enforced encryption + clear text refused)
- [x] R14 universal edition de-identified: no real company / product / contact; placeholders + profile configuration
