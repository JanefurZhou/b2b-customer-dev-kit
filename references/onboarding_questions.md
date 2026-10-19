# First-install interview checklist (Onboarding Interview)

This skill is a **de-identified, industry-agnostic template** with no real company information and no default industry. On first load the AI must use this checklist
to collect each item from the user, write it into `config/company_profile.json`, then run
`python3 scripts/onboarding.py check` until it prints `READY`. **Never invent any value on the user's behalf**;
optional items the user cannot answer yet may stay empty, but every "required" item must be obtained.

## How to use

0. `python3 scripts/onboarding.py start` first shows the "what to fill in right after installing" list (three checks + recommended items, read-only).
1. `python3 scripts/onboarding.py init` creates a blank profile (never overwrites an existing one).
   Optional: ask which kind of business the user is in, `onboarding.py packs` lists the 13 industry packs, then
   `apply-pack <id>` pre-fills method-level suggestions (tiers / roles / channels / intent terms), which you then rewrite with the user in their own words.
   See `industry_adaptation_guide.md`.
2. Ask in the order below; when one sentence from the user yields several fields, fill them all at once to reduce back-and-forth.
3. Edit the JSON directly, or use `python3 scripts/onboarding.py ask` for guided questions.
4. After the kit is written run `python3 scripts/onboarding.py kit-check` (7/7 to pass); when everything is done run `python3 scripts/onboarding.py check`,
   read it back to the user, and after confirmation run `attest`; only `READY` allows later tasks. Changing the profile or the kit after confirmation requires reading back, confirming and `attest` again.

## Required fields (check blocks on these)

| Field | Question to ask | Used for |
| --- | --- | --- |
| `business.industry` | In one sentence, which industry / segment are you in? (e.g. "industrial valve export", "HR SaaS", "cross-border freight forwarding") | picking a pack, review framing |
| `business.offer_type` | Do you sell physical products, software, people-based services, or project-based work? (physical_product / software / service / project / other) | default search channels |
| `company.brand_display` | Which company / brand name goes in your e-mail signature? | signature, subject |
| `contact.founder_name` | Sender name for outbound e-mail (signature)? | signature |
| `contact.email` | Which mailbox sends outbound e-mail? | sender identity, replies |
| `product.one_liner_en` | One English sentence saying what you sell? (e.g. `<your one-line positioning>`) | first line of the e-mail, positioning |
| `product.primary_keywords` | Which ≥3 English terms would customers use to search for your kind of product / service? | core of the query matrix |
| `product.differentiators` | Your ≥2 hardest, verifiable differences from others? (performance / process / results / speed / credentials / service …) | evidence section of the e-mail |
| `targeting.buyer_titles` | ≥1 decision role you want to reach? (procurement manager / CTO / HR director / owner …) | role terms, query matrix |

## Strongly recommended (activation works without them, but positioning will be coarse)

- `company.website` / `product_site`: main site and product site (separate when different).
- `contact.whatsapp`: WhatsApp in international format; `contact.signature_lines`: extra signature lines.
- `product.alt_keywords`: synonyms / category expansion terms.
- **`offer.*` (deal-entry layer; every e-mail / WhatsApp script reads from here, strongly recommended)**:
  - `entry_offer`: how does a customer start with low risk? (free sample / 14-day trial / free diagnosis / pilot / trial shipment / mock-up)
  - `cta_question`: the English closing question of the e-mail? (e.g. "Open to a 20-minute demo next week?")
  - `key_facts`: 2–4 short publishable facts (MOQ / go-live time / certification name / delivery time / customer count — facts, not adjectives)
  - `proof_points`: publishable cases (customer-authorised or de-identified); `repeat_hook`: one sentence for repeat-order follow-ups with existing customers
  - Physical goods may keep the legacy fields `product.moq` / `sample_lead_time` / `bulk_lead_time`; they are used automatically when `key_facts` is empty.
- `targeting.channel_keywords`: customer-type terms (distributor / contractor / startup /
  clinic chain / importer / agency …).
- `targeting.customer_levels`: custom customer tiers, each
  `{name, desc, keyword_suffixes}`; the search script builds per-tier term lists from them.
- `targeting.target_regions`: target markets (ISO country codes, e.g. USA/GB/DE).
- `targeting.languages`: sending languages (en/fr/de/es/it …) for localisation.
- `targeting.exclude_keywords`: terms that are **clearly not customers** in your industry (consumers,
  repair, second-hand, tutorials, job boards, a category you do not serve); excluded by search and the gate.
- `targeting.competitor_markers`: identifying terms of peers / competitors (manufacturer / agency /
  software vendor …) so competitors are not treated as customers.
- `positioning.need_tags`: your product / service line tags (need_tag values during research);
  for rules like "line X and customer type Y are mutually exclusive", write `conflict_groups` / `tag_rules`.
- `rules.*`: `daily_limit`, `local_send_window` (recipient-local window, default `09:00-11:00,14:00-16:00`;
  `send_window.py table --me <your tz>` shows each market in your local time), `same_contact_cooldown_hours`,
  `require_confirmed_email`, `notes` (custom red lines).
- `search.social_platforms`: which social platforms to use for login-free public search (linkedin / instagram / facebook / youtube /
  tiktok / pinterest / x / threads / whatsapp / lemon8; empty = all 10), see `social_media_playbooks.md`.

## Part B: Soul Seven Kit (`soul_seven_kit/`, 7 files, all required)

`onboarding.py init` has copied the 7 templates from `references/soul_kit/` into
`soul_seven_kit/`. Fill 3–5 concrete lines per file (replace the "(e.g. …)" examples with your real practice), then change
`filled: false` at the top to `filled: true` and run `onboarding.py kit-check` — flipping filled without real content does not pass.
Fill-in reference: `soul_kit/fill_reference_customer_dev.md`. These 7 files define "the AI doing the work" itself,
complementing the business facts of Part A:

| File | What to ask the user to fill in |
|---|---|
| IDENTITY.md | role in one sentence, who it serves, delivery goal, explicit boundaries, red lines |
| SOUL.md | communication tone, working priorities, decision principles (no fabrication / leave a trace / no overreach etc.) |
| AGENTS.md | standard SOP, **brake nodes where it must stop and ask the boss**, never-do list, exception escalation |
| TOOLS.md | for every tool / script / channel: when to use, how to use, what to use when it breaks |
| MEMORY.md | living work notes (customer DB pointers, key decisions, open items, pitfalls) |
| USER.md | the boss's reporting frequency / channel / format, approval granularity, communication preferences |
| HEARTBEAT.md | daily / weekly health-check items (pool, sending volume, bounces, reply follow-up, blockers) |

Interview carefully for IDENTITY's boundaries and red lines, AGENTS' human brake nodes, and USER's reporting and
approval preferences — these three are most often filled in vaguely; make the boss give concrete rules.

## Credentials (never in the profile)

SMTP/IMAP passwords and authorisation codes are keys, provided at runtime through environment variables; **never** write them into
company_profile.json, scripts or the conversation log:

```bash
export SMTP_HOST=...   SMTP_PORT=465   SMTP_USER=...   SMTP_PASS=...
# when bounce scanning is needed:
export IMAP_HOST=...   IMAP_USER=...   IMAP_PASS=...
```

## Interview examples (demonstrating the questions only; values are fictional placeholders)

**Example A: industrial parts**
> AI: I need to set up your profile before we start. Which industry are you in, and do you sell products, software, services or projects?
> User: Precision machined parts export; products.
> AI: Company name for the signature, sender name and e-mail?
> User: Northwind Precision, Sam Lee, sam@northwind.example.
> AI: Describe what you sell in one English sentence? Which terms do customers search? Your two hardest differences?
> User: CNC machined parts for automation OEMs; cnc machining / precision parts / machined components;
>       full inspection report, ISO 9001.
> AI: How does a customer start with low risk? What do you want to ask at the end of the e-mail?
> User: 3 free sample pieces to drawing; "Send a drawing and I'll quote within 48h?"

**Example B: SaaS**
> AI: Which industry and which offer type?
> User: HR onboarding software, SaaS.
> AI: Which decision makers and countries? How do customers start?
> User: HR directors and People Ops, UK and Germany first; a free 14-day pilot with one team.

After filling in, the AI writes the profile, runs check, **reads back every item** for the user to confirm, runs `attest` after explicit agreement,
and only after `READY` moves on to search / research / sending.
