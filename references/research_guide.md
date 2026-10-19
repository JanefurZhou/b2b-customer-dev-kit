# Customer background research methodology (universal edition)

> Company / brand name never decides the need; research does. This document is the detailed research guide.
> Every "target category / process / selling point" mentioned here comes from the `config/company_profile.json` you fill in at first install
> (`product.primary_keywords` / `product.one_liner_en` / `product.differentiators` /
> `offer.*` (entry offer / key facts) and `targeting.*`, see the Install Gate in SKILL.md and
> `onboarding_questions.md`); never treat any specific industry as the default.
> "Category" here means whatever you sell: product lines, software modules, service types, project capabilities.

---

## 1. Why research is mandatory

**Three transferable lessons:**
1. Judged by the company name alone it looked like a competitor, but it was a prospect inside the target region — never let stereotypes replace judgement.
2. The website looked like a shop in the same category, but the main business was an **adjacent category you do not serve** — a wasted e-mail.
3. A shop selling only "lower-tier alternatives" is exactly the one with the **biggest upgrade opportunity**; it was almost skipped "because they already sell this kind of thing".

**Conclusion:** company / category name ≠ real need. Pass the **scope gate** first (is it inside your profile's target scope), then research (what they need, which hook works). Sending without research = shooting blind.

---

## 2. The three research questions

For every candidate, answer:

### Q1: What is their business? (scope gate first)
- Is the main business your **target category** as defined in `targeting` (judged by `primary_keywords` and related terms)?
- How does their current product / solution relate to your differentiators — decides "upgrade / replace / complement" hooks
- Target audience (B2B / B2C / institutions / projects)
- Price positioning (premium / mid / mass)

> ⚠️ Main business is an **irrelevant adjacent category** explicitly listed at install → non-target, blocked, never enters later steps.
> The exclusion list depends on your industry (maintained in the search script configuration); the skill ships no industry-specific exclude terms as defaults.

### Q2: What are their channel and stance?
- Customer type: channel partner / brand / integrator / end company / institution / project owner (per your customer spectrum)
- Industry-relevant certifications / compliance (names per the real requirements of your industry)
- Sustainability / compliance positioning (real standard terms of your industry)
- A wholesale / trade / vendor application / partner program / RFP / procurement page (present = explicit B2B buying signal)
- Recent strategy (new product / service, expansion, new market, funding, new project, new management, relevant hiring)

### Q3: What might they need?
- Derive `need_tag` (which of your lines) and `solution_tag` (what matters most → which hook) from Q1+Q2
- Uses only lower-tier alternatives → pitch your **differentiated upgrade** selling point from the profile
- Small company / new team / first attempt → pitch `low_commitment` only when you really have a low-commitment entry (sample / trial / pilot / diagnosis)
- Clear deadline (peak season / go-live / schedule / budget window) → pitch `speed` only when your real delivery time matches
- Wants exclusive / private label / custom / on-premise → pitch `exclusive_custom` only when you really have the capability
- Weak signals → `unknown` / `review`, conservative generic pitch, confirm during follow-up

---

## 3. Information source priority

### First: the website (5 minutes)
| Page | What to look for |
|------|--------|
| Home | positioning, main business, audience (is it inside the target scope?) |
| Products / Services / Solutions | does it touch your target category; relation of their current solution to your differentiators; price band or size |
| About / Our Story / Team | company background, decision-maker background, team size |
| Wholesale / Trade / Partners / Procurement | wholesale, distribution, vendor onboarding, partner program, tenders |
| Sustainability / Compliance | certifications and policies relevant to your industry (names must really exist) |
| Solutions / Industries / Case studies | industries served, projects done, customisation accepted |
| Press / News / Blog / Careers | new products / services, expansion, funding, new projects, open roles (= budget and pains) |

**Search tip:** search the website for your `primary_keywords` + the related terms you use to distinguish solutions + `supplier / vendor / partner`.

### Second: search engine (3 minutes)
```
- "[company] wholesale / vendor application / partner program / RFP / tender"
- "[company] <your-core-term>"
- "[company] launch / expansion / new project / funding <year>"
- "[company] site:linkedin.com <buyer_titles>"
```

### Third: LinkedIn (3 minutes)
- Company page: headcount, industry tags, recent activity
- Decision makers: titles per `targeting.buyer_titles` (procurement / CTO / HR director / operations / owner; title bank in `linkedin_strategy.md`)
- Used to find named personal e-mails and avoid the high bounce rate of info@ mailboxes

### Fourth: social media (2 minutes)
- LinkedIn posts / Instagram / YouTube / X: recent activity, what they promote, what they complain about
- Judge the level of their current solution, company stage and overall positioning from the content

---

## 4. Research focus (fill this table with your own industry)

| Focus | What to look at (example dimensions, replace with your industry) |
|---------|---------|
| category match | your target category keywords; adjacent irrelevant categories listed at install are excluded outright |
| current solution | relation of the customer's current solution to your `differentiators` (replace / upgrade / coexist) |
| positioning / size | premium / mass, size, stage (which line to pitch, which hook) |
| customer type | channel partner / brand / integrator / end company / institution / project owner (decides the tier) |
| certifications | certifications really used in your industry and really required in the customer's market |
| time window | peak season, fiscal budget, tender cycle, go-live / construction dates (`speed` applies only when your real cycle fits) |
| market | compliance and localisation of the target region; outreach language must be localised |

**Competitor test (general principle):**
- Exclude only when **both peer semantics (`competitor_markers`, e.g. manufacturer / agency / software vendor) and the competitor region defined in your profile** are hit;
- a region hit alone or a semantics hit alone never excludes.
- A manufacturer in the target market with its own capacity can be positioned as a **capacity complement / flexible subcontracting partner**; whether to contact them is your strategy decision —
  never label competitors by company name alone.

---

## 5. need_tag decision tree (structure generic, tag names your own)

```
start research (scope gate passed)
  │
  ├─ which of your lines? (values = positioning.need_tags, defined from your product / service base)
  │   ├─ <offer-line-A>   → need_tag <line_a>
  │   ├─ <offer-line-B>   → need_tag <line_b>
  │   └─ several lines / overall solution → need_tag multi
  │
  ├─ relation of the current solution to your differentiators?
  │   ├─ lower-tier alternative only  → add the "upgrade opportunity" tag
  │   └─ already has similar capability → pitch exclusive / capacity / category expansion (only when you really have it)
  │
  ├─ channel / volume traits?
  │   ├─ small company / new team     → low_commitment: offer.entry_offer (real profile value)
  │   ├─ clear deadline               → speed: offer.delivery_time (real profile value)
  │   └─ channel partner / group / large project → strategic_scale: capacity and annual planning (real profile value)
  │
  └─ category or solution unclear?
      └─ need_tag = unknown / review (conservative, confirm during follow-up)
```

### 5.1 need_tag iron rules (must read)

1. **need_tag comes only from research evidence**: product / service pages, procurement / partner pages, certification pages, news, hiring. Never from the company name.
2. **Every tag traces to one piece of evidence**, written into notes; without evidence only `unknown` is allowed.
3. **The scope gate precedes need_tag**: main business outside `targeting` → excluded, no tag needed.
4. **Regular self-check**: the search script's category check sub-command (`audit-category`, when present) outputs a suspected non-target list (flags only); handle after manual review.

### 5.2 Diagnose solution_tag at the same time (research decides the hook) ⭐

> Research sets not only the product (need_tag) but also diagnoses the pain point and matches a `solution_tag` from the real capabilities in your profile.
> Capability panorama in `solution_capabilities.md`; values are the 11 cross-industry decision drivers (`industry_playbooks.md` §1),
> **but only those whose capability your profile really has**.

Ask one more question during research: "What hurts this account most? Which of my **real** capabilities solves it?"

| Research signal (generic) | Matching capability (from the profile) | solution_tag |
|---------|---------|-------------|
| regulated industry / tender requires credentials / certification page on the website | certifications and documents you really hold | `compliance` |
| ESG / sustainability commitment | verifiable sustainability facts | `sustainability` |
| using a lower-tier solution, mediocre results / quality | measurable differences in `differentiators` | `quality_upgrade` |
| distributor / high volume / public price comparison | entry threshold and terms (`offer.key_facts`) | `cost` |
| small company / new team / first attempt | `offer.entry_offer` (sample / trial / diagnosis / pilot) | `low_commitment` |
| deadline / complaints about a slow current supplier | `offer.delivery_time` (real value) | `speed` |
| new product line / new market / funding | capability matching the new direction | `innovation` |
| wants exclusive / private label / custom / on-premise | custom capability (if any) | `exclusive_custom` |
| scattered suppliers / tools | your multi-line combination (if any) | `one_stop` |
| group / chain / large project | capacity + annual planning (if any) | `strategic_scale` |
| ignored by big suppliers, slow responses | your real service model | `dedicated_service` |

Notation (notes field, next to need_tag):
`solution=<tag1>+<tag2>(signal:<specific fact observed in research>)`

> 📖 Capability panorama: `solution_capabilities.md`.

---

## 5.5 Evidence tiers S1 / S2 / S3 (every conclusion traceable, nothing invented) ⭐

Every need_tag / solution_tag / pain-point judgement states its evidence tier and source URL. **Insufficient tier → no conclusion.**

| Tier | Definition | Examples | Allowed actions |
|---|---|---|---|
| **S1 first-hand** | explicitly stated on the customer's own official channels | website product / procurement / policy pages; company LinkedIn page; tender or procurement posts from official accounts; customs records showing continuous imports of similar goods | direct basis for need_tag / solution_tag |
| **S2 credible second-hand** | public third-party or individual employee information, cross-checkable | trade media, exhibitor lists, employee posts, review sites, job ads | usable; source must be noted; one extra S1 is better |
| **S3 weak signal** | guesses, fragments, unverifiable | one comment, a hashtag hit, "looks like it by the name", analogy with a similar company | **never** a basis for tags → `need_review`, user decides |

Rules:
1. **≥1 S1 or 2 independent S2** before setting need_tag / solution_tag; otherwise `need_tag=unknown` or `need_review`.
2. Brand name, domain and industry impression always count as S3 — "brand name never decides the need; research does".
3. Format (notes of add_sent or the research record): `evidence=S1:https://...;S2:https://...`.
4. Customer facts quoted in e-mails may come from S1/S2 only; S3 content never enters an e-mail.
5. Pain points of success cases are tiered the same way: the AI proposes evidence-backed candidates only; `add_success` after user confirmation.

## 6. Suggested time budget

| Stage | Time | Output |
|------|------|------|
| data de-dup | 1 min | exclude duplicates / blacklist / already sent |
| scope gate | 1 min | inside the target scope? non-target blocked immediately |
| website scan | 3–4 min | main business + current solution + customer type + certifications + news |
| search / LinkedIn | 2–3 min | buying signals, decision makers, recent moves |
| tag decision | 1 min | need_tag + solution_tag |
| **total** | **7–10 min per account** | — |

In batch development, a 2-minute scope gate per account can do the coarse split first, then dig into the ones that pass. **Before sending, every account's tag must rest on research.**

---

## 7. Common mistakes

| ❌ Wrong | ✅ Right |
|------------|-----------|
| skipping same-category companies in the target market as competitors by region / name | double condition "peer semantics + competitor region"; those with own capacity can be subcontracting partners |
| sending because the website looks like a target customer | confirm the main business is inside your target scope first |
| skipping because they already use a similar solution | check the level; users of lower-tier solutions are the upgrade targets |
| using info@ for a large company | find the named e-mail of the `buyer_titles` decision maker on LinkedIn |
| judging the business by the company name | check the website business lines before every send |
| one research pass is valid forever | companies pivot / expand; re-check periodically |
| inventing thresholds / lead times / certifications / cases to fill out the pitch | only verifiable facts from the profile |

---

## 8. Research record template

```
Company: [name]
Website: [URL]
Country: [country]
Tier: [per your customer spectrum, e.g. L1_core / L2_...]
Main business: [one sentence]
Current solution: [relation to your differentiators: replace / upgrade / coexist]
Buying signal: [vendor / partner / RFP / hiring / expansion / certification / none]
need_tag: [<line_a>/<line_b>/multi/unknown]
solution_tag: [compliance/cost/speed/low_commitment/... (only capabilities you really have)]
Sources: [website / search / LinkedIn / ...]
Notes: [special findings: new product, expansion, funding, tender, new management …]
```

In practice the tags go into the customer DB / `sent_history.csv` fields or notes; everything else into the task log.
