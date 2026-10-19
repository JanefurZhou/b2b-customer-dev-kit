# Generic B2B hooks and messaging playbook (all industries)

**Version**: v3.1 | **Applies to**: physical goods, industrial products, software / SaaS, professional services, logistics, project-based sales — any B2B business
**Companions**: `industry_adaptation_guide.md` (pick an industry pack, build the offer layer first) · `email_templates.md` (finished skeletons)

---

## ⚠️ Before use: confirm "what you sell + how customers start"

This playbook provides only **hook structures and selection logic**. Every fact — what you sell, where you differ, how customers try you with low risk —
comes from the `config/company_profile.json` created at first install; the AI must not add or invent any.

```
=== fact confirmation ===
IF profile is READY:
    {offer}        ← product.one_liner_en           (one-line positioning)
    {usp}          ← product.differentiators[0..1]  (verifiable differences)
    {entry_offer}  ← offer.entry_offer              (sample / trial / demo / free diagnosis / pilot / mock-up)
    {facts}        ← offer.key_facts                (MOQ / go-live time / certification / delivery time / customer count)
    {cta}          ← offer.cta_question             (closing question)
    {proof}        ← offer.proof_points             (publishable cases, authorised or de-identified)
ELSE:
    → back to the Install Gate in SKILL.md; ask for whatever is missing, never substitute a "plausible" number
```

**Cross-industry placeholder map** (change the "words", never the "structure"):

| Placeholder | Physical goods | Industrial | SaaS / software | Professional services | Logistics | Project-based |
|---|---|---|---|---|---|---|
| `{entry_offer}` | free sample | sample to drawing | free trial / pilot | free diagnosis / sample deliverable | trial shipment | mock-up / technical documentation |
| `{min_commitment}` | MOQ | minimum batch | shortest subscription | starter package | minimum volume | minimum project value |
| `{delivery_time}` | sampling / bulk lead time | lead time | go-live time | delivery cycle | transit time | construction / supply period |
| `{proof}` | number of customers | certifications / PPAP | customer count / cases | result cases | lanes / warehouses | reference projects |

---

## 1. Decision drivers (solution_tag) — 11 industry-generic decision drivers

The core research question is: "**What does this customer care about most when deciding?**" The answer is the `solution_tag`.
It varies by customer, not by industry. `decision_maker_sender.py` picks the opening line directly from it.

| solution_tag | What they care about | Typical signals (any industry) |
|---|---|---|
| `compliance` | compliance, credentials, traceability | certification / regulation pages on the website; regulated industry; tenders require credentials |
| `sustainability` | ESG, environment, sustainability | sustainability report / commitment; ESG procurement policy |
| `quality_upgrade` | better quality / performance | using a low-tier solution; complaints centre on quality / stability |
| `cost` | total cost | distributor / high-volume buyer; public price comparison; budget-cut news |
| `speed` | speed, fast go-live | a clear date / go-live milestone; complaints about a slow current supplier |
| `low_commitment` | low-risk trial | small company / new brand / new team; first attempt at this kind of solution |
| `innovation` | new products, new direction | new product line, new market, post-funding expansion |
| `exclusive_custom` | custom, exclusive, on-premise | premium positioning; stresses bespoke / private label / on-premise |
| `one_stop` | fewer vendors to manage | scattered supply chain / tools; several suppliers patched together |
| `dedicated_service` | being taken seriously, having an owner | SME customers; complaints about slow big suppliers |
| `strategic_scale` | capacity, planning, long term | chain / group / large project; annual framework procurement |

> `need_tag` is the other dimension: **which of your product / service lines** the customer wants, with values you define in
> `positioning.need_tags` (e.g. `line_a` / `line_b` / `multi` / `unknown`).
> Both tags come only from research evidence.

---

## 2. The 7 generic hooks

Each hook gives: applicable signals → subject skeleton → body skeleton (≤60 words) → matching solution_tag.
Every `{...}` in a skeleton must be replaced with profile facts or customer facts; appearing verbatim in an outbound e-mail is an incident.

### 2.1 Gap-filling / expansion
- **Signals**: the customer has adjacent products / services but lacks yours; or is expanding categories / features / markets.
- **Subject**: `{offer} for [Company]'s {their_new_area}` / `Filling the {gap} at [Company]`
- **Body**:
```
Hi {name},

[Company] now covers {their_current_area} — {offer} is the piece that usually sits next to it.
{usp}. {facts}.

{cta}
```
- **solution_tag**: `one_stop` / `innovation` / `open`

### 2.2 Quality upgrade
- **Signals**: the customer uses a lower-tier solution; reviews / social media mention quality, stability, results.
- **Subject**: `A step up from {their_current_solution}` / `{usp_short} for [Company]`
- **Body**: acknowledge their status first, then **one verifiable comparison fact** (never disparage the current supplier).
```
Hi {name},

{their_strength} stands out at [Company]. One area we could lift: {usp} — measurable, not a claim.
{entry_offer} available so your team can compare side by side.

{cta}
```
- **solution_tag**: `quality_upgrade`

### 2.3 Cost / efficiency
- **Signals**: distributors, high-volume buyers, tightening budgets, public price comparison, looking for an alternative supplier.
- **Subject**: `{offer} — {fact_1}` / `A second option for {category} at [Company]`
- **Body**: state thresholds and terms directly, **no empty phrases like "competitive pricing"**.
```
Hi {name},

If [Company] wants a second option for {category}: {facts}.
{usp}.

{cta}
```
- **solution_tag**: `cost` / `low_commitment`

### 2.4 New initiative
- **Signals**: new product line / service, funding, new market, new management.
- **Subject**: `For [Company]'s {new_initiative}` / `{offer} for the {new_market} launch`
- **Body**: name their new move (proof of homework), offer an entry they can start right away.
```
Hi {name},

Saw [Company] is {new_initiative} — congratulations.
We {offer_short}; {usp}. Easy start: {entry_offer}.

{cta}
```
- **solution_tag**: `innovation` / `low_commitment`

### 2.5 Compliance & ESG
- **Signals**: regulated industry, tenders require credentials, certification / ESG pages on the website, market-entry regulations.
- **Subject**: `{market}-ready {offer} for [Company]` / `Documented {category} for [Company]`
- **Body**: list only certifications / credentials **you really hold**, written exactly, no abbreviation, no exaggeration.
```
Hi {name},

[Company]'s {compliance_focus} — noted. {cert_fact}. Documentation available before any commitment.
{facts}.

{cta}
```
- **solution_tag**: `compliance` / `sustainability`

### 2.6 Timing / deadline
- **Signals**: the customer has a clear date (peak season, go-live, project milestone, fiscal budget window, regulation effective date).
- **Subject**: `Ready before {their_deadline}` / `{offer} — {delivery_time}`
- **Body**: spell out the backward schedule (start now → delivery / go-live → which milestone), real cycles only.
```
Hi {name},

Planning for {their_deadline}? Starting now means {delivery_time} → ready by {date}.
{usp}.

{cta}
```
- **solution_tag**: `speed`

### 2.7 Bespoke & dedicated
- **Signals**: premium positioning, stresses exclusive / private label / on-premise; or SME customers who need attentive service.
- **Subject**: `Built around [Company]'s requirements` / `Dedicated {category} support for [Company]`
- **Body**: focus on capability and process; premium customers do not hear price and MOQ first.
```
Hi {name},

[Company]'s {positioning} calls for something built to spec, not off the shelf.
{custom_capability}. One named contact from first call to delivery.

{cta}
```
- **solution_tag**: `exclusive_custom` / `dedicated_service` / `strategic_scale`

---

## 3. Hook by customer type (cross-industry quick reference)

| Customer type (recognisable in any industry) | Preferred hook | Messaging direction |
|---|---|---|
| channel partners: distributors / agents / dealers / resellers | 2.3 cost / 2.1 gap-filling | margin room, entry threshold, regional support |
| brands / product companies: make their own products | 2.2 upgrade / 2.7 bespoke | verifiable difference, custom capability |
| integrators / implementers / engineering firms | 2.1 gap-filling / 2.6 timing | delivery dates, technical documentation, cooperation |
| end-company functions (IT / HR / procurement / operations) | 2.4 new initiative / 2.3 efficiency | business results, go-live time, pilot |
| SMEs / new companies | 2.3 low commitment / 2.7 dedicated | free start, a named owner |
| groups / chains / large projects | 2.7 scale / 2.5 compliance | capacity, compliance documents, annual planning |
| heavily regulated industries (medical / food / energy / finance) | 2.5 compliance | exact licences, documentation first |
| clear schedule (peak season / go-live / construction) | 2.6 timing | backward timeline |

---

## 4. Regional strategy (decides only tone, language and sending window)

> Regional traits are a starting point; **research evidence outranks regional stereotypes**. Send inside the customer's local window;
> use `python3 scripts/send_window.py table --me <your tz>` for the live conversion (daylight-saving time included).

| Region | Communication style | Common concerns | Localisation |
|---|---|---|---|
| 🇺🇸 USA | direct, efficiency-driven | speed, ROI, flexible start | English |
| 🇬🇧 UK | polite, understated | credentials, reliability, long-term relationship | English |
| 🇩🇪 Germany / DACH | formal, evidence-driven | certifications, precise delivery, data | German greeting and closing (automatic); Xing as a complement |
| 🇫🇷 France | formal, relationship-driven | quality, uniqueness | French greeting and closing (automatic) |
| 🇮🇹 Italy | relationship-driven, many family businesses | quality, the owner decides | Italian greeting and closing (automatic) |
| 🇪🇸 Spain / 🇵🇹 Portugal | relationship-driven | value for money, trust | local language preferred |
| 🇳🇱 Netherlands / Nordics | very direct | sustainability, efficiency | English is fine |
| 🇯🇵 Japan | formal, slow decisions | quality control, detail, long term | Japanese preferred; build trust first |
| 🇦🇪 Middle East | relationships and meetings | credentials, reliable delivery | English; WhatsApp common |
| 🇧🇷 Latin America | relationship-driven | price, local support | Portuguese / Spanish; WhatsApp common |
| 🇨🇳 Domestic China B2B | relationships and efficiency | cases, price, response speed | Chinese; WeChat / phone first |

**Multilingual query templates** (`{offer}` = your core term, translated into the local language first):
```
English   "{offer} distributor {country}" / "{offer} company {country}"
German    "{offer} Händler Deutschland" / "{offer} Anbieter"
French    "{offer} distributeur France" / "{offer} fournisseur"
Italian   "{offer} distributore Italia" / "{offer} fornitore"
Spanish   "{offer} distribuidor España" / "{offer} proveedor"
Japanese  "{offer} <local term for distributor>" / "{offer} <local term for case study>"
```

---

## 5. Banned words and replacements (cross-industry baseline)

**Banned in subjects**: Partnership · Collaboration · Free!!! · Discount · Cheap · Guaranteed · Best · #1

**Banned in bodies**: competitive pricing · world-class · leading · revolutionary · guaranteed results ·
any absolute claim you can't prove · I came across · I'd love to · could be a great fit · we specialize in

| Empty phrase | Replace with a verifiable fact |
|---|---|
| competitive pricing | a concrete threshold or term (`{min_commitment}`, payment terms) |
| high quality | one measurable metric (tolerance, yield, SLA, repeat rate) |
| fast delivery | a concrete cycle (`{delivery_time}`) |
| experienced team | concrete years or cases (`{proof}`) |
| leading provider | customer count, project count, certification name |
| partner | work with / support |

> Industry-specific banned words (medical efficacy claims, food health claims, financial return promises) are added in `soul_seven_kit/SOUL.md`
> and `rules.notes`.

---

## 6. Edge cases

- **Peers / competitors**: hitting `targeting.competitor_markers` blocks; a company with similar capability inside the target market may be positioned as a "capacity / delivery complement partner" per your strategy, with a human deciding whether to contact.
- **Hot leads**: the customer replied or asked for a quote → no automatic reply, escalate to a human; identity and credit checks go to the separate post-inquiry risk-control research flow.
- **Duplicate sends**: the same domain contacted several times in one day → skip and record; one owner with several companies → one e-mail.
- **Company status**: website down → check for closure first; closed → remove; paused → mark paused.
- **Missing facts**: numbers, certifications, cases not in the profile are never written; go back and ask the user.

---

## 7. Hook selection decision tree

```
Step 1  profile READY? no → back to the Install Gate
Step 2  research → need_tag (which line) + solution_tag (what matters most), one piece of evidence each
Step 3  pick the hook
        compliance / sustainability    → 2.5 compliance & ESG
        quality_upgrade                → 2.2 quality upgrade
        cost / low_commitment          → 2.3 cost / efficiency
        innovation                     → 2.4 new initiative
        speed                          → 2.6 timing / deadline
        exclusive_custom / dedicated_service / strategic_scale → 2.7 bespoke & dedicated
        one_stop / open                → 2.1 gap-filling / expansion
        unknown                        → 2.1 or 2.3 as a conservative probe, complete research during follow-up
Step 4  region (§4) → language, greeting, sending window
Step 5  replace placeholders: {offer}{usp}{entry_offer}{facts}{cta}{proof} all from the profile
Step 6  self-check (banned words / ≤60 words / every number traceable) → whole batch to the user for approval → send
```
