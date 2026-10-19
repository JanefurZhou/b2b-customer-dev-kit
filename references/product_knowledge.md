# Product / service knowledge base template (you fill it in; any industry)

> This is a **blank template**. The skill ships no product facts of any company or industry.
> Replace every `<...>` with your own real information; delete sections that do not apply.
> "Product" here means whatever you sell: physical goods, components, software, professional services, logistics solutions, project capabilities.
> When the AI drafts e-mails or distils hooks it quotes only this file and `config/company_profile.json`; it must not invent anything.

---

## 1. What you sell (product / service lines)

> One line per offer line. The `need_tag` column is the "which of your lines they need" tag given to customers during research;
> copy it into `positioning.need_tags`.

| need_tag | Name | Offer type | One-liner (English, ready for an e-mail) | Typical customer |
|---|---|---|---|---|
| `line_a` | <offer-line-1> | <physical / software / service / project> | <one-liner> | <customer-type> |
| `line_b` | <offer-line-2> | <...> | <one-liner> | <customer-type> |

---

## 2. Verifiable core selling points (differentiators)

> Every selling point must be verifiable by the customer (certificate, data, case study, sample, trial, demo).
> Copy the first two into `product.differentiators`.

### 2.1 Core difference
- <the real, measurable difference compared with common alternatives>

### 2.2 Quality and compliance
- <exact certification names / test reports / security and data compliance / industry licences — only what you really hold>

### 2.3 Delivery capability
- <entry threshold min_commitment: MOQ / minimum contract / shortest subscription>
- <delivery_time: sampling + bulk / go-live time / project duration / transit time>
- <capacity or service capacity: monthly output / concurrent customers / team size>

### 2.4 Customisation and R&D
- <customisation, private label, on-premise deployment, dedicated solutions supported? process and lead time>

### 2.5 Service and support
- <after-sales, SLA, on-site, training, local support, payment terms — as applicable>

---

## 3. Entry to a deal (offer layer, goes into profile.offer)

| Field | Your real value | Notes |
|---|---|---|
| `entry_offer` | <free sample / 14-day trial / free audit / pilot / site visit> | how a customer starts with zero or low risk |
| `cta_question` | <Open to a 20-minute demo next week?> | the closing question of the e-mail |
| `key_facts` | <2–4 short facts> | e.g. MOQ 50 pcs · setup in 2 days · ISO 9001 certified |
| `proof_points` | <publishable case studies> | customer-authorised or de-identified |
| `repeat_hook` | <our 2027 range is ready / v3 is live> | for repeat-order follow-ups with existing customers |

---

## 4. Product / service × customer-type match

> List the 3–7 customer types you most want to develop and, for each, "which line + which selling point + preferred hook".

| Customer type | Recommended line (need_tag) | Entry selling point | Preferred hook (industry_playbooks §2) |
|---|---|---|---|
| <customer-type-1> | <line_a> | <differentiator> | <2.x> |
| <customer-type-2> | <line_b> | <differentiator> | <2.x> |

---

## 5. Time windows (if applicable)

> Seasons, fiscal-year budgets, tender cycles, trade shows, regulation effective dates, release rhythm … write them if you have them, otherwise delete this section.
- Key window: <window>
- Backward schedule: <from first contact → trial/sample → decision → delivery>

---

## 6. Differentiation phrase bank (English, must rest on the facts in section 2)

| Hook type | English phrase |
|---|---|
| Core difference | <your measurable difference> |
| Entry threshold | <min_commitment fact> |
| Delivery speed | <delivery_time fact> |
| Customisation | <customisation fact> |
| Compliance / credentials | <certification fact, certificate required> |
| Case study | <proof point, authorisation required> |

> These are the **fact material** for AI-drafted e-mails; whether and how to use them is your decision after reviewing the draft.

---

## 7. Banned words and industry compliance additions

General baseline: `industry_playbooks.md` §5. Add the banned / mandatory statements of your industry here, for example:
- Medical / health: no efficacy or diagnostic claims
- Food: no health-benefit claims; allergens and labelling per the importing country's rules
- Finance / investment: no promised returns
- Software: list only security certifications actually obtained; state the compliance basis when personal data is involved
- <your-industry-specific rule>
