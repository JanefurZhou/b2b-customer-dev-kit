# Solution capability arsenal + research diagnosis map (universal edition)

> **Core logic (causal order, never reversed):**
> not "we have a few capabilities, let's try each one on the customer", but
> **research → diagnose the customer's pain point → match a solution capability → tailor the hook**.
> The capability panorama is the "arsenal"; the research result is "which trigger to pull".
>
> Same idea as need_tag:
> - `need_tag` (which of your product / service lines they need) is decided by research evidence → decides **what** to pitch
> - `solution_tag` (which solution hook they respond to) is decided by research evidence → decides **which value proposition** moves them
>
> **Both tags are decided only by research evidence, never by the brand name, never by gut feeling.**
>
> ⚠️ This is a **universal template**: the table below is a skeleton of "capability categories"; **your own real capabilities and wording
> all come from the `config/company_profile.json` filled in at first install** (`product.differentiators` /
> `product.one_liner_en` / `offer.entry_offer` / `offer.key_facts` etc.,
> see the Install Gate in SKILL.md and `onboarding_questions.md`) and can be maintained in
> `references/product_knowledge.md`. A capability without real evidence must not enter the arsenal.

---

## 1. Solution capabilities (arsenal · cross-industry skeleton)

> How to use: keep only the rows **you really have**, and replace the "hook direction" with your own real wording from
> `product.differentiators` / `offer.*`. `<...>` placeholders must never appear in an outbound e-mail.
> The "what it looks like by industry" column only helps you find your row; it is not your fact.

| # | Capability category | What it looks like by industry | Who it lets you develop | Hook direction (English, replace with real facts) |
|---|---|---|---|---|
| ① | **Core difference** `differentiators` | process / material · tolerance / yield · features / performance · methodology / results | customers on a lower-tier solution with an appetite to upgrade | "<your-verifiable-advantage>" |
| ② | **Entry threshold** `offer.min_commitment` | MOQ · minimum batch · shortest subscription · starter package | small companies, new teams, first-timers | "start from <your-min-commitment>" |
| ③ | **Low-risk entry** `offer.entry_offer` | sample · prototype · free trial · pilot · free diagnosis · mock-up | cautious customers who want to verify first | "<your-entry-offer> before any commitment" |
| ④ | **Delivery speed** `offer.delivery_time` | sampling + bulk lead time · go-live time · project duration · transit time | customers with a hard deadline | "<your-delivery-time>, ready for your <deadline>" |
| ⑤ | **Customisation** | private label / ODM · custom development · on-premise · dedicated solution | customers wanting exclusivity / differentiation / customisation | "<custom capability — state fact only>" |
| ⑥ | **One-stop scope** | multi-category / multi-form · multi-module · end-to-end service | customers with scattered suppliers / tools | "<scope A> and <scope B> from one team" |
| ⑦ | **Service model** | dedicated contact · SLA · on-site · local support | SMEs afraid of being ignored by big suppliers | "<your actual service commitment>" |
| ⑧ | **Compliance and credentials** | product certifications · quality systems · data-security certifications · professional licences | regulated industries, tenders, ESG buyers | "<exact certification name>" |
| ⑨ | **Capacity and planning** | output · annual scheduling · concurrent projects · team size | groups, chains, large projects, framework procurement | "<capacity fact>, planned with you" |
| ⑩ | **Supporting services** | logistics and customs · integration / migration · training · financing / payment terms | customers new to cross-border or implementation | "<the actual support you provide>" |

**Fill-in and usage principles:**
- Capability facts **come only from the profile and the product / service knowledge base**; the AI must not invent thresholds, lead times, certifications or customer cases.
- The strongest lever differs per business: review your own won deals (`success_cases.csv`),
  count which hook types actually produced replies / orders, then rank the arsenal.

---

## 2. Research pain point → solution_tag diagnosis map (11 generic values)

> During research, besides setting need_tag (which line), diagnose **what they care about most** and match a `solution_tag` from the capabilities you really have.
> The values are fixed to 11 cross-industry ones (`decision_maker_sender.py` recognises them directly); just delete the rows you cannot serve.

| Pain point / signal found in research (any industry) | Diagnosed gap | Matching capability | solution_tag |
|---|---|---|---|
| regulated industry, tender requires credentials, website has a certifications page | compliance threshold | ⑧ | `compliance` |
| ESG / sustainability commitment or procurement policy | sustainability requirement | ⑧ + ① | `sustainability` |
| using a clearly lower-tier solution, signs of upgrading | solution upgrade gap | ① + ⑤ | `quality_upgrade` |
| distributor / high volume / public price comparison | cost pressure | ② + ⑨ | `cost` |
| small, first attempt, afraid of the investment | entry threshold too high | ② + ③ | `low_commitment` |
| hard deadline, complaints about a slow current supplier | insufficient speed | ④ | `speed` |
| new product line / new market / funding / new project | missing capability for a new direction | ① + ⑥ | `innovation` |
| wants exclusivity / private label / custom / on-premise | commoditisation | ⑤ | `exclusive_custom` |
| scattered suppliers / tools | consolidation need | ⑥ | `one_stop` |
| group / chain / large project owner | stability + planning | ⑨ + ⑩ | `strategic_scale` |
| ignored by big suppliers, slow responses | lacks attentive service | ⑦ | `dedicated_service` |

**One account may carry several solution_tags** (decided by research signals, stackable; the first one is the main hook when sending).
Legacy tags (`low_moq` / `upgrade_opportunity` / `seasonal` / `exclusive_design` / `category_expand` /
`strategic_partner` / `eco_only` / `traditional` etc.) are mapped to the new values by the scripts automatically; historical data needs no change.

---

## 3. How solution_tag is stored

The sending JSON carries a `solution_tag` field directly (the scripts read it first to pick the hook); in the customer DB it goes into `notes`, next to the need_tag evidence, traceable:

```
notes: need_tag=<line_a>(evidence: website <specific page/news>) | solution=<tag1>+<tag2>(signal: <specific fact observed in research>)
```


---

## 4. The loop: how solution capabilities drive the whole process backwards

```
Search (widen by the profile's target customer types / keywords to find candidates)
   │  each customer type maps to one real capability + the pain-point customers to find
   ▼
Scope gate (anything outside the profile's targeting scope is blocked)
   ▼
Research (diagnose the pain point from evidence, not the brand name)
   │  produces two tags: need_tag (which line) + solution_tag (which hook)
   ▼
E-mail (hook chosen by solution_tag, every fact quoted from company_profile)
   │  from "what we sell" → "which specific problem of yours we solve"
   ▼
Send → follow up → win → review (rank the arsenal from real wins)
```

- Research diagnosis steps: `research_guide.md`.
- Hook / e-mail wording: `email_templates.md` (its placeholders are replaced with your real facts after the profile is filled).
