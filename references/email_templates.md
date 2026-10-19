# Cold e-mail template bank (short and direct · cross-industry skeleton)

> Pick the template by `solution_tag` (the "what the customer cares about most" set after research). Each template ≤60 words (signature excluded).
>
> This file is an **industry-independent skeleton**: product / service positioning, selling points, entry offer, key facts and contact details all come from
> the `config/company_profile.json` created at first install and are substituted by the AI when drafting; **never copy the examples verbatim, never invent numbers or selling points that are not in the profile**.
>
> **Placeholder convention**
> | Placeholder | Source | Physical goods example | SaaS example | Service example |
> |---|---|---|---|---|
> | `[Company]` | customer fact | | | |
> | `[Category]` | `product.primary_keywords[0]` | stainless valves | HR software | SEO audits |
> | `[Positioning]` | `product.one_liner_en` | | | |
> | `[Differentiator N]` | `product.differentiators` | | | |
> | `[Entry]` | `offer.entry_offer` | free sample | 14-day trial | free audit |
> | `[Fact N]` | `offer.key_facts` | MOQ 50 pcs | setup in 2 days | fixed fee from €900 |
> | `[Closing]` | `offer.cta_question` | Worth a sample? | Open to a demo? | Want the audit? |
> | `[Case]` | `offer.proof_points` | (authorised or de-identified) | | |
> | `[WA]` | `contact.whatsapp` | omit the WhatsApp line when empty | | |

## Usage rules

1. **Research first, set need_tag (which line) + solution_tag (what matters most), then pick the template** (see research_guide.md).
2. Everything in `[brackets]` must come from customer facts or the confirmed profile; if missing, ask, never invent.
3. Follow-up e-mails must carry new information; never copy the first e-mail and change only the name.
4. Add the WhatsApp CTA only when the profile has a WhatsApp number.
5. **Banned phrases**: I came across / I thought / I'd love to / we specialize in / could be a great fit / happy to.
6. Match the language of the customer's country; German / French / Italian greetings and closings are localised automatically by the scripts by region.

---

## 1. First-contact templates (by solution_tag)

### 1.1 Compliance / credentials first · `compliance` / `sustainability`

**Subject**: Documented [Category] for [Company]

> Hi [Name],
>
> [Company]'s [compliance / ESG focus] — noted. [Differentiator 1: the exact certificate / credential matching their concern].
>
> • [Fact 1]
> • Documentation before any commitment
>
> [Closing] [WhatsApp line, only when a number exists]

### 1.2 Quality / difference first · `quality_upgrade` / `exclusive_custom`

**Subject**: [short version of Differentiator 1] — for [Company]

> Hi [Name],
>
> Why teams like [Company]'s switch to us:
>
> • [Differentiator 1]
> • [Differentiator 2]
> • [Fact 1] · [Fact 2]
>
> [Entry] available. [Closing]

### 1.3 Low-commitment start · `low_commitment` / `cost`

**Subject**: An easy way to test [Category] — [Company]

> Hi [Name],
>
> No big commitment needed to try us:
>
> • [Entry]
> • [Fact 1] · [Fact 2]
> • [Differentiator 1]
>
> [Closing]

### 1.4 Speed / deadline · `speed`

**Subject**: Ready before [customer's deadline]

> Hi [Name],
>
> Planning for [customer's deadline: peak season / launch date / construction schedule / budget window]? Starting now → [delivery / go-live time] → ready by [date].
>
> • [Differentiator 1]
> • [Fact 1]
>
> [Closing]

### 1.5 New direction / expansion · `innovation` / `one_stop`

**Subject**: For [Company]'s [new move]

> Hi [Name],
>
> Saw [Company] is [new move: new product line / new market / funding / new project]. [Positioning], and [Differentiator 1].
>
> Easy start: [Entry]. [Closing]

### 1.6 Dedicated / scale · `dedicated_service` / `strategic_scale`

**Subject**: [Category] support built for [Company]

> Hi [Name],
>
> [Differentiator 1]. One named contact from first call to delivery; [Fact 1].
>
> [Closing]

### 1.7 Generic exploration · `open` / `unknown` (when research signals are insufficient)

**Subject**: [Category] for [Company]

> Hi [Name],
>
> [Positioning]. What clients value:
>
> • [Differentiator 1]
> • [Differentiator 2]
> • [Fact 1]
>
> [Closing]

---

## 2. Follow-up e-mails (differentiated progression)

> ⚠️ Every follow-up must carry new information (new case / new angle / new version / new data); never copy the first e-mail and change only the name; respect the cooldown and per-contact frequency rules.

### 2.1 Follow-up 1 (after the configured cooldown days following the first e-mail)

**Subject**: Re: [keyword of the new information]

> Hi [Name],
>
> Quick follow-up. Recently [Case: must be real and publishable] for a [region / industry] client — [result].
>
> [Entry] still open. [WhatsApp line]

### 2.2 Follow-up 2 (new angle)

**Subject**: [keyword of the different angle]

> Hi [Name],
>
> Different angle: [new angle, e.g. pilot size / custom solution / timing]. Helped a [customer type] get [result] starting with [Entry].
>
> Worth 5 minutes?

### 2.3 Follow-up 3 (light exit)

**Subject**: Last note — [Company]

> Hi [Name],
>
> Won't follow up again. If [Category] comes up on your side — we're here. [Fact 1].
>
> [WhatsApp line]

---

## 3. First WhatsApp message (only when a number exists)

**First contact**:
> Hi [Name], [one specific observation about them]. We provide [Positioning] — [Fact 1]. Want me to send a short overview?

**Follow-up / repeat order**:
> Hi [Name], quick update: [offer.repeat_hook]. Want me to send the details?

---

## 4. Pre-send self-check

- [ ] No filler like "I came across / I thought / I'd love to / great fit"?
- [ ] Body ≤60 words (signature excluded)?
- [ ] Every bullet is a fact / number taken from the profile, not invented?
- [ ] Every `[...]` in the template replaced, no leftover placeholders?
- [ ] Industry compliance (medical / food / finance claim limits) checked?
- [ ] Only contact details confirmed at install; no WhatsApp line forced in without a number?
- [ ] Language matches the customer's country; sent inside the customer's local working hours?
- [ ] Signature identical to the profile, no fields added or removed?
