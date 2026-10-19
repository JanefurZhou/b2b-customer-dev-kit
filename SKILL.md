---
name: b2b-customer-dev-kit
description: >-
  Use when the user wants to find, vet, and contact new B2B customers in any
  industry: lead search (keyword matrix, 15 discovery channels incl. customs
  data, no-login public search on 10 social platforms), S1/S2/S3 background
  research, need positioning, localized cold e-mail, DNS checks, local-window
  sending, bounce scanning, 5-step follow-up, WhatsApp hand-off, win review;
  plus a data-access layer (own customer DB and SaaS/CRM import, mailbox keys
  or MCP sending, warm-up, CRM sync) and daily data triggers with a 4-axis
  search rotation. Triggers: find customers, customer development, cold email,
  outreach, lead research, need positioning, customs data, social prospecting,
  bulk sending, bounce handling, WhatsApp bulk, customer DB import, CRM sync,
  win review, 找客户, 客户开发, 背调, 海关数据. Industry-agnostic, ships with
  no company or customer data; a mandatory install gate must pass before any
  search or send script runs. Not for consumer marketing, paid ads, or market
  sizing.
license: CC-BY-NC-4.0
compatibility: "Requires Python 3.8+ (standard library only; 3.9+ for daylight-saving-exact send windows). Network access needed for DNS/SMTP/IMAP and web search."
metadata:
  version: "3.1"
  type: "universal-template"
  onboarding: "mandatory-first-run"
---

# B2B Customer Development Kit (universal edition v3.1)

Core idea: **no coarse filtering — research every account, position its need, and pitch the matching solution; the brand name does not decide the need, research does.** Replace AI memory with a data loop, manual arithmetic with scripts, and guesses with evidence.

## ⛔ Install Gate — the first thing after installing (fail any of the three checks and every search/send script refuses to run)

This is a **universal template**: it contains no company name, product, signature, keywords, customer list or default industry. Until the gate passes, only build the profile; do not search, replenish or send.

### Anti-fabrication rules (highest priority)

- **Every key fact comes from the user or from a source the user names** (website, business card, their own words in the conversation): company name, contacts, e-mail, phone/WhatsApp, website, product claims, MOQ/price/lead time/launch date, certifications, case studies, keywords. Industry packs are method-level suggestions only; they are not user facts.
- A field is unknown → **ask the user**. Placeholder domains, guessed e-mail patterns and "plausible-looking" numbers cause bounces and mis-sends.
- **Only the user can confirm.** Run `attest` only after you have read every value back verbatim and the user has explicitly replied "confirmed". Any later change to the profile or the Soul Seven Kit breaks the content fingerprint, the scripts block again, and you must read back and confirm again.

### Step one: run the first-install checklist

```bash
python3 scripts/onboarding.py start      # one screen: what to fill in right after installing + the current status of each item (read-only)
python3 scripts/onboarding.py init       # create a blank config/company_profile.json + soul_seven_kit/ (never overwrites existing files)
```

### The three checks

| Check | What to fill in | Command | When it fails |
|---|---|---|---|
| Check 1 Required profile fields | `business.industry`, `business.offer_type`, `company.brand_display`, `contact.founder_name`, `contact.email`, `product.one_liner_en`, `product.primary_keywords` (≥3), `product.differentiators` (≥2), `targeting.buyer_titles` (≥1), `data_sources.customer_db` (`imported` / `crm_sync` / `none`; this skill ships no customer database) | `ask` (field by field) or first `packs` → `pack <id>` → `apply-pack <id>` to apply an industry method layer (13 industry packs) | lists the missing fields |
| Check 2 Soul Seven Kit health check | Seven files in `soul_seven_kit/`: IDENTITY (role / serves / red lines) · SOUL (tone / priorities / decisions) · AGENTS (SOP / human confirmation / never do) · TOOLS (when to use / how to use / when it breaks) · MEMORY (conclusions / to-do / next step) · USER (reporting / approval / sensitive) · HEARTBEAT (runs / completion rate / errors), each with three to five lines of real content | `kit-check` (missing file / empty shell / unreplaced "(e.g. …)" examples / missing key section / placeholders — any one fails) | lists the specific problems in each file |
| Check 3 Confirmation by the user | The AI reads the profile and the kit summary back verbatim; the user explicitly replies "confirmed" | `check` (returning `FILLED_NOT_CONFIRMED` is normal) → `attest` | `REFUSED` / `CHANGED_AFTER_CONFIRM` |

Fill-in reference for the kit (customer-development role, method-level wording; company facts come from the user): `references/soul_kit/fill_reference_customer_dev.md`. On first install MEMORY / HEARTBEAT may honestly say "first install, no data yet".

Recommended right away (not blocking, but directly affects results; `start` shows each item): `targeting.target_regions`, `targeting.reference_brands`, `offer.key_facts`, `offer.entry_offer`, `rules.local_send_window` (default `09:00-11:00,14:00-16:00`), `search.social_platforms` (empty = all 10 enabled), SMTP environment variables (only needed for scripted bulk sending).

**Contact-details rule**: use only contact details the user has confirmed. SMTP/IMAP passwords are keys and live only in environment variables (`SMTP_HOST/PORT/USER/PASS`, `IMAP_*`), never in the profile or in messages. Full interview script: `references/onboarding_questions.md`.

### Data Access Layer (set up right after install; `start` shows the status of each item)

| What to connect | Command | Notes |
|---|---|---|
| Own customer DB (required declaration at install) | `data_import.py inspect <Excel/CSV>` → `import --relation existing_customer\|prospect --source own:excel` | Everything lands in `$B2B_DATA_DIR/customer_db.csv`; English and Chinese column names are recognised automatically, `--map` overrides; existing customers / do-not-contact never enter the cold pool |
| Trade SaaS / customs / CRM exports | Drop into `data/inbox/` → `triggers.py scan` raises a notice → import through the same entry | Integration paths and verified official APIs/MCPs: `references/saas_integration_guide.md` |
| Sending route | `mail_setup.py providers` → `env <provider> --user <mailbox>` → `test` (login only, no sending) | Business-mailbox client keys / hosted multi-mailbox + warm-up ramp + automatic bounce pause / MCP connector drafts: `references/mail_setup.md` |
| CRM sync | `crm_sync.py export --target hubspot\|salesforce\|okki\|fumeng\|generic` · `pull` · `push-hubspot` · `mcp-payload` | CSV works with any CRM; HubSpot API and MCP are dry-run by default |
| Data Triggers | `triggers.py scan [--apply-safe]` | pool low / new import / follow-up due / new reply / bounce spike / WA lead / warm-up step / CRM sync due / weekly review → `reports/trigger_queue.json`; every outbound action needs human sign-off: `references/data_access_and_triggers.md` |

## Industry Adaptation

The loop is the same in every industry; only three things change, all in the profile, none in the code:

| What changes | Profile section | Example: parts factory → SaaS → consultancy |
| --- | --- | --- |
| Who to find | `targeting` | OEM buyer → CTO → founder |
| Where to find them | `search` + `business.offer_type` | customs / trade shows → review sites / job posts → tenders / directories |
| How to start with a low commitment | `offer` | sample → 14-day trial → free diagnosis |

Research produces two tags: `need_tag` (which of your lines the customer needs; values defined by the user in `positioning.need_tags`) and `solution_tag` (the customer's decision driver, 11 fixed cross-industry values: `compliance`, `sustainability`, `quality_upgrade`, `cost`, `speed`, `low_commitment`, `innovation`, `exclusive_custom`, `one_stop`, `dedicated_service`, `strategic_scale`). Hooks are chosen by `solution_tag`; legacy v1 tags are mapped automatically. 13 industry packs, terminology map and 4 fictional example profiles: `references/industry_adaptation_guide.md`.

## When to Use

- Building systematic B2B acquisition from zero in any industry: finding customers, widening channels (customs data, trade shows, tenders, hiring signals, competitor reverse-lookup, public search on 10 social platforms).
- Background research and need positioning: need_tag / solution_tag, evidence grading, cross-brand de-dup, tag-conflict correction.
- Writing and sending: multilingual localised cold e-mail, DNS/MX validation, e-mail guessing, batch sending by the recipient's local time.
- Follow-up and review: bounce scanning, 5-level cooldown follow-up, social 1-3-7-21, WhatsApp conversion, success cases and weekly kit review.

### When NOT to use

- Hot leads / customers who already replied / unconverted enquiries → hand to a person for one-to-one follow-up and tell the user first.
- Consumer marketing, paid ads, SEO, pure market sizing; lists with no lawful basis for contact.
- Quotes, payment reminders, contract terms → this skill only does development and follow-up; the user handles those.
- Gate not `READY`, or the user has not yet approved the current draft batch → sending stays locked.

## Process (Install Gate + Step 0 + seven steps + close-out)

Full loop flowchart: `references/assets/sop_flowchart.png` (PDF with the same name); exits and loops of every node: `references/sop_flowchart.md` section 4.

```
Install Gate (start→init→profile→kit-check→check→attest=READY)
  ▸ Data Access Layer          → data_import · mail_setup · crm_sync → customer pool customer_db
  ▸ Data Triggers (daily)      → triggers.py scan → enter the matching step from the queue (outbound actions need human sign-off)
  ▸ Step 0 Omni-channel Review → winning patterns + WA review + last week's kit write-back conclusions
  ▸ Step 1 Search Candidates   → queries · channels(15) · social(public search on 10 platforms)
      └ Three Iron Rules of Search → filter --against DB lookup · funnel diagnosis · pending-verification pool
  ▸ Step 2 Background Research → 5 sources + 3 research questions + S1/S2/S3 (S3 only → need_review)
  ▸ Step 3 Need Positioning    → need_tag + solution_tag (tag_rules conflict → human)
  ▸ Step 4 Write Content       → whole e-mail in the native language · ≤120 words · plain text · S1/S2 facts only
  ▸ Step 5 Send                → three pre-send checks → DRY_RUN → user approval → send inside the recipient's local window
  ▸ Step 6 Follow-up Management → bounce / reply / won / no-reply branches; e-mail 3/3/10 days; social 1-3-7-21
  ▸ Step 7 WhatsApp Trigger    → convert → validate → preview → harness → send → audit → wa_review
  ▸ Step 8 Win Review + Kit Write-back → add_success → review → weekly write-back → kit-check → back to Step 0
```

1. **Gate + data access** — `python3 scripts/onboarding.py check` = `READY`; customer DB imported as declared; sending route passes `mail_setup.py test`; run `triggers.py scan` first every day.
2. **Step 0 Omni-channel Review** — `csv_ops.py review_success`, `wa_review.py review`; read this week's conclusions in `soul_seven_kit/MEMORY.md` as the starting point for this round.
3. **Step 1 Search Candidates** — `search_customers.py queries` (keyword matrix) · `channels` (15 discovery channels; no-registration customs path in `references/customs_data_guide.md`) · `social` (login-free public search on 10 social platforms + 30 procurement-chain titles; playbooks in `references/social_media_playbooks.md`). The script only generates public search queries; actions that need a login (connection requests, DMs, joining groups) are the user's own manual decision. All results go through `filter --against <customer_db.csv>` (DB de-dup + funnel diagnosis + pending-verification pool). Self-replenishing pool: `replenish` / `schedule` rotate on four axes — Depth d1 companies → d2 decision makers → d3 deep-mining the existing pool (fastest) · Reach regions near to far · Height customer tier high to low · Breadth core → wide → max (slowest) (`references/self_replenishing_engine.md`).
4. **Step 2 Background Research** — every conclusion carries an evidence grade and source: at least 1 S1 or 2 independent S2 before setting a tag; S3 only → `need_review` for the user to decide (`references/research_guide.md` §5.5).
5. **Step 3 Need Positioning** — need_tag decides which line to pitch, solution_tag decides the hook; `conflict-check --against <pool.csv>` only flags conflicts, never changes data.
6. **Step 4 Write Content** — `references/email_templates.md`; placeholders are filled only from `product.*` / `offer.*`; the senders block any leftover `<...>` / `{...}`.
7. **Step 5 Send** — three pre-send checks (mailbox ✓ de-dup `csv_ops.py check` / `cross_brand_check` ✓ notes ✓) → `DRY_RUN=1` produces a per-e-mail report → **explicit user approval** → `decision_maker_sender.py` (or `batch_sender.py`; three sending routes: single mailbox key / hosted multi-mailbox rotating under warm-up caps / `mail_setup.py mcp-export` for a connector to draft). Every e-mail carries a `List-Unsubscribe` header and an opt-out line. Contacts with `region`/`tz` are sent only inside the recipient's local weekday window; outside it they are deferred (`send_window.py table --me <your tz>` converts live, daylight saving included). ≤200 e-mails per day, 30-second interval.
8. **Step 6 Follow-up Management** — 24–48 hours after sending, scan bounces/replies once: `DRY_RUN=1 imap_scanner.py` to see what is detected, then write back for real (mailbox opened read-only); `csv_ops.py cooldown <email>` computes the 5-level cooldown (`followup_count` = e-mails sent − 1: after 1 / 2 / 3 e-mails wait 3 / 3 / 10 days; after 4 e-mails → stop generic mailboxes, LinkedIn / personal mailbox only; 5 or more → stop e-mail entirely, move to Step 7); social DMs on 1-3-7-21 (manual); one channel per customer per day.
9. **Step 7 WhatsApp Trigger** — when a trigger signal fires: `wa_bulk_sender.py convert → validate → preview → harness → send → audit` (two-number isolation; `send` paces itself at random 8–15 s intervals and a 30–60 s cooldown every 5 messages; the daily 200-message counter forces STOP); details in `references/wa_bulk_guide.md`.
10. **Step 8 Win Review + Kit Write-back** — deal won → the AI proposes evidence-backed pain-point candidates → the user confirms → `add_success --won_channel email|wa`; `review_success` / `email_dashboard.py` / `wa_review.py --compare-email` for omni-channel attribution; every week write the mistakes back into the matching kit file per `references/soul_kit/weekly_writeback.md` → `kit-check` → back to Step 0.

**Gate scope**: commands that search, send, open WhatsApp or really push to a CRM (`search_customers.py`, `batch_sender.py`, `decision_maker_sender.py`, `wa_bulk_sender.py screenshot/send/harness/audit`, `crm_sync.py push-hubspot` in real-push mode) all refuse to run until the gate is `READY` and the content fingerprint matches. Read-only or local preparation tools (`validate`/`preview`/`template`/`convert`, `dns_validator.py`, `email_guesser.py`, `send_window.py`, the dashboards, `data_import.py`, `mail_setup.py`, `triggers.py`, `crm_sync.py export/pull`) work before the profile exists, so you can import the customer DB and set up the mailbox during install. When the gate blocks, the error says which check failed.

**Safety baseline**: credentials live only in environment variables (the hosted-mailbox file stores variable names only); CRM push is dry-run by default; triggers are read-only, the only automatic action is pausing a mailbox on a bounce spike; SMTP only on 465/587+STARTTLS, IMAP only over IMAPS; sending, bounce scanning and DNS validation all support `DRY_RUN=1`; bounce scanning opens the mailbox read-only; generic mailbox prefixes are blocked automatically; bounces are blacklisted permanently; scripts never rewrite customer data on their own; social platforms are public search only.

Data access and triggers: `references/data_access_and_triggers.md`; data structures and CSV operations: `references/csv_guide.md`; full SOP: `references/SOP.md`; unattended scheduling and the human/machine boundary: `references/automation_setup.md`; version history: `CHANGELOG.md`.

### Check axes (every account / every e-mail batch passes these 6 axes)

- **Target fit** — the business matches the profile's product/service and customer tier, and hits none of the exclude_keywords.
- **Reachable contact** — a real, traceable named decision-maker mailbox that passes DNS/MX.
- **Demand hook** — a concrete buying signal, solution_tag backed by S1/S2 evidence, hook supported by the profile's differentiators and offer.
- **Localization** — language, greeting and sending window match the recipient's country.
- **Deliverability** — daily cap, per-contact cooldown and local window all satisfied.
- **Approval & signature** — the batch is explicitly approved by the user; the signature contains only user-confirmed contact details.

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "Let's guess a company/product to get started." | The template is deliberately blank; an invented identity or contact details destroy deliverability and trust. Pass the gate first. |
| "Just flip filled to true in the kit." | `kit-check` reads the real content: empty shells, unreplaced "(e.g. …)" examples and missing key sections all fail. |
| "Confirmed once; later profile edits don't need confirming." | The content fingerprint stops matching and the scripts block again; every change must be read back and confirmed. |
| "`info@`/`sales@` count towards the customer pool." | Generic mailboxes mostly bounce or go unread; only traceable named contacts count towards pool health. |
| "Someone mentioned it in a comment, so that's the need." | That is a weak S3 signal; it can only be marked need_review for the user to decide. |
| "To save time, send before approval." | Outbound e-mail is a high-risk external action; every batch needs explicit user approval. |
| "Mass friend requests / DMs on social would be faster." | This skill only does login-free public search; logged-in actions are the user's decision and must follow platform terms. |
| "Send whenever it's convenient for me." | Send inside the recipient's local weekday window; the script defers recipients outside it. |
| "The bounce might be temporary, send again." | Bounces are blacklisted permanently; resending damages sender reputation. |
| "Use the full quota on a new mailbox from day one." | Hosted mailboxes ramp up through warm-up tiers (adjustable defaults); a round with bounces above the threshold pauses automatically. |
| "Any e-mail in the customer DB can be cold-contacted." | Existing customers, do-not-contact and competitors never enter the cold pool; SaaS-exported addresses still need DNS validation and research. |

## Red Flags

- A search / send / WhatsApp-send command running while the profile is missing, `configured=false`, or the content fingerprint does not match.
- "(e.g. …)" example lines still in the kit, yet `attest` has already run.
- A draft containing an e-mail / phone / website the user never confirmed, or leftover `[...]` / `<...>` placeholders.
- A guessed `export@/info@` treated as a verified lead.
- An account with S3-only evidence given a specific need_tag and pitched aggressively.
- The same number appearing twice in the WhatsApp list and entering harness/send; more than 200 messages in one day.
- Sending outside the local window, or breaking the per-contact cooldown; two channels used for one customer on the same day.
- SMTP/IMAP keys written into the profile, scripts, logs or `config/mailboxes.json`.
- A paused hosted mailbox still sending; `approved=false` items executed in a CRM push or MCP sending list.
- A draft batch sent before the user's explicit approval.

## Role contract

Workflow prompt audit: N/A — single agent context; the bundled scripts make no model calls and there is no multi-step prompt chain.

- Runtime mode: single_context · Role mode: single_role · Entry role: `b2b-outbound-owner` (machine-readable copy: `references/role-contract.json`)
- Role: B2B outbound customer-development owner
- Purpose: Run one evidence-bounded outbound loop from onboarding gate to search, vetting, positioning, approved sending, follow-up, WhatsApp hand-off, and review for the user's own business.
- Inputs:
  - User-confirmed config/company_profile.json
  - Seven-kit files in soul_seven_kit/ that pass kit-check
  - Public search results and the user's customer CSV files
- Responsibilities:
  - Gate every task on onboarding check = READY before search or sending.
  - Vet each account with S1/S2 evidence and set need_tag and solution_tag from research.
  - Prepare localized drafts and DRY_RUN reports for the user to approve before any send.
  - Write every send, bounce, reply, and WhatsApp result back through csv_ops.py.
- Out of scope:
  - Inventing company facts, contacts, emails, phone numbers, prices, or case studies.
  - Logging in to, registering on, or automating actions inside social platforms.
  - Sending quotes, payment reminders, or contract terms.
- Decision authority:
  - May choose search queries, channels, and candidate order within the confirmed profile.
  - May mark an account need_review when evidence is only S3.
  - May defer a send that falls outside the recipient's local window.
- Outputs:
  - Candidate pool with funnel diagnosis
  - Research notes with evidence grades
  - Approved draft batch and send report
  - Follow-up, WhatsApp, and review summary
- Acceptance tests:
  - onboarding.py check prints READY and kit-check passes 7/7.
  - Every sent address is a named, DNS-validated contact that passed csv_ops.py check.
  - Every tag and email claim maps to an S1 or S2 source recorded in notes.
  - consistency_audit.py reports FAIL 0.
- Stop conditions:
  - Stop and ask the user when a required fact is missing or the gate is not READY.
  - Stop all actions immediately when the user says pause or stop.
  - Stop sending for the day at the daily limit or after a repeated send failure.
- Hand-off to:
  - User approval of each draft batch
  - User handling of replies, quotes, and contracts

## Verification

Before closing a development round, confirm each item:

- [ ] `python3 scripts/onboarding.py check` prints `READY` and `kit-check` is 7/7.
- [ ] The default channels and platforms from `search_customers.py channels` / `social` fit the user's industry.
- [ ] Every new lead has a real, traceable named contact; research evidence reaches S1 or 2×S2; weak signals are marked need_review.
- [ ] Drafts are localised and quote only facts; the batch was explicitly approved by the user; the `DRY_RUN` report was checked e-mail by e-mail.
- [ ] Addresses passed DNS/MX; sending happened inside the recipient's local window; cooldown and daily cap were respected.
- [ ] Bounces are blacklisted; send / blacklist CSVs are written back; the WhatsApp list passed `validate` (no duplicates, no unfilled placeholders).
- [ ] Dashboard / funnel numbers were reported, separating target from non-target accounts rather than raw counts only.
- [ ] Human sign-off items from `triggers.py scan` were handled and `ack`ed; `crm_sync.py` is aligned with the CRM (if used).
- [ ] This week's kit write-back is done and `kit-check` passes (if it still fails after two fix attempts, stop and hand the listed problems to the user); `python3 scripts/consistency_audit.py` reports FAIL 0.

## Record schema (where state lives)

All state is plain CSV under `B2B_DATA_DIR` (default `data/`), written only through `csv_ops.py`; field lists are the `*_FIELDS` constants in `scripts/csv_ops.py` and are documented in `references/csv_guide.md`:

- `data/sent_history.csv` — `email, brand, send_date (YYYY-MM-DD), subject, need_tag, followup_count, last_followup_date, status (sent / bounced / replied / permanent_stop), notes`
- `data/blacklist.csv` — `email, brand, reason, date`; `data/wa_contacts.csv` — `wa_number, brand, contact_name, source_date, status`; `data/success_cases.csv` — `email, brand, contact, region, need_tag, … hook_type, source_channel, won_channel, … notes` (full list in csv_guide §3)
- `data/pipeline.csv` (reserve pool), `data/customer_db.csv` (imported DB), `data/mailbox_usage.csv`, `data/crm_sync_log.csv`, `reports/trigger_queue.json`
- Weekly conclusions: `soul_seven_kit/MEMORY.md` (section "Conclusions this week"), rewritten by the user at Step 8.
