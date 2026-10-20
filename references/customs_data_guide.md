# Customs / import-export data guide (no-registration path first)

> Applies to: `business.offer_type = physical_product` (and logistics / freight-forwarding services, to find customers with steady volumes).
> Principle: start with **no-registration, no-payment** public paths; platforms that require registration or payment are listed as "optional · the user decides"; this skill never registers accounts on the user's behalf.
> Customs data only proves "who imports what" — it is **S1/S2-grade need evidence**, not a contact. After getting an importer's name you still go: website → named decision-maker mailbox → `filter --against` DB lookup → research → positioning.
> Free tiers change; the platform's current page wins. What follows reflects public information as of October 2026.

---

## 1. Four steps

### Step 1: find the HS code (free, no registration)
- Use the target market's official tariff lookup to find your product's HS code: US HTS (hts.usitc.gov), EU TARIC (European Commission site), UK Trade Tariff (gov.uk).
- The first 6 digits are global; note the 2–3 codes closest to your product in your own list (notes or a private list outside `search.cert_terms`).

### Step 2: country level — pick the market first (free, no registration)
- **Eurostat Comext** (EU foreign-trade database, free data): by HS code, see each EU country's import volume and origin countries to tell who is buying and growing.
- **UN Comtrade** (UN trade data): country-level imports/exports worldwide, viewable directly on the website.
- Write the conclusion into `targeting.target_regions`: keep only countries with **large and growing** imports; this step decides the region axis of every later search.

### Step 3: company level — find real importers
| Source | Coverage | Registration | Usage |
|---|---|---|---|
| ImportYeti | US ocean import bills of lading (from about 2015) | Basic search is free and account-free; some reports say that after many page views from one IP a free login is requested — stop there and switch to the search-engine method below | Search a peer / competitor factory name → see its US customers (= your potential buyers); or search a brand name → see which factories it buys from |
| Search engine site: method | Same (only indexed public pages) | None | `site:importyeti.com "<your category>"`; `site:importyeti.com "<reference / competitor brand>"` |
| Panjiva / ImportGenius / Volza etc. | Multi-country bills of lading | Registration required, mostly paid | Optional, the user decides; this skill never registers on the user's behalf |

> `search_customers.py channels --ch customs` generates these queries (including `site:importyeti.com`) from your category terms and regions.

### Step 4: from importer to decision maker (back to the main flow)
1. Importer company name → search for the website (bills of lading often show the legal name, not the brand).
2. Website → procurement / supply-chain lead → `search_customers.py social --platforms linkedin --tier execution` for a named decision maker.
3. `email_guesser.py` + `dns_validator.py` → named mailbox.
4. `filter --against` DB de-dup → research: "keeps importing the same category" in the bills = **S1 need evidence** (`evidence=S1:importyeti company page`), then set need_tag / solution_tag.

## 2. How to judge a good customer (4 fields on the bill of lading)

| Field | Good signal | Bad signal |
|---|---|---|
| Latest import | within the last 6 months | none for over a year (may have changed channel or closed) |
| Frequency | monthly / quarterly | one shipment only (possibly a sample or one-off project) |
| Number of suppliers | 2–5 (room to switch) | only 1 for many years (hard to enter; long-term follow-up) |
| Goods description | matches your HS code / category | only a neighbouring category (research first, then decide) |

## 2.5 Quantifying and timing (v3.2)

Export the bills you found to CSV (English or Chinese headers: date, origin, supplier, hs, teu) and run:

```bash
python3 scripts/customs_summary.py <imports.csv> --md
```

You get shipment count, last shipment, monthly TEU, scale tier (small-batch < 0.5 / mid-volume 0.5–3 / bulk > 3 TEU per month), origin and supplier shares, median purchase interval, next purchase window (inferred), plus import-stoppage, single-supplier and small-sample signals. How to use them: `references/research_guide.md` 5.6.

## 3. How to use it in an e-mail (without exposing data-source details)

- You may write: "We work with several importers of <category> in <country>" (only when true); "Saw you're active in <category>".
- Do not write: specific bill numbers, volumes, or which database you saw it in — recipients resent it.
- Pick the hook by solution_tag: several suppliers → `cost` / `speed`; one long-term supplier → `low_commitment` (small trial order).

## 4. Closing the loop

- HS codes and market conclusions used this round → `soul_seven_kit/MEMORY.md` "Conclusions this week".
- Which importers replied / closed → `csv_ops.py add_success ... --won_channel email`; `review_success` counts the customs channel's conversion by source_channel and decides whether to invest in it next round.
