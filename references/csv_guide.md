# CSV data layer guide

> This document supplements SKILL.md with CSV field definitions, script parameters and FAQs.

> **Encoding**: all CSVs are written as UTF-8 with BOM so Excel opens them by double-click; reading works with or without BOM. Import legacy GB18030 sheets with `data_import.py` first.

## 1. File structure

```
data/
├── sent_history.csv   — sending records (written after every send)
├── blacklist.csv      — dead mailboxes / do-not-send list
├── wa_contacts.csv    — WhatsApp contacts
├── success_cases.csv  — success cases (full customer file + confirmed pain points + acquisition channel)
└── pipeline.csv       — reserve pool (researched customers in reserve)
scripts/
├── csv_ops.py         — CSV operations (CRUD + cooldown + de-dup + reserve pool)
└── email_dashboard.py — e-mail tracking dashboard (with the success-case review module)
```

## 2. CSV field definitions

### 2.1 sent_history.csv

| Field | Type | Description | Example |
|------|------|------|------|
| email | string | recipient e-mail (lower case) | buyer@brand.example |
| brand | string | customer company / brand | BrandName |
| send_date | date | sending date | 2026-06-07 |
| subject | string | e-mail subject | <your one-line value angle> for <Brand> |
| need_tag | enum | need tag (set by research; the set of line tags is defined for your industry at install) | <line_a> / <line_b> / multi / unknown |
| followup_count | int | follow-up count (0 = first e-mail) | 0 |
| last_followup_date | date | last follow-up date | 2026-06-07 |
| status | enum | Current status | sent / bounced / replied / permanent_stop (cooldown is not stored; the `cooldown` command computes it from dates) |
| notes | string | notes (research findings / customer feedback / special requests) | customer said contact again in Q3; needs ISO 9001 certificate |

**need_tag values**:
> need_tag = **which** of your product / service lines the customer needs; values are your own from `positioning.need_tags` (consistent with `product_knowledge.md` §1).
- `<line_a>` / `<line_b>` …: your own product / service lines
- `multi`: several lines / overall solution
- `review`: contradictory signals, awaiting manual review
- `unknown`: insufficient research, conservative generic pitch

"What the customer cares about most" is not in need_tag but in `solution_tag` (11 generic decision drivers, see `industry_playbooks.md` §1),
stored in the `solution_tag` field of the sending JSON or in notes.

**notes field**:
- records research findings, customer feedback, special requests, follow-up agreements
- several notes separated by `; `
- `csv_ops.py check <email>` returns every historical note
- notes must be checked before sending and the strategy adjusted accordingly

**status transitions**:
```
sent → bounced / replied
sent → permanent_stop (moved to WA / permanent stop)
("in cooldown" is not a stored state: `csv_ops.py cooldown <email>` computes in_cooldown / action live)
bounced → added to blacklist automatically
```

### 2.2 blacklist.csv

| Field | Type | Description | Example |
|------|------|------|------|
| email | string | blocked e-mail | dead@brand.example |
| brand | string | customer company / brand | BrandName |
| reason | string | reason | bounce / domain_dead / closed / wa_only / non_target |
| date | date | confirmation date | 2026-06-07 |

**reason values**:
- `bounce`: e-mail bounced (mailbox missing / full)
- `domain_dead`: the customer's website is offline
- `closed`: the customer is out of business
- `wa_only`: moved to the WA channel, e-mail stopped
- `non_target`: not part of the target customer group

### 2.3 wa_contacts.csv

| Field | Type | Description | Example |
|------|------|------|------|
| wa_number | string | WhatsApp number | +<country-code-number> (E.164) |
| brand | string | customer company / brand | BrandName |
| contact_name | string | contact | John |
| source_date | date | entry date | 2026-06-07 |
| status | enum | status | pending / wa_only / replied / self |

**status values**:
- `pending`: WA number obtained, not contacted yet
- `wa_only`: WA channel confirmed, e-mail stopped
- `replied`: reply received on WA
- `self`: the customer added us

## 3. Commands of csv_ops.py

### 3.1 Environment

```bash
# data directory (default data/)
export B2B_DATA_DIR=data
```

### 3.2 check — mandatory before sending (most used)

**Syntax**: `python3 scripts/csv_ops.py check <email>`

**Returned JSON fields**:
| Field | Description |
|------|------|
| email | queried e-mail |
| sent | sending records of this e-mail |
| sent_count | number of sends |
| blacklisted | blacklisted? |
| blacklist_reason | blacklist reason |
| wa_only | WA-only? |
| can_send | sendable now? |
| in_cooldown | in cooldown? |
| cooldown_remaining | cooldown days left |
| **notes** | **every historical note of this e-mail (chronological)** |

**When**: before every send; one command does de-dup + notes.

### 3.3 add_sent — record a send

**Syntax**: `python3 scripts/csv_ops.py add_sent <email> <brand> <subject> <need_tag> [notes]`

**Parameters**:
- `email`: recipient
- `brand`: customer company / brand
- `subject`: subject (quote when it contains spaces)
- `need_tag`: need tag (set by research; enumeration defined for your industry at install)
- `notes`: optional notes (research findings / special requests)

**Computed automatically**:
- `send_date`: today
- `followup_count`: from existing records (0 = first, 1 = second e-mail …)

### 3.3.5 add_note — add a note

**Syntax**: `python3 scripts/csv_ops.py add_note <email> <note>`

**Purpose**: appends a note to the latest sending record of this e-mail. Several notes separated by `; `.

**When**:
- research found something to remember for the next e-mail
- the customer's reply mentioned a special request ("contact again in Q3", "needs compliance documents")
- recording bounce reasons, follow-up agreements

### 3.4 add_blacklist — add to the blacklist

**Syntax**: `python3 scripts/csv_ops.py add_blacklist <email> <brand> <reason>`

### 3.5 add_wa — add a WA contact

**Syntax**: `python3 scripts/csv_ops.py add_wa <wa_number> <brand> <contact_name> [status]`

**Parameters**: `status` optional, default `pending`

### 3.6 mark_bounced — mark a bounce

**Syntax**: `python3 scripts/csv_ops.py mark_bounced <email>`

**Automatic actions**:
1. status in sent_history.csv set to `bounced`
2. added to blacklist.csv (reason=bounce)

### 3.7 mark_replied — mark a reply

**Syntax**: `python3 scripts/csv_ops.py mark_replied <email>`

### 3.8 mark_wa_only — move to the WA channel

**Syntax**: `python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>`

**Automatic actions**:
1. status in sent_history.csv set to `permanent_stop`
2. record added to wa_contacts.csv (status=wa_only)

### 3.9 cooldown — cooldown check

**Syntax**: `python3 scripts/csv_ops.py cooldown <email>`

**Cooldown rules**:
| followup_count | Cooldown days | Description |
|----------------|---------|------|
| 0 | 3 | wait 3 days after the 1st e-mail |
| 1 | 3 | wait 3 days after the 2nd e-mail |
| 2 | 10 | wait 10 days after the 3rd e-mail |
| 3 | Stop generic mailboxes permanently | from the 4th e-mail on: LinkedIn / personal mailbox only |
| ≥4 | Stop sending permanently | from the 5th e-mail on: WA / personal mailbox only |

**Return fields**:
| Field | Description |
|------|------|
| can_followup | follow-up allowed? |
| in_cooldown | in cooldown? |
| cooldown_remaining | cooldown days left |
| next_eligible_date | next sendable date |

### 3.10 cross_brand_check — cross-brand de-dup

**Syntax**: `python3 scripts/csv_ops.py cross_brand_check <domain>`

**Parameters**: `domain` as `brand.example` or `@brand.example`

**Return fields**:
| Field | Description |
|------|------|
| found | match found? |
| matches | number of matching records |
| brands | brands already contacted |

### 3.11 stats — statistics

**Syntax**: `python3 scripts/csv_ops.py stats`

**Return fields**: sent_total, sent_by_status, blacklist_total, wa_contacts_total, unique_brands, unique_emails

### 3.12 success_cases.csv — success cases

**Fields**:
| Field | Type | Description | Example |
|------|------|------|------|
| email | string | customer e-mail | john@brand.example |
| brand | string | customer company / brand | BrandName |
| contact | string | contact name | John Doe |
| region | string | region / country | US |
| need_tag | string | need tag (your own product / service line) | line_a |
| first_sent_date | date | first sending date | 2026-06-15 |
| reply_date | date | reply date | 2026-06-18 |
| order_date | date | order date | 2026-07-01 |
| order_amount | float | deal amount (USD) | 15000 |
| success_points | string | success points (pain points confirmed by the user) | 1. personalised hook 2. named decision-maker sending |
| email_subject | string | e-mail subject | Documented valves for BrandName |
| hook_type | string | hook type (= solution_tag, one of the 11 generic decision drivers) | compliance |
| language | string | e-mail language | EN/IT/DE/FR/ES/JP/NL/PT |
| source_channel | string | acquisition channel | LinkedIn / trade show / tender / competitor reverse-lookup |
| won_channel | string | winning channel (email / wa; empty = untagged, wa_review falls back to brand matching) | email |
| company_info | json | company background | {"founded":"1990","size":"50-100"} |
| contact_phone | string | contact phone | +1-555-1234 |
| company_address | string | company address | 123 Main St, NY |
| website | string | website | https://brand.example |
| social_linkedin | string | LinkedIn | https://linkedin.com/company/brand |
| social_instagram | string | Instagram | @brand |
| social_facebook | string | Facebook | facebook.com/brand |
| social_twitter | string | Twitter/X | @brand |
| whatsapp | string | WhatsApp number | +1-555-1234 |
| products_info | json | customer business info (research conclusion) | {"main_offerings":"...","current_solution":"...","need_tag":"line_a"} |
| notes | string | notes | |

**Commands**:
```bash
# add a success case (with the full customer file)
python3 scripts/csv_ops.py add_success <email> <brand> <contact> <order_amount> <success_points> \
  --region US --need_tag line_a --source_channel LinkedIn \
  --company_info '{"founded":"1990"}' --whatsapp "+1-555-1234"

# list success cases (filter by region / need tag / channel)
python3 scripts/csv_ops.py list_success [--region US] [--need_tag line_a] [--channel LinkedIn]

# review success cases (distil success points before starting development)
python3 scripts/csv_ops.py review_success
```

### 3.13 pipeline.csv — reserve pool ⭐

**Fields**:
| Field | Type | Description | Example |
|------|------|------|------|
| email | string | customer e-mail | buyer@brand.example |
| brand | string | customer company / brand | BrandName |
| region | string | region / country | US |
| need_tag | string | need tag (research done; values from positioning.need_tags) | line_a |
| status | enum | status | ready / pending / disqualified / used |
| priority | enum | priority | HIGH / MEDIUM / LOW |
| research_done | bool | research done? | true |
| added_date | date | date added to the pool | 2026-07-09 |
| notes | string | notes | research done, needs compliance documents |

**status values**:
- `ready`: search + research + need positioning done, sendable
- `pending`: search only, research and positioning pending
- `disqualified`: disqualified (failed verification / blacklisted / closed)
- `used`: taken from the pool for sending

**Commands**:
```bash
# reserve pool status (enough reserve?)
python3 scripts/csv_ops.py pipeline_check
# returns: ready_count, pending_count, shortage, need_supplement

# add to the pool (research done)
python3 scripts/csv_ops.py add_pipeline <email> <brand> <region> <need_tag> [priority] [notes]

# list the pool (filter by status / region)
python3 scripts/csv_ops.py list_pipeline [--status ready] [--region US]

# take from the pool for sending (marks used)
python3 scripts/csv_ops.py use_pipeline <email>
```

**Reserve pool rules**:
- minimum reserve: 100 accounts (7-day reserve); recommended 300–500 (monthly reserve)
- check frequency: full check Sunday 22:00; confirm availability before each daily send
- replenish trigger: below 50% of the reserve → replenish immediately
- cycle: reserve → daily consumption → reserve hits 0 → replenish task starts → replenish done

## 4. FAQ

**Q: What if a CSV file does not exist?**
A: The scripts create it. On first run with an empty data/ directory, add_sent / add_blacklist / add_wa create the CSV with its header.

**Q: Several e-mails of one brand?**
A: check queries by e-mail. Different e-mails of one brand are separate records, but cross_brand_check de-dups by domain and catches different mailboxes under the same domain.

**Q: Can the cooldown days be changed?**
A: Yes. Edit the `COOLDOWN_RULES` constant in csv_ops.py (default `{0: 3, 1: 3, 2: 10}` days); the e-mail counts for stopping generic mailboxes / stopping entirely are `MAX_GENERIC_FOLLOWUP` (default 3) and `MAX_TOTAL_FOLLOWUP` (default 4). Update the table in §3.9 after changing them.

**Q: Can the LLM read / write the CSV directly?**
A: No. LLM CSV parsing is error-prone (quotes / commas / line breaks) and session state is not persistent. Always use the scripts.
