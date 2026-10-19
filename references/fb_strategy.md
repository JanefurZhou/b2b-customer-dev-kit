# Facebook Groups Outreach Strategy (Universal B2B Kit · Any Industry)

> Facebook (Meta) groups remain one of the **lowest-cost discovery channels** for many B2B sellers — goods, services and software alike:
> members include business owners, buyers, operators, managers and distributors who openly discuss what they need.
> This playbook describes a **compliant, content-first** method. No cold pitching in groups and no harvesting of
> personal data. Every fact you cite about your own products must come from your onboarding profile
> (`config/company_profile.json` — see SKILL.md "first-run onboarding gate" and `onboarding_questions.md`).

---

## 1. Compliance and account safety (read first)

1. **Never post sales pitches in groups** — you will be banned and the account flagged. Value first, contact via DM.
2. **Use a real, complete personal profile** (or a properly set-up business Page acting through a named admin).
   Blank/new accounts that immediately post get restricted.
3. **Warm up a new account for 1–2 weeks** before outreach: join groups, read, react, comment without links.
4. Respect each group's rules; many ban any commercial DM. If the rules forbid it, don't DM — answer publicly instead.
5. Don't paste the same message to dozens of members; vary wording manually and keep volume modest
   (suggested cap: ~20 meaningful group actions and ~10 DMs per day).
6. DM only people who publicly signaled a sourcing need or replied to your comment.
7. Your own identity/signature/website/WhatsApp come **only from the profile** — never invent contact details.

---

## 2. What kinds of groups to join (generic)

Pick group types that fit the customer segments defined in your `targeting` profile:

- **Buyer groups** for your category (importers/distributors for goods; operators/managers for software and services)
- **Customer-type groups** that match your `targeting.channel_keywords` (e.g. retailers, contractors, founders, HR leaders, ecommerce sellers) in your target regions
- **Trade-show or industry-association groups** (post-show member lists are rich sources)
- **Sourcing / supply-chain discussion groups** (buyers asking for suppliers)
- **Local-language business groups** in each target country (search in the local language, not only English)

Red flags (skip): pure MLM groups, "like-for-like" promo groups, groups dominated by other suppliers selling
the same thing, groups with no moderation.

### 2.1 How to find groups (search syntax)

Use the Facebook search box with combinations such as:

- `<your-core-product> importers`
- `<your-core-product> buyers group`
- `<category> wholesale` / `<category> sourcing` (physical goods)
- `<country> retail business owners` (consumer goods)
- `<customer-industry> founders` / `<role> community` / `<category> users` (software / services)
- `<trade show name> exhibitors` / `<industry association> members`

Replace `<your-core-product>` / `<category>` with `product.primary_keywords` from your profile.
Target **20–40 groups** initially; prune to the 10–15 most active.

---

## 3. Three-phase playbook

### Phase A — Lurk and map (days 1–7)

- Read the group: who posts buying questions? Who answers helpfully? Who are the admins?
- Note recurring pain points (MOQ, lead time, quality consistency, certifications, language/time-zone gaps).
- Build a simple list: member name / business / role / country / signal (what they asked) / group / date.

### Phase B — Value comments (ongoing)

Answer sourcing questions **thoroughly and without self-promotion**:

- Explain how to evaluate the thing they're asking about (specs, checks, red flags).
- Share a generic checklist; do not attach company catalogs in public comments unless rules allow.
- End without a CTA. Your goal is to be recognized as a knowledgeable supplier-side person.

### Phase C — Permission-based DM (only when invited)

Trigger conditions for a DM:
1. They replied to your comment asking for more, OR
2. They posted a sourcing request that clearly matches what you do.

DM opening structure (2 short sentences):
1. Reference their exact question/post.
2. Offer one specific, relevant piece of help — no pricing, no catalog dump, no "do you need a supplier".

```
Hi {Name}, saw your question in {Group} about {their topic}. The point most buyers get wrong is
{one specific insight}. If useful I can share a short spec checklist we use internally.
```

Only after they respond positively may you introduce your company, using facts strictly from your profile
(`product.one_liner_en`, `product.differentiators`, `product.moq`, `product.sample_lead_time`).

---

## 4. Signal library — what good buying signals look like

| Signal in a post/comment | Meaning | DM action |
|---|---|---|
| "Looking for a supplier of ..." | Active sourcing | Answer publicly, then DM with one insight |
| "Current supplier issues / delays / defects" | Dissatisfaction | Offer a diagnostic checklist |
| "Small quantity, everyone quotes huge MOQ" | MOQ pain | Relevant only if your real MOQ fits — quote the real number |
| "Need certification for {market}" | Compliance barrier | Help explain the cert requirements first |
| "New brand, how do I start?" | Early-stage buyer | Share a generic starter checklist |
| Expansion / launch / new project post | Demand forming | Congratulate + one relevant observation |

Never fabricate a match. If your real capability doesn't fit the signal, skip.

---

## 5. Content you can post occasionally (if group rules allow)

- A genuinely educational post: "How to inspect {product category} before a bulk order"
- A market observation: "{raw material / regulation / trend} update — what it means for buyers"
- A neutral teardown of a common quality problem in the category
- No price lists, no "contact us", no links to your store

Profile/Page info and the pinned post (not group posts) carry the company introduction.

---

## 6. Profile / Page essentials (filled from your onboarding profile)

- Display name and role: use `contact.founder_name` / your real title
- Intro line: `product.one_liner_en`
- About: who you help + 2–3 verifiable `differentiators`; website only if it is your real domain
- Contact: the email/WhatsApp from the profile; **secrets never go here**
- Languages: match `targeting.target_regions` / `targeting.languages`

---

## 7. Moving contacts into the pipeline

1. After a real DM conversation, ask which email works best — let **them** offer it.
2. Verify the domain/email (`dns_validator.py`), dedupe against the main DB (`csv_ops.py check`).
3. Research the company (`research_guide.md`), then add to the candidate pool with
   `source_channel = Facebook Group:{Group Name}`.
4. Continue through the standard email/WhatsApp flow; Facebook is the **discovery** layer, not the sending layer.

---

## 8. Daily/weekly routine

| Frequency | Actions |
|---|---|
| Daily (~20 min) | Scan 3–5 priority groups; answer 1–3 questions; DM only on fresh signals |
| Weekly | Add signals to the prospect list; prune dead groups; post one educational piece |
| Monthly | Count leads by group; double down on groups that actually produced conversations |

Benchmarks to watch (generic): signal→reply rate, reply→email-share rate. Track `source_channel` so you can
attribute real wins per group in `success_cases.csv`.

## 9. Common mistakes

1. Pitching in the group on day one → ban.
2. Harvesting member lists / mass DMs → account restriction and bad reputation.
3. Quoting capabilities you don't have → trust loss at the sample stage.
4. Treating Facebook as the closing channel → it only finds and warms people.
5. No records → you cannot tell which groups work.
