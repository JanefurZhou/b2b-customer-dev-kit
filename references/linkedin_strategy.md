# LinkedIn Outreach Strategy (Universal B2B Kit · Any Industry)

> LinkedIn is the primary channel for finding **named decision-makers** and escaping generic mailboxes
> (info@/sales@). This playbook is industry-neutral: everywhere a product term appears as
> `<example-product-term>`, substitute the `product.primary_keywords` from your own
> `config/company_profile.json` (created during first-run onboarding — see SKILL.md and
> `onboarding_questions.md`). Never invent titles, numbers, certifications or contact details.
>
> The title library below is procurement-oriented (goods, parts, consumables). If you sell software,
> services or projects, swap the role words for your own `targeting.buyer_titles` (e.g. CTO, HR director,
> head of marketing, project director) — every Boolean command keeps the same structure.

## Boolean Search Command Library (21 Commands)

### A Group: Boolean Basics (3 commands)

| # | Command | Purpose |
|---|---|---|
| 1 | `"sourcing manager"` | Exact match for full title |
| 2 | `purchasing OR sourcing OR procurement OR buyer` | Search all buyer types in one query |
| 3 | `buyer NOT recruiter NOT sales NOT "business development"` | Exclude recruiters and competitors |

### B Group: Position + Product Combinations (6 commands)

> Replace `<example-product-term>` with your own primary keywords; `<related-category-term>` with adjacent
> category words your buyers also use.

| # | Command | Purpose |
|---|---|---|
| 4 | `("purchasing manager" OR "sourcing manager") AND (<example-product-term> OR <related-category-term>)` | Lock category to relevant buyers |
| 5 | `procurement AND (<example-product-term> OR <related-category-term>) NOT recruiter` | Procurement + category, noise removed |
| 6 | `"product development manager" AND (<example-product-term> OR <related-category-term>)` | Influence-layer KP |
| 7 | `"category manager" AND (<example-product-term> OR <related-category-term>)` | Category manager targeting |
| 8 | `("supply chain" OR sourcing) AND director AND (<example-product-term> OR <related-category-term>)` | Decision layer combined search |
| 9 | `"{target brand name}" buyer` | Single-brand buyer targeting |

### C Group: Google Site Search (6 commands, doesn't use LinkedIn search quota)

| # | Command | Purpose |
|---|---|---|
| 10 | `site:linkedin.com/in "purchasing manager" (<example-product-term> OR <related-category-term>)` | Google searches LinkedIn profiles |
| 11 | `site:linkedin.com/in (sourcing OR procurement) <example-product-term> {country}` | Add country dimension |
| 12 | `site:linkedin.com/in "product development" <example-product-term>` | Find influence-layer KPs |
| 13 | `site:linkedin.com/company <example-product-term> {country}` | Batch mine target company pages |
| 14 | `site:linkedin.com/company <example-product-term> distributor OR wholesaler OR importer` | Find distributors and importers |
| 15 | `site:linkedin.com/in "purchasing manager" "{city}"` | City-level precision targeting |

### D Group: LinkedIn Filters & Scenarios (6 commands)

| # | Command/Action | Purpose |
|---|---|---|
| 16 | People filter: Region + Industry + Size 51-200 | Small-medium brand sweet spot: has budget, short chain |
| 17 | People filter: Region + Industry + Size 201-500 | Mid-size brand sweet spot |
| 18 | Keyword + 2nd degree connection filter | Leverage mutual connections for higher acceptance |
| 19 | Position word + Current company industry filter | Lock currently-employed real KPs |
| 20 | Search members within group pages | Use free same-group DM channel |
| 21 | Search Posts for your primary keywords, check posters | Reverse-find active KPs |

## Position Word Library (28 Words, 3 Tiers)

### Decision Layer (manage direction)

| Position (EN) | Chinese | Tier |
|---|---|---|
| Purchasing Director | 采购总监 | Decision |
| Procurement Director | 采购总监(职能向) | Decision |
| Sourcing Director | 寻源总监 | Decision |
| Supply Chain Director | 供应链总监 | Decision |
| VP Sourcing | 寻源副总裁 | Decision |
| VP Supply Chain | 供应链副总裁 | Decision |
| Head of Procurement | 采购负责人 | Decision |
| Head of Buying | 采购团队负责人 | Decision |

### Execution Layer (manage implementation)

| Position (EN) | Chinese | Tier |
|---|---|---|
| Purchasing Manager | 采购经理 | Execution |
| Procurement Manager | 采购经理(职能向) | Execution |
| Sourcing Manager | 寻源经理 | Execution |
| Category Manager | 品类经理 | Execution |
| Senior Buyer | 高级采购 | Execution |
| Buyer | 采购 | Execution |
| Procurement Specialist | 采购专员 | Execution |
| Sourcing Specialist | 寻源专员 | Execution |
| Purchasing Agent | 采购代理 | Execution |
| Supply Chain Coordinator | 供应链专员 | Execution |
| Import Manager | 进口经理 | Execution |
| Supply Chain Manager | 供应链经理 | Execution |

### Influence Layer (manage selection)

| Position (EN) | Chinese | Tier |
|---|---|---|
| Product Development Manager | 产品开发经理 | Influence |
| Product Manager | 产品经理 | Influence |
| R&D Manager | 研发经理 | Influence |
| NPD Manager | 新品开发经理 | Influence |
| Brand Manager | 品牌经理 | Influence |
| Operations Manager | 运营经理 | Influence |
| Quality Manager | 质量经理 | Influence |
| Managing Director | 总经理(中小企业常兼采购) | Influence |

> 上表偏「采购」职能，适合卖产品/零部件/耗材。卖软件、服务或项目时，把决策层换成对应职能（写进 `targeting.buyer_titles`）：
> 软件 → CTO / VP Engineering / Head of IT / VP Operations / CMO；服务 → CEO / Founder / Managing Director / Head of Marketing / HR Director / CFO；
> 项目型 → Project Director / Procurement Manager / Head of Engineering / Architect；物流 → Logistics Manager / Supply Chain Director / Import Manager。
>
> 非采购职能的布尔式示例（结构与下面 21 条相同，只换角色词）：
> - 软件：`("CTO" OR "VP Engineering" OR "Head of IT") AND (<customer-industry>) AND {country}`
> - 服务：`("Head of Marketing" OR "Managing Director" OR "Founder") AND (<customer-industry>)`
> - 项目：`("Project Director" OR "Procurement Manager") AND (contractor OR developer) AND {country}`

### Profile-driven Search Combos

When generating search commands, combine tier position words with **your own** keywords:

```
Decision layer:
("purchasing director" OR "sourcing director" OR "head of buying") AND (<example-product-term> OR <related-category-term>)

Execution layer:
("purchasing manager" OR "sourcing manager" OR "buyer" OR "category manager") AND (<example-product-term> OR <related-category-term>)

Influence layer:
("product development manager" OR "product manager" OR "brand manager") AND (<example-product-term> OR <related-category-term>)
```

## Connection Request Templates (3 Styles)

### Template 1: Common Ground Style (highest acceptance; shared group/mutual connection)

**With shared group:**
```
Hi {Name}, I noticed we are both members of {Group Name} — I enjoyed the recent discussion on {topic}. I work on the {your-core-term} side and would be glad to connect.
```

**With mutual connection:**
```
Hi {Name}, I saw we are both connected with {Mutual Name}. I work in {your-core-term} — would be glad to connect.
```

### Template 2: Value Style (when you observe company expansion/activity)

```
Hi {Name}, noticed {Company} is expanding its {area}. We support teams like yours with {one verifiable differentiator from your profile} — {one fact from offer.key_facts}. Thought connecting could be useful.
```

### Template 3: Asking Style (when target has posted content; nearly impossible to refuse)

```
Hi {Name}, your post on {topic} was a great read. I work in {your-core-term} and would like to follow your insights. Hope to connect.
```

### Connection Request Rules
- Keep notes under 150 characters (2-3 lines, no mobile folding)
- Send ~20/day, steady pace (don't spike and rest)
- First 3 messages: NO pricing, product links, or "do you need"
- Target acceptance rate: 20%+ (internal starting target set by this skill, not an industry statistic — adjust to your own baseline)

## Post-Connection: 5:3:2 Rhythm & Icebreaker

### 5:3:2 Rhythm
Before sending the first real message:
- Like 5 of their posts over several days
- Write 3 industry-insight comments on their content
- Then send 2 messages (first = icebreaker, second = value follow-up)

### Icebreaker (2-sentence structure: reference specific activity + light question)

```
Saw {Company} launched {new product/service/project} last month — that space is getting real traction in {market}. How are you resourcing it?
```

Generic variants (adapt to the real signals you observed):

```
Saw your post about expanding into {new area} — how are you handling {the part you solve} for it, in-house or with an external partner?

Noticed {Company} is moving into {adjacent category}. What markets are you primarily targeting?

Saw your comment in {Group} about {challenge} — that comes up a lot with teams like yours. Have you found a reliable way to handle {your-core-term} yet?
```

## Three-Sentence Development Message (LinkedIn InMail)

### Structure

| Sentence | Task | Writing Rule |
|---|---|---|
| 1st | Why YOU | A specific fact only relevant to them (launch/expansion/new project/hiring/post) |
| 2nd | One-sentence value | What you help with + one verifiable number/fact from your profile |
| 3rd | Question ending | Answerable in 10 seconds, never "looking forward to cooperating" |

### Generic example (replace bracketed facts with your real profile values)

```
Noticed {Company} is expanding its {area}. We provide {your one_liner_en} for teams in {region} — {offer.key_facts[0]}, {offer.key_facts[1]}. Would it help if I sent over a short overview?
```

## Five Opening Angles (rotate to avoid repetition with same KP)

| Angle | Example First Sentence |
|---|---|
| Activity reference (preferred) | `Saw your post last week about {topic} —` |
| Shared group | `Your comment in {Group} on {thread} caught my eye —` |
| Industry event (fallback) | `With {trade show} coming up in {market} —` |
| Similar case | `We recently helped a {country} brand fix {problem} —` (only if the case is real) |
| Product pain point | `Many buyers tell us {verifiable category pain point} is their top headache —` |

## Pre-Send Self-Check (3 Questions)

Before sending any outreach message, verify:
1. Is the first sentence specific to THIS person? (not generic)
2. Is the number/claim in sentence 2 verifiable and present in your profile?
3. Can they answer sentence 3 in 10 seconds?

If ANY fails, rewrite.

## Transfer to Email (use after second round of replies)

```
Happy to put the details together in one file — which email works best for you?
```

(Rule: let them give the email, don't ask for it)

## Free DM Channels
1. Same-group members can DM directly (no InMail needed)
2. Accounts with "Open Profile" badge can be messaged by anyone

## 1-3-7-21 Follow-Up System

| Timing | Purpose | Content & Hook Example | Key Action |
|---|---|---|---|
| Day 1 | Lock momentum | Send summary + useful resource | Hook: meeting notes / industry resource |
| Day 3 | Deepen relevance | Add one relevant info point (real case) | Hook: case study update |
| Day 7 | Push next step | Ask one specific small question (spec/qty/timing) | Hook: light reminder |
| Day 21 | Stay present | Industry news or new product, value-type touch | Hook: industry news / new product |
| Monthly | Long-term presence | One value touchpoint per month + weekly content coverage | Hook: trade show / industry report / new release |

### Follow-Up Stop Conditions (Loop Guards)

| Scenario | Stop After | Next Action |
|---|---|---|
| KP never replies to any of the 4 touchpoints (Day 1/3/7/21) | All 4 attempts sent | Move to Grade C — content coverage only, no individual outreach |
| KP replies once then goes silent | 2 follow-ups over 14 days | Escalate to the account owner: continue or archive? |
| KP explicitly says "not interested" or "not now" | Immediately | Archive. Re-approach only after 90 days or on a buying signal |
| KP asks to be contacted at a specific time | Set reminder | Pause all outreach until that time |
| KP bounces back (email/LinkedIn invalid) | Immediately | Mark unreachable in pipeline, move on |

**Hard rule**: Never send more than 4 follow-up messages to a KP who never replied. After 4, they're Grade C.

### Follow-Up Message Examples

**Day 1:**
```
Hi {Name}, great connecting! As promised, here's a quick overview of our capabilities plus a short checklist for evaluating {category} options. Let me know if any questions come up.
```

**Day 3:**
```
Hi {Name}, following up with a quick case — we recently helped a {country} brand resolve {specific, real problem}. Thought it might be relevant to what you mentioned.
```

**Day 7:**
```
Hi {Name}, quick question — for your upcoming {project/launch/season}, are you looking at {option A} or {option B}? This helps me prepare the most relevant {entry_offer} for you.
```

**Day 21:**
```
Hi {Name}, saw this article about {category} trends in {market} and thought of you. There's a new development on our side that might interest you. No rush — just wanted to keep you in the loop.
```

## Customer Grading & Pipeline Tracking

### Grading System

| Grade | Definition | Touch Frequency |
|---|---|---|
| A | Discussed specific needs, warm lead | Weekly active outreach |
| B | Interacted, no specific needs yet | Every 2 weeks |
| C | Connected, no interaction | Content coverage only |

Re-grade every 2 weeks:
- B with needs emerging → upgrade to A
- A with 3 no-responses → downgrade to B

### Closing Techniques (for A-grade customers)
1. **Live proof**: a video tour of production, a live product demo, or a case walkthrough — whichever shows your real process ("seeing is believing")
2. **Sample proposal**: send physical samples (state real sample lead time and who bears freight)

### Pipeline Tracking Table (5 fields, update daily in 5 min)

| KP Name | Company | Stage | Last Contact | Next Follow-up |
|---|---|---|---|---|
| {Name} | {Company} | Sample sent | {date} - Quote confirmed | {date} |

### Optimization Benchmarks (internal thresholds set by this skill, not industry statistics)
- Connection acceptance rate < 20% → fix profile & connection notes
- Conversation rate < 20% → fix icebreaker messages
- Inquiry conversion < 10% → fix follow-up rhythm
- Fix whichever layer is stuck

### Fallback: When Boolean Search Yields Few Results

If search returns < 10 viable KPs:

1. **Broaden position words**: add "merchandiser", "import coordinator", "supply chain analyst"
2. **Broaden category words**: use the related/adjacent category terms from your profile
3. **Remove NOT filters**: temporarily remove `NOT recruiter NOT sales` to cast wider net, then filter manually
4. **Switch to Google site search**: use `site:linkedin.com/in` commands (Group C), which don't use LinkedIn quota
5. **Lower company size threshold**: try 11-50 employees (very small brands often have the founder purchasing)
6. If still < 10 → report to the account owner; consider a different region or vertical temporarily

## 30-Day Action Checklist

### Week 1: Setup + Database Building

| Task | Daily Action | Weekend Checkpoint |
|---|---|---|
| Profile optimization (7 elements) | Complete all 7 elements | 3-second scroll test passes |
| Build 28-word position library | Adapt to your industry | Database complete |
| Daily new target list | Add 40-50 people/day | List reaches 300+ |

### Week 2: Outreach

| Task | Daily Action | Weekend Checkpoint |
|---|---|---|
| Connection requests | ~20/day, rotate 3 template styles | Acceptance rate 20%+ |
| Icebreakers | Use 2-sentence structure for accepted connections | Conversations starting |

### Week 3: Content + Network

| Task | Daily Action | Weekend Checkpoint |
|---|---|---|
| Content posting | 3 posts/week (production photos, process, real cases) | Engagement visible |
| Old contact re-mining | Check past contacts for new opportunities | |
| Industry groups | Join 3-5 relevant groups, lurk first | New conversations 5+/week |

### Week 4: Follow-up + Review

| Task | Daily Action | Weekend Checkpoint |
|---|---|---|
| Follow-up | Roll 1-3-7-21 table | Follow-up execution rate 100% |
| Review | Weekly review of 3 numbers | Month-end full review |

### Daily 30-Minute Standard Actions

| Time | Action |
|---|---|
| 5 min | Check profile visitors, return visits (welcome message, no interrogation) |
| 10 min | Send connection requests (~20, steady pace) |
| 10 min | Reply messages + feed interaction (likes, industry comments) |
| 5 min | Update pipeline tracking table (tomorrow's follow-ups from the table) |

## Five Common Pitfalls (Self-Check)

1. **Bare account mass-sending**: sending requests before profile is optimized
2. **Connect but don't interact**: 2000 connections with zero interaction = dead list
3. **First message is a pitch**: treating icebreaker as a quote
4. **Follow-up abandoned**: most people quit between Day 7 and Day 21
5. **No records**: tracking customers by feel, losing track of where they dropped off

## Profile Optimization Checklist (7 Elements)

1. **Avatar**: Professional headshot, clean background, approachable expression
2. **Headline**: `[Title] at <your-brand> | {your one_liner_en} | {one differentiator}`
3. **About** (3-part structure, under 120 words):
   - Part 1: Who am I (your real business and years of experience)
   - Part 2: Who I help + 2-3 capability facts strictly from your profile (e.g. offer.key_facts: minimum commitment, delivery/onboarding time, certifications…)
   - Part 3: Verifiable credentials (brands worked with, websites) — only real ones
4. **Recommendations**: 3+ recommendations from past clients or partners
5. **Featured section**: catalogue / case study / demo video / product or project photos (whatever proves your offer)
6. **Recent activity**: Post 3x/week minimum
7. **Language**: match target regions; localize for key markets

### About Section Template

```
I'm {your role} at <your-brand>, where we {your real business description}. We provide {your offer lines} to {customer types} in {regions}.

We help {target customer} with {your-core-term}:
- {real differentiator 1}
- {real differentiator 2}
- {real differentiator 3}

Past clients include companies across {regions — only if true}. Happy to share industry insights — connect if you work on {category}.

<your-domain> | WhatsApp: +<country-code-number>
```

## AI Prompt Pack for LinkedIn Content (10 Prompts)

When asked to generate LinkedIn content, use these prompt structures (fill every bracket from your profile):

1. **Boolean search strings**: "I provide {your one_liner_en}, target market {country}. Generate 15 LinkedIn Boolean search commands by decision/execution/influence tiers."
2. **Position word expansion**: "Based on who buys {your one_liner_en}, add 20 English position titles, classified by tier."
3. **Connection request notes**: "Write 3 LinkedIn connection request notes (common ground/value/asking style) under 150 chars for {position}@{company}."
4. **Icebreaker messages**: "Based on this company update '{summary}', write a 2-sentence icebreaker: sentence 1 references the update, sentence 2 asks a light question. No pricing/links/intro."
5. **Three-sentence message**: "Write a 60-word outreach message (relevant fact / value + verifiable number / question ending) for {your one_liner_en}."
6. **5 opening angles**: "Generate 5 opening first-sentences for {category} decision-makers: activity reference / shared group / industry event / similar case / product pain point."
7. **Weekly follow-up hooks**: "Generate 4 follow-up hooks for {market} this week (industry news / new product / case study / holiday-event), each with an opening line."
8. **Weekly content topics**: "Generate 3 weekly content topics (production photos / process / case study / interactive question / personal story), each with first 3 hook lines."
9. **Group professional reply**: "Someone in an industry group asked '{question}'. Write a professional answer as a {your role}: answer thoroughly, zero ads at the end."
10. **About section**: "Write a LinkedIn About section (3-part: who / problem solved + capability facts / verifiable credentials), under 120 words."
