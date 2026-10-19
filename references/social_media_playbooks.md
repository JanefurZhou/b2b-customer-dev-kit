# Playbook for the 10 overseas social media platforms (all industries · login-free public search first)

> Platforms: LinkedIn / Instagram / Facebook / YouTube / TikTok / Pinterest / X / Threads / WhatsApp / Lemon8
> Core idea: **social media is an acquisition tool, not a publishing platform.** No chasing followers or likes; 80% of the time goes to search + reach, 20% to supporting content.
> Execution boundary of this skill: **the scripts do login-free public search only** (handing `site:` queries to Google / Bing) and extract company and decision-maker leads from pages already indexed publicly;
> **anything that requires registration / login** (connection requests, DMs, joining groups, follower lists, likes and comments) is marked "manual · login required", decided by the user, never executed automatically by this skill.
> Every social lead still goes through: website → named mailbox → `filter --against` DB de-dup → research (S1/S2 evidence) → positioning → three pre-send checks before any e-mail.

---

## 1. One command generates public search queries for 10 platforms

```bash
python3 scripts/search_customers.py social                 # the 10 platforms: role / public queries / what to extract / which actions need login
python3 scripts/search_customers.py social --titles        # 30 procurement-chain titles (decision / execution / influence tiers)
python3 scripts/search_customers.py social --all --regions UK,DE --out social.txt
python3 scripts/search_customers.py social --platforms linkedin instagram --tier decision
python3 scripts/search_customers.py social --platforms youtube --urls   # adds YouTube on-site search links (public pages, no login)
```

- Where the terms come from: category / customer-industry terms = `product.primary_keywords` (software / service businesses use the customer anchor `targeting.customer_industries` instead); role terms = `targeting.channel_keywords`; titles = `targeting.buyer_titles` first, title bank as backup; competitors = `targeting.reference_brands`.
- Platform switch: `search.social_platforms` (empty = all 10).
- Using the results: search result page → open the public profile / company page → take the website → back to the results file of "Step 1 Search Candidates" in the main flow, through `filter --against`.

## 2. Platform roles at a glance

| Platform | Rating | Place in the loop | Login-free public search yields | Manual · login required (not executed by this skill) |
|---|---|---|---|---|
| LinkedIn | ⭐⭐⭐⭐⭐ | find decision makers | name, title, company page, website; buying / tender signals in posts | connection requests, InMail, Sales Navigator |
| Instagram | ⭐⭐⭐⭐ | find brands / stores | website link in bio, city, stockist / wholesale labels; retailers that @ competitors | follower / following lists, hashtag page scrolling, DMs |
| Facebook | ⭐⭐⭐ | find groups / business pages | public group names and topics, website / e-mail / address in page About | joining groups, posting, Messenger |
| YouTube | ⭐⭐⭐ | buyers in comments / channels | channel "business enquiries" e-mail, website links, buyers identifying themselves in comments | comments, subscriptions |
| TikTok | ⭐⭐⭐ | short-video / comment signals | website in bio, brand name, "where do you source" accounts in comments | comments, DMs |
| Pinterest | ⭐⭐⭐ | boards / long-tail brands | brand / store websites behind Pin links | saves, DMs |
| X (Twitter) | ⭐⭐ | listening for need posts | accounts posting "looking for / recommend a supplier" | replies, DMs |
| Threads | ⭐⭐ | linked with IG | same-name account → back to the IG public page for the website | replies, DMs |
| WhatsApp | ⭐⭐⭐⭐ | **conversion / follow-up home ground** (not a search source) | WhatsApp business numbers published on websites / directories (record only) | all sending goes through Step 7 wa_bulk engine + anti-ban rules |
| Lemon8 | ⭐⭐ | lifestyle posts / emerging brands | brand names in posts → search the website | comments, DMs |

## 3. Procurement-chain title bank (30 titles, three tiers)

Printed by `social --titles`; LinkedIn Boolean strings pick the tier with `--tier`. `targeting.buyer_titles` from the profile always comes before the bank.

| Tier | Role | Titles |
|---|---|---|
| decision tier | signs off, approves budget | Owner · Founder · CEO · Managing Director · General Manager · Head of Purchasing · Procurement Director · VP Operations · Commercial Director · Category Director |
| execution tier | finds suppliers, compares, orders | Buyer · Senior Buyer · Purchasing Manager · Procurement Manager · Sourcing Manager · Category Manager · Supply Chain Manager · Product Manager · Merchandiser · Vendor Manager |
| influence tier | raises needs, evaluates, influences selection | Operations Manager · Quality Manager · Technical Director · Engineering Manager · Project Manager · Product Development Manager · Brand Manager · Marketing Manager · IT Manager · Office Manager |

Reach order: execution tier first (knows the need best, replies most) → name the decision tier at the same time (signs off) → influence tier only for extra evidence (quality / technical requirements). Software / service businesses replace "Head of Purchasing"-type titles with the business owner of the function (CTO, HR Director, Head of Marketing …) in `buyer_titles`.

The 21 LinkedIn Boolean strings are in `references/linkedin_strategy.md`; the `social` sub-command generates their "login-free site: versions".

## 4. Playbook per platform (public search → manual action)

### 4.1 LinkedIn (decision makers)
1. `site:linkedin.com/in ("Buyer" OR "Purchasing Manager" OR "Owner") "<category>" "<region>"` → public decision-maker profiles.
2. `site:linkedin.com/company "<category>" <role term> "<region>"` → company page → website in About.
3. `site:linkedin.com/posts "<category>" ("looking for" OR sourcing OR RFQ)` → posts with buying signals = **S2 evidence** (see the evidence tiers in research_guide).
4. Manual · login required: connection request (≤300 characters, value before the ask; templates in linkedin_strategy.md).

### 4.2 Instagram (brands / stores)
1. **9 hashtag sets** (generated from the category term; browsing hashtag pages needs login, so the script generates only the `site:instagram.com "#tag"` versions): `#<category>` · `#<category>wholesale` · `#<category>supplier` · `#<category>b2b` · `#<category>store` · `#<category>brand` · `#<region><category>` · `#<category>design` · `#<category>trade`.
2. **Competitor follower mining (public version)**: follower lists need login → not done; instead `site:instagram.com "<competitor>" (stockist OR retailer OR "available at")` finds **retailers / dealers that publicly @ the competitor** — they already sell the category, the most precise buyers.
3. Extract: website in bio, city, stockist / wholesale labels.
4. Manual · login required: **three-sentence DM** — ① who I am + why you (one specific fact from your public profile) ② one verifiable fact (from `offer.key_facts`) ③ one low-threshold question (`offer.cta_question`).

### 4.3 Facebook (five-step group approach)
1. Find groups: `site:facebook.com/groups "<category>" (buyers OR wholesale OR B2B OR procurement)`.
2. Judge groups: buyer roles in the public name / description, recent activity → candidate group list (judged without joining).
3. Manual · login required: after joining, **give value first** (industry data, spec comparisons, pitfall lists), no hard ads.
4. Manual · login required: DM buyers who ask questions, with the three-sentence DM.
5. Back to the main flow: company name → website → named mailbox → DB check.

### 4.4 YouTube (buyers in comments)
- `site:youtube.com "<category>" (review OR unboxing OR "how to choose" OR "factory tour")`; `--urls` adds on-site search links (public pages, no login).
- Extract: business e-mail in the channel description, website links; people in comments identifying as "buyer at store / company X" (**S2**, verify on the website to make it S1).

### 4.5 TikTok / Pinterest / X / Threads / Lemon8
- TikTok: `site:tiktok.com "<category>" (wholesale OR supplier OR "small business")`; "where do you source" in comments = need signal.
- Pinterest: the Pin's external domain is the brand / store website; straight into candidates.
- X: `site:x.com "<category>" ("looking for" OR "recommend a" OR supplier OR RFQ)` listens for need posts.
- Threads: accounts usually share the IG name; back to the IG public page for the website.
- Lemon8: good for emerging / young brands; brand names in posts → search the website.

### 4.6 WhatsApp (conversion home ground, not a search source)
- Public search only to **record** business numbers published on websites: `"<category>" <role term> "<region>" ("wa.me" OR "WhatsApp Business")`.
- When to actually send: per the Step 7 WhatsApp trigger conditions (≥3 e-mails sent, no reply, no bounce / bounced with no alternative mailbox / high value with public WA / the customer gave the number), through `wa_bulk_sender.py convert → validate → preview → harness` and the 200-per-day limit.

## 5. Cross-platform coordination (one customer, several channels)

At most 3 channels per customer, in this order, **each step only after the previous one produced a result**:

1. E-mail (main channel, named decision maker) → 2. LinkedIn connection (manual, same decision maker) → 3. WhatsApp (only when the trigger conditions are hit).
Instagram / Facebook / YouTube etc. serve mainly to **find** customers and **add evidence**, not as a fourth or fifth channel on the same customer.
An explicit refusal on any channel → `csv_ops.py add_blacklist` → stop on every channel.

## 6. Follow-up cadence: social 1-3-7-21 vs the 5-level e-mail cooldown

| Channel | Cadence | Computed by |
|---|---|---|
| social (LinkedIn / IG / FB DMs, manual) | Day 1 ice-breaker → Day 3 value (industry info / spec comparison) → Day 7 case (user-confirmed cases only) → Day 21 switch channel (e-mail or WA) | manual note in notes: `social=li d1 2026-10-19` |
| e-mail (scripts) | 1st → 3 days → 2nd → 3 days → 3rd → 10 days → 4th → stop generic mailboxes (LinkedIn / personal mailbox only) → after the 5th e-mail stops entirely | `csv_ops.py cooldown <email>` (`COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}`) |
| WhatsApp (scripts + manual) | first message → continue only on reply; no second similar message without a reply | `wa_review.py` / `wa_contacts.csv` |

The two cadences **never stack**: one customer, one channel per day (`rules.same_contact_cooldown_hours`).

## 7. Evidence tiers (S1 / S2 / S3) — social leads especially need tiering

| Tier | Definition | Social examples | Allowed actions |
|---|---|---|---|
| S1 first-hand | explicitly stated on the customer's own official channels | website says "wholesale enquiries", company LinkedIn page states the business, tender / procurement posts from official accounts | direct basis for need_tag / solution_tag |
| S2 credible second-hand | public third-party or employee information, cross-checkable | employee post about looking for suppliers, trade media, exhibitor lists | usable, source in notes; one more S1 is better |
| S3 weak signal | guesses, fragments in comments, unverifiable | one comment, inference from a similar account, hashtag hit | **no conclusion** → `need_review`, user decides |

In notes: `evidence=S1:https://...;S2:https://...`. Full rules in the "evidence tiers" section of `references/research_guide.md`.

## 8. Compliance and boundaries

- Public pages only; no bypassing login walls, no automated bulk reading of platform pages, no automatic follows / connections / DMs.
- Platform terms and local privacy law (GDPR legitimate-interest assessment, right to object) outrank this playbook.
- Only business-relevant parts of personal profiles are taken (name, title, company); no private information is collected.
