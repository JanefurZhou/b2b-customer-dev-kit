# SOP closed-loop logic flowchart (v3.1)

> This file is the **visual if/else closed loop** of the whole B2B customer development process, matching SKILL.md section by section.
> Image (universal edition, no company-specific information): `assets/sop_flowchart.png`; vector / PDF: `assets/sop_flowchart.pdf`;
> machine-readable spec `assets/sop_flowchart.json` (generated together with the image) — section N of `python3 scripts/consistency_audit.py` uses it to verify
> that step names, commands and key numbers match SKILL.md / SOP.md / this file / the script constants. Changing the chart means changing all three.
> If you want your own WhatsApp number or similar in the chart, redraw it with values you have confirmed; never write them into the universal template.

**New in v3.1 vs v3.0**:
- New **② Data Access Layer** at the top: own customer DB import (mandatory declaration at install) · SaaS / customs / CRM export import · business-mailbox keys / multi-mailbox hosting with warm-up / MCP sending · CRM sync · Data Triggers; everything flows into the customer pool.
- The self-replenishing engine becomes a **four-axis rotation**: Depth (d1 companies → d2 decision makers → d3 deep-mining the existing pool) → Reach (regions near to far) → Height (tiers high to low) → Breadth (core/wide/max).
- **Data Triggers** (`triggers.py scan`) scan the customer pool and every data table daily; any outbound action needs human sign-off; bounce anomalies pause hosted mailboxes automatically.

**New in v3.0 vs v2.2**:
- **① Install Gate** at the top: new-install checklist → required profile fields → Soul Seven Kit health check → the user's own confirmation; any failed check loops straight back to filling in (red dashed line); only a pass enters Step 0.
- Step 1 **three discovery sources**: keyword matrix · 15 discovery channels (incl. the registration-free customs path) · 10 social platforms login-free public search + 30 procurement-chain titles.
- Step 2 **evidence tiers S1/S2/S3**: insufficient evidence (S3 only) → need_review for the user to decide, back to Step 3.
- Step 5 **recipient-local sending window** (enforced by the scripts): outside the window the contact is deferred to the next window.
- Step 6 **two cadences**: e-mail 5-level cooldown (3/3/10 days) + social DM 1-3-7-21 (manual); one channel per day.
- Step 8 **win review + weekly kit write-back**: attributed to exactly one file → kit-check → back to Step 0.

## Legend

| Line | Meaning |
|------|------|
| grey solid | main flow |
| red dashed | failed → go back and fix |
| green solid / dashed | loop / self-loop (dashed = wait and retry) |
| cyan solid | hand-over to WhatsApp |
| purple solid | gate pass / back to Step 0 for the next round |
| yellow diamond | decision node (if / else) |
| "▶" at the bottom of a node | the script command or reference document of that step |

---

## 1. Main flowchart

![Main flowchart](assets/sop_flowchart.png)

- **① Install Gate** (`onboarding.py start` → `init / ask / apply-pack` → `kit-check` → `check → attest`) → `if` any of the three checks fails → fill in what is missing (red dashed line back to the new-install checklist); `else` READY → Step 0.
- **② Data Access Layer** (configure right after installing): own customer DB `data_import.py inspect → import` (profile `data_sources.customer_db` required: imported / crm_sync / none) · SaaS / customs / CRM exports dropped into `data/inbox/` through the same entry · sending channel `mail_setup.py` (business-mailbox keys / multi-mailbox hosting with warm-up / MCP connectors) · `crm_sync.py` (CSV / HubSpot API / MCP) → everything flows into the customer pool `customer_db.csv`.
- **Data Triggers** (`triggers.py scan`): pool low / new import file / due follow-up / new reply / bounce anomaly / WA lead / warm-up step-up / mailbox paused / CRM pending sync / weekly review → written to `trigger_queue.json`; `if` outbound → human sign-off; `else` protective actions (pausing a mailbox on bounce anomalies) may run automatically.
- **♻ Self-replenishing engine**: scheduler once a day → check the customer pool → `if` sendable<100 or reserve<30 days → four-axis rotation replenish (Depth d1→d2→d3 · Reach regions near to far · Height tiers high to low · Breadth core→wide→max) → today's queries go to Step 1; `else` sufficient → wait for tomorrow (green dashed).
- **Step 0 Omni-channel Review** (`review_success` · `wa_review review`): success-case plays + WA review + last week's kit write-back conclusions; MEMORY "This week's conclusions" is the starting point of the round.
- **Step 1 Search Candidates** (`queries` · `channels` · `social`) → Three Iron Rules of Search: #1 check the DB first (`filter --against`) → #2 funnel diagnosis (`funnel`) → `if` bottleneck (dup in DB>40% / named rate<20%) → change region / tier or complete e-mails first, back to Step 1 (red dashed); `else` #3 pending-verification pool → truly new customers go to Step 2.
- **Step 2 Background Research** (5 information sources + three research questions + S1/S2/S3) → `if` only S3 → need_review, user decides, then Step 3; `else` (≥1 S1 or 2 independent S2) → Step 3.
- **Step 3 Need Positioning** (two-tag routing): need_tag (your own product / service lines line_a / line_b / multi / unknown) → which line to pitch; solution_tag (11 generic decision drivers) → which hook: compliance/sustainability → compliance type; quality_upgrade/exclusive_custom → differentiation type; low_commitment/cost → low-commitment type; speed → speed type; innovation/one_stop → new-direction type; dedicated_service/strategic_scale → dedicated type; open/unknown → generic exploration. Violating `positioning.tag_rules` → not sent, handed to a human (`conflict-check`).
- **Step 4 Write Content**: the whole e-mail in the recipient's native language, ≤120 words, plain text, quoting S1/S2 facts only.
- **Three pre-send checks** (mailbox ✓ de-dup ✓ notes ✓) → `if` any fails → fix and back to Step 4 for a re-check; `else` → Step 5.
- **Step 5 Send** (`DRY_RUN=1` preview → user approval → `decision_maker_sender.py`) → `if` the recipient is outside the local working-day window → deferred this run (`deferred_window`), sent in the next window; `else` send and write back.
- **Step 6 Follow-up Management** (`imap_scanner.py`, `DRY_RUN=1` first; `cooldown`) → four branches:
  - bounce → `mark_bounced` blacklist + permanent stop → back to the customer pool for replenishment (green)
  - reply → `mark_replied` → manual follow-up; quotes / lead times / inquiry replies need user confirmation; explicit refusal → `add_blacklist` stops every channel
  - no reply → read `followup_count` (= e-mails sent − 1): 0 / 1 / 2 (1–3 e-mails sent) → wait 3 / 3 / 10 days → new angle, back to Step 4; =3 (4 e-mails sent) → stop generic mailboxes → LinkedIn / personal mailbox (manual · 1-3-7-21); ≥4 (5+ e-mails sent) → e-mail stopped → Step 7 WhatsApp
  - won → Step 8
- **Step 7 WhatsApp Trigger**: trigger signal → `convert` → `validate → preview` (fail → fix and convert again) → `harness` test number → `send` (200 → STOP, continue next day with `progress`) → `audit` → write back + `--won_channel wa` → `wa_review` → feeds Step 8 and the next round's WA list.
- **Step 8 Win Review + Kit Write-back**: `add_success` (user-confirmed pain point) → omni-channel review (`review_success` · `email_dashboard` · `wa_review --compare-email`) → weekly kit write-back (`soul_kit/weekly_writeback.md`) → `kit-check` → back to Step 0 for the next round (purple).

---

## 2. WhatsApp bulk-send sub-flow — the last link of the e-mail → WA loop

> The universal edition ships no sub-flow image with real numbers, to avoid leaking contact details. The text version follows
> (matching `scripts/wa_bulk/` and `wa_bulk_guide.md`; numbers always come from the confirmed profile):

export `wa_targets` → template + validation (number placeholder `<phone-E164>` until you fill in your own)
→ open each chat + white-screen detection for unregistered numbers → screenshot check of the last digits → send and write back `won_channel`
→ `wa_review` channel review → trigger the next round, closing the loop.

- **Entry**: the pending list handed over by the main flow (wa_targets.json).
- **Two-number iron rule**: the small number (outreach number) = logged in for bulk sending (a ban only costs the outreach number); the main number (customer-facing) = signatures / conversations, **never bulk-sends**.
- **① List → input** (wa_bulk_sender.py convert wa_targets.json): pending → Format B template + variables; phone/brand/intro differentiated from need_tag / research.
- **validate** → `if` number format / empty message fails → fix the list / template and convert again (red dashed); `else` preview.
- **② preview (read-only, no sending)** → `if` duplicate / near-identical messages or wa.me links → rewrite {intro}, remove wa.me (wa.me in bulk sends is judged as marketing and banned) (red dashed); `else` fully differentiated → harness.
- **③ harness self-test** (test send to the small number) → `if` not received / garbled → check the whatsapp:// protocol, clean the registry key (back up HKCU\SOFTWARE\Classes\whatsapp first) (red dashed); `else` ready to send.
- **Daily quota gate**: `if` ≥200 sent today → stop, continue next day with progress; `else` enter the send loop.
- **Per-contact send loop (the core if/else)**:
  1. ④ take the next contact, Start-Process whatsapp://send?phone={phone}, wait 5 s
  2. **popup white-screen detection**: sample 9 points in a 3×3 grid at the screen centre; `if` ≥6 white (unregistered) → SKIP, record the checkpoint; `else` screenshot verification
  3. **screenshot verification**: strip non-digits and compare the last 8 digits; `if` matches the current contact → send; `else` retry (max 2) → still failing → SKIP
  4. ⑤ send: paste from a clipboard temp file + SendKeys Enter (avoids special-character corruption)
  5. ⑥ checkpoint: update wa_progress.json + daily counter (resume after a crash)
  6. **anti-ban throttle**: random 8–15 s interval per message, 30–60 s cooldown every 5
  7. `if` contacts remain → back to the quota gate (blue loop); `else` all processed → audit
- **Wrap-up**: ⑦ audit re-checks every screenshot → `if` anomalies (not delivered / wrong recipient) → resend / check individually; `else` ⑧ write back wa_status="sent"; the dashboard files it under "✅ moved to WA" next time → back to the main flow dashboard.

---

## 3. Key design principles (teaching points)

1. **Every rejection / stop has an explicit if condition**, not a hunch: competitor, duplicate send, bounce, generic mailbox, unregistered number, near-identical message — all decided up front.
2. **Failures go back, never push through**: three pre-send checks, three WA self-check gates; any failure loops back to fix, never skips.
3. **The loop repeats**: bounces replenish the pool, follow-up progression returns to scanning, bulk sends resume from checkpoints; data is always written back to support the next batch.
4. **wa.me context**: wa.me is banned in bulk sends (judged as marketing); the dashboard's "one-click open" is you manually opening one chat, which is safe — no contradiction.
5. **Two-number isolation**: bulk sends only from the small number; the main number never bulk-sends, keeping ban losses on the outreach number.

---

## 4. Loop checklist (exit and loop-back of every node)

> Criterion: every node must have both a **normal exit** (where it goes) and an **exception / loop-back** (where it returns on failure or wait). Any empty cell means the loop is not finished.

| Node | Normal exit | Exception / loop-back | Guaranteed by |
|---|---|---|---|
| New-install checklist | check 1 | — (entry) | `onboarding.py start` |
| Check 1 company profile | check 2 | required field missing → fill in (ask / apply-pack) | `config.missing_fields`, script gate |
| Check 2 kit health check | check 3 | missing file / empty shell / examples not replaced / key section missing → fill in | `config.kit_health` / `kit-check` |
| Check 3 user confirmation | Step 0 | not confirmed or profile changed → `user_confirmed` reset → back to check | `attest` (rejects placeholders / unchecked kit) |
| Data Access Layer · customer DB import | customer pool `customer_db.csv` | columns not recognised → re-import with `--map`; existing customers / do-not-contact → never into the cold pool | `data_import.py` |
| Data Access Layer · sending channel | Step 5 can really send | `test` login fails → change the client key / enable the protocol; mailbox paused → investigate then `resume` | `mail_setup.py` |
| Data Access Layer · CRM sync | CRM and customer DB consistent | pull updates existing e-mails only; push defaults to DRY_RUN | `crm_sync.py` |
| Data Triggers | matching step per queue item | outbound actions → human sign-off; `ack` when handled; rescan next day | `triggers.py` |
| Scheduler / check customer pool | four-axis replenish → Step 1 | sufficient → wait for tomorrow; bounce replenishment → back to the pool check | `schedule` / `replenish` |
| Step 0 Omni-channel Review | Step 1 | no success cases → straight to Step 1 (still reading MEMORY conclusions) | `review_success` |
| Step 1 Search Candidates | #1 check the DB first | bottleneck → change region / tier or complete e-mails → back to Step 1 | `filter --against` / `funnel` |
| #3 pending-verification pool | Step 2 | no named mailbox → pending@ placeholder, must be completed before sending | `email_guesser` / `dns_validator` |
| Step 2 Background Research | Step 3 | only S3 → need_review → user decides → Step 3 | research_guide §5.5 |
| Step 3 Need Positioning | Step 4 | violates tag_rules → not sent, handed to a human | `conflict-check` |
| Step 4 Write Content | three pre-send checks | follow-up rounds return here from the cooldown (new angle) | email_templates |
| Three pre-send checks | Step 5 | any fails → fix and back to Step 4 | `check` / `cross_brand_check` / placeholder block |
| Step 5 Send | Step 6 | outside the local window → next window; daily or warm-up limit reached → next day; bounce over threshold → mailbox paused automatically | `send_window.py` / `DAILY_LIMIT` / `mail_setup.py` |
| Step 6 Follow-up Management | four branches | no reply → back to Step 4 after the cooldown | `imap_scanner.py` / `cooldown` |
| Bounce | back to the pool for replenishment | — (permanent stop) | `mark_bounced` |
| Reply | manual follow-up → won or refused | refused → `add_blacklist` stops every channel | `mark_replied` |
| Stop generic mailboxes (4 e-mails sent) | LinkedIn / personal mailbox (manual) | no reply by Day 21 and a WA signal hit → Step 7 | social 1-3-7-21 |
| Step 7 WhatsApp Trigger | write back + `wa_review` → Step 8 | validation fails → convert again; 200 → STOP → next day; next round's list fed back | `wa_bulk_sender.py` |
| Step 8 Win Review + Kit Write-back | kit write-back → kit-check | health check fails → rewrite the matching file | `add_success` / `kit-check` |
| Re-check | back to Step 0 (next round) | — | purple return edge |

Automatic check: `python3 scripts/consistency_audit.py` verifies that commands, parameters, fields, counts, cooldown rules, status values and the social platform list agree between scripts and docs.
