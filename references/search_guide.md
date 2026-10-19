# Customer search script guide (search_customers.py · universal edition)

> This file explains the search logic of `scripts/search_customers.py`. Use it with
> `SOP_search_workflow.md` (methodology) and `self_replenishing_engine.md` (the core of a pool that never runs dry).
> **Product boundaries, category vocabulary and exclude terms all come from the `config/company_profile.json` you fill in at first install**
> (`product.primary_keywords` / `product.one_liner_en` / `targeting.*`);
> the skill ships no industry-specific vocabulary as defaults. See the Install Gate in SKILL.md and `onboarding_questions.md`.

## Product boundaries (read before searching)

Settle three things at install:

1. **What you sell**: expressed in `product.primary_keywords` (core product terms + common related terms / synonyms, English).
2. **Who your target customer is**: expressed in `targeting` (customer type, region, decision roles).
3. **Who is not your customer**: list "adjacent but irrelevant categories / roles" as exclude terms at install; competitor detection uses
   the double condition "peer semantics + competitor region", not a blanket rule by company name or region.

When these are missing the script must refuse to run (Install Gate) instead of searching blindly with placeholders.

## ♻️ Self-replenishing engine (a pool that never runs dry · the core leap)

Upgrade "one-off wide search" into "a long-running customer acquisition engine" (four-axis rotation: Height / Breadth / Depth / Reach; never burn everything at once):

1. **Pool floor**: when sendable cold-outreach candidates in the customer DB (own customers imported by `data_import.py` + SaaS exports + search results) < hard red line **100** or sendable days < lead time **30 days** → automatic replenish + warning (all three numbers are adjustable defaults).
2. **Four-axis rotation**: Depth d1 companies → d2 decision makers → d3 deep-mining the existing pool (fastest) → Reach regions near to far → Height customer tier high to low → Breadth core/wide/max (slowest); state in `search_state.json`, nothing is hit twice. Details: `references/self_replenishing_engine.md`.
3. **Built-in scheduler**: `schedule` runs the loop daily as a resident process and produces queries independently of any search engine.

```bash
# fully automatic: start the resident scheduler (09:00 daily: check pool → replenish → rotate)
python3 scripts/search_customers.py schedule --at 09:00 --floor 100 --ahead-days 30
# manual replenish: pool level + today's queries
python3 scripts/search_customers.py replenish --emit queries_today.txt
# rotation progress
python3 scripts/search_customers.py status
```

> Full methodology, long-run SOP and parameter details → `references/self_replenishing_engine.md`.

## Why graded entry (bottlenecks of the old script)

| Bottleneck | Old approach | Consequence |
|------|--------|------|
| result cap too low | only the first 80 results | most results never processed |
| mixed category scope | adjacent categories outside the profile slipped in | non-target accounts polluted the pool |
| e-mail bar too high | only non-generic mailboxes allowed in | many good accounts with only info@ were thrown away |

## Core mechanisms

1. **Full domain de-dup, then processing**: `filter_and_grade()` de-dups by **domain** (several pages of one site count once), with no cap.
2. **Scope gate**: title / body hitting the irrelevant category terms configured at install → blocked automatically (configurable non-target keyword list).
3. **Narrow competitor test**: excluded only when **both the competitor region (defined in the profile) and peer semantics (`competitor_markers`, e.g. manufacturer / agency / software vendor)** are hit; companies in the target market are customers by default.
4. **Graded entry A/B**:
   - **Grade A**: named mailbox (e.g. first.last@) → send directly
   - **Grade B**: only a generic mailbox such as info@/contact@/sales@ → stored with the note "find the decision maker on LinkedIn / complete a named mailbox with email_guesser"
   - **none**: no e-mail → stored with the note "complete the e-mail from the website / LinkedIn"

## Customer spectrum (Height: from high value to long tail · rename the tiers for your industry)

The customer spectrum = `targeting.customer_levels`, each tier `{name, desc, keyword_suffixes}`. An industry pack (`onboarding.py apply-pack <id>`) can pre-fill a starting set,
which you then rewrite as your real customer types. The same skeleton in different industries:

| Industry | L1 (closest, easiest to win) | L2 | L3 | L4 (further, needs nurturing) |
|---|---|---|---|---|
| Physical goods export | importers / distributors `importer, distributor` | brands `brand, private label` | retail `retailer, store chain` | e-commerce / project buyers |
| Industrial | OEM `OEM, machine builder` | industrial distribution `industrial distributor` | integrators / engineering `system integrator` | end plants `plant` |
| SaaS / software | ICP companies `<industry> company` | competitor users `"<competitor> customer"` | growth signals `hiring, raised funding` | implementation partners `implementation partner` |
| Professional services | SMEs `SME` | expanding `expanding to, new office` | mid / large function heads `head of` | referral partners `partner agency` |
| Logistics | importers / traders `importer` | e-commerce sellers `Amazon seller` | exporting manufacturers `exporter` | project logistics `project cargo` |
| Project-based | main contractors `general contractor` | designers `architect` | owners `developer` | distribution / installers `installer` |

> "What we can offer" lives in `product_knowledge.md` §4: one real capability + preferred hook per tier, not hard-coded here.

> Run only some tiers with `--levels`: `python3 search_customers.py queries --levels L1_core,L2_growth   # tier names = the name values in your customer_levels`

## 5 orthogonal axes (enabled by --breadth wide/max)

These axes are **not** fully combined with "customer × category × region" (it would explode); they are sampled and attached to representative categories:

| Axis | What to search | Customers it finds |
|----|--------|-----------|
| **① scene / use case** | `<use-scene-keyword>`: scenarios where your product / service is used | customers who buy by scenario |
| **② intent / buying intent** | generic: looking for vendor / RFP / alternative to …; industry packs add: low MOQ / free trial / tender … | active customers currently looking for a supplier |
| **③ channel / platform** | site:linkedin / g2 / clutch / industry B2B platforms … (per pack or your own) | customers hidden on specific platforms |
| **④ niche positioning** | `<niche-keyword>`: sub-segment / positioning terms of your industry | vertically positioned customers |
| **⑤ cert / compliance** | `<cert-keyword>`: certification / compliance terms really used in your industry | compliance-sensitive customers |

## Category vocabulary (generated from the profile, never hard-coded)

The category vocabulary is not fixed; it expands from `product.primary_keywords`, each core term with at least:

- **core term**: `<your-core-term>`
- **synonyms / colloquial names**: what buyers actually type
- **related terms**: adjacent categories still inside your target scope
- **scene terms**: `<use-scene-keyword>`
- **time-window terms** (if applicable): `<peak-season / budget-cycle / tender-season keyword>`

> Expansion principle: better too many synonyms than a missing one; adjacent business you do not do goes into **exclude terms**, not search terms.

## Channel recipes (channels sub-command)

`python3 search_customers.py channels` lists the 15 discovery channels; ▶ marks the channels generated by default for your industry pack / `business.offer_type`.
directory / tender / review / events find **directory pages, tender pages, review pages** — they are lead sources:
extract the company names from the page first, then look up the website; `filter` never enters those pages themselves as customers:

| Channel | Suited to | Channel | Suited to |
|---|---|---|---|
| `social` social / professional networks | all industries | `tender` public tenders | all industries (projects / institutions especially) |
| `hiring` hiring signals | all industries (software / services especially) | `directory` industry directories / associations | all industries |
| `events` conference attendee lists | all industries | `media` news / funding / expansion | all industries |
| `competitor` competitor reverse-lookup | all industries | `maps` maps / local directories | physical / services / projects |
| `customs` customs data | physical goods / logistics | `rfq` buyer side of sourcing platforms | physical / projects |
| `exhibition` trade-show exhibitor lists | physical / projects | `review` review sites | software / services |
| `partners` ecosystem partners | software / services / projects | `ecommerce` independent online stores | physical goods |
| `gift` gift channel | physical goods (needs explicit `--ch gift`, not a default) |  |  |

Pick channels: `channels --ch tender hiring --regions UK,Germany --out ch.txt`;
fix the default channels: write `search.channels` in the profile.

## Usage

### A. Generate queries (run each with a search engine / browser tool)
```bash
# by region in batches (recommended; avoids too many at once)
python3 search_customers.py queries --regions USA --breadth max --out q_usa.txt
python3 search_customers.py queries --regions UK,Germany --breadth wide --out q_eu.txt

# focus by tier + region
python3 search_customers.py queries --regions USA --levels L1_core --breadth max --out q.txt
```
Exclude marketplaces when searching (alibaba / made-in-china / globalsources / etsy and social platforms; the built-in PLATFORM_BLOCKLIST can be extended).

### B. Channel discovery queries (social / maps / customs / RFQ / trade media / vertical channels)
```bash
python3 search_customers.py channels --ch <channel-key> --regions USA --out ch.txt
python3 search_customers.py channels            # list every channel with its description
```

### C. Filter + incremental DB de-dup + scope gate + grading
```bash
# strongly recommended: --against the DB to avoid re-developing existing customers
python3 search_customers.py filter results.json --against <main-customer-db.csv> --out candidates.csv
```
Structure of each `results.json` item (fields optional):
```json
[{"url":"...","title":"...","snippet":"...","emails":["..."],
  "is_competitor":false,"customer_type_hint":"","region_hint":""}]
```
Output `candidates.csv` fields: domain, url, brand, **email_grade(A/B/none)**, best_email, all_emails, region_hint, customer_type_hint, **next_action**, note

### D. Non-target review
```bash
python3 search_customers.py audit-category candidates.csv
```
Flags records that look outside the profile's scope, **flagging only, never editing**; handle after manual research.

## Hand-over to the main flow (the loop)

Search candidates → **scope gate** (outside targeting → blocked) → **research** (research_guide.md) → set **need_tag** → **de-dup** (`csv_ops.py check` / cross_brand_check) → into the reserve pool → write and send.

- **Grade A** candidates: straight to writing after research.
- **Grade B** candidates: complete a named mailbox with `email_guesser.py` + LinkedIn first, then send (avoid the high bounce rate of generic mailboxes).

## Exclusion quick reference (platform part generic; category part per your industry)

| Category | Excluded on hit |
|------|-----------|
| platforms / marketplaces | alibaba/aliexpress/made-in-china/1688/globalsources/dhgate/amazon/ebay/temu/shein/etsy/faire/indiamart … (extend as needed) |
| directories / blogs / dead pages | /blog/ /news/ /category/ /tag/, blog./news./wiki. sub-domains, pinterest/youtube/reddit/wikipedia/yellowpages/yelp |
| non-target categories | **defined at install**: adjacent but irrelevant English category terms go into the non-target keyword list (never hard-code any industry's list in this file) |
| peers / competitors | both the competitor region defined in the profile (matching TLD / country terms) + `competitor_markers` (manufacturer / agency / software vendor) |
| duplicate domains | only the first record per domain is kept |
