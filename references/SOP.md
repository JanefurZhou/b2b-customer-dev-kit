# B2B Customer Development Standard Operating Procedure (SOP)

**Version**: v3.1 | **Updated**: 2026-10-19  
**Scope**: every B2B cold-e-mail customer development task

---

## 📋 Overview: Install Gate + Step 0 + the seven-step main flow (v3.1)

> First thing after installing: `python3 scripts/onboarding.py start` (new-install checklist) → pass all three checks (required profile fields → Soul Seven Kit health check 7/7 → the user's own confirmation via attest) before entering the flow below.
> Every step's "exit / loop-back" is listed in the loop checklist of `references/sop_flowchart.md` — a step without an exit counts as unfinished.

```
Install Gate (start → init → required profile → kit-check 7/7 → check → attest = READY)
  ↓
Step 0 Omni-channel Review ─→ Step 1 Search Candidates ─→ Step 2 Background Research ─→ Step 3 Need Positioning ─→ Step 4 Write Content
 success_cases                  queries/channels            research_guide                 need_tag +                  email_templates
 wa_review                      social · filter             S1/S2/S3                       solution_tag                quote S1/S2 only
 MEMORY weekly conclusions      funnel                      only S3 → need_review           conflict-check
  ↑                                                                                                                      ↓
Step 8 Win Review + Kit Write-back ←─ Step 7 WhatsApp Trigger ←─ Step 6 Follow-up Management ←─ Step 5 Send
 add_success → review_success          convert→validate→preview   imap_scanner(DRY_RUN)          three checks → DRY_RUN
 weekly write-back → kit-check         →harness→send→audit        cooldown · 1-3-7-21            → user approval
 → back to Step 0                      200/day STOP               bounce/reply/won/no reply      → send inside local window
```

---

## 🔄 Detailed SOP (with decision logic)

### Step 0: Omni-channel Review (success cases + WA review + this week's kit conclusions; mandatory before every development run)

> v3.0: the weekly review also does the "kit write-back" — this week's mistakes are written back to the matching file (`references/soul_kit/weekly_writeback.md`), then run `onboarding.py kit-check`. Review conclusions go into `soul_seven_kit/MEMORY.md`, run data into `HEARTBEAT.md`.

**Input**: success_cases.csv  
**Output**: distilled success points + strategy reference for this round

**⚠️ Core principle: pain-point analysis only takes effect after the user confirms it; the AI gives preliminary suggestions, never the final verdict.**

```python
# pseudocode
review = csv_ops.review_success()

IF review.total_cases == 0:
    PRINT "No success cases yet, starting the development flow normally"
ELSE:
    # === pain-point confirmation status ===
    pending_cases = [c for c in review.cases if not c.confirmed]
    
    IF pending_cases:
        # unconfirmed pain points → must be fed back to the user first
        PRINT "⚠️ The pain-point analysis of these cases awaits your confirmation:"
        FOR case IN pending_cases:
            # the AI lists candidate pain points for the user to pick; it never decides on its own
            PRINT f"""
Brand: {case.brand}
Customer: {case.contact} ({case.region})
Preliminary analysis — probably one of these pain points:
  1. Compliance / credential requirement (customer mentioned certification / compliance) → compliance
  2. Needs faster delivery / go-live (customer mentioned urgent / deadline / go-live) → speed
  3. Needs a custom solution (customer mentioned custom / tailored / exclusive) → exclusive_custom
Which one is it? (reply with the number or add details)
"""
        # ⏸️ pause and wait for the user
        # only after confirmation → write the confirmed pain point into the success_points field of success_cases.csv
        # csv_ops.py add_success <email> <brand> <contact> <amount> "<confirmed_points>" --hook_type <solution_tag>
        WAIT_FOR_USER_CONFIRMATION()
    
    # === filter relevant cases by target market ===
    relevant = [c for c in review.cases if c.region == target_region AND c.confirmed]
    
    IF relevant:
        # confirmed cases in the same region → copy the play
        best_hook = most_common_hook(relevant)
        best_language = most_common_language(relevant)
        best_channel = most_common_channel(relevant)  # ⭐ most effective acquisition channel
        PRINT f"{len(relevant)} confirmed success cases in this region, most effective hook: {best_hook}"
        PRINT f"Most effective acquisition channel: {best_channel} ({count_by_channel(relevant, best_channel)} deals)"
    ELSE:
        # no same-region cases → use the global best (confirmed cases only)
        confirmed_cases = [c for c in review.cases if c.confirmed]
        IF confirmed_cases:
            best_hook = review.top_patterns[0]
            best_channel = review.by_source_channel[0]  # ⭐ globally most effective channel
            PRINT f"No same-region cases, global best hook: {best_hook}"
            PRINT f"Global most effective channel: {best_channel}"
        ELSE:
            PRINT "No confirmed success cases, starting with the generic strategy"
    
    # === distilled points must be applied to this round ===
    success_patterns = extract_patterns(confirmed_cases)
    FOR candidate in new_candidates:
        candidate.apply_lessons(success_patterns)
```

**Pain-point confirmation flow in detail**:

```
customer replies / orders → success event detected
    ↓
AI preliminary analysis of the pain point probably solved (3–5 candidates)
    ↓
fed back to the user for confirmation:
  "This customer replied; it is probably one of these pain points:
   1. Compliance / credential requirement (certification / compliance mentioned) → compliance
   2. Faster delivery / go-live (urgent / deadline / go-live mentioned) → speed
   3. Custom solution (custom / tailored / exclusive mentioned) → exclusive_custom
   Which one is it?"
    ↓
user confirms → formally written to success_cases.csv
    confirmed=true, success_points=the pain point confirmed by the user
    ↓
⚠️ not confirmed by the user → not written to success_cases.csv
    only the ai_analysis field is recorded, confirmed=false
    shown as ⏳ pending in the dashboard
```

**Commands**:
- The AI gives the pain-point analysis in the conversation first, **without writing to the DB**; after confirmation write it: `csv_ops.py add_success <email> <brand> <contact> <amount> "<pain point confirmed by the user>" [--hook_type <solution_tag>] [--won_channel email|wa]`
- List success cases: `csv_ops.py list_success [--region XX] [--need_tag XX] [--channel XX]`
- Review success cases: `csv_ops.py review_success`

---

### Step 1: Search Candidates (keyword matrix · 15 discovery channels · 10-platform social public search)

**Input**: target market + industry keywords  
**Output**: candidate list (JSON/CSV)

**Three discovery sources, one exit** (all generate public search queries only; no login, no registration):
- Keyword matrix: `search_customers.py queries`
- 15 discovery channels (customs / exhibitions / tenders / hiring / competitor reverse-lookup …): `search_customers.py channels`; the registration-free customs path is in `references/customs_data_guide.md`
- 10 social platforms public search + 30 procurement-chain titles: `search_customers.py social`, playbooks in `references/social_media_playbooks.md`
- Unified exit: results → `search_customers.py filter results.json --against <customer_db.csv>` (DB de-dup + funnel diagnosis + pending-verification pool)

```python
# pseudocode
candidates = []

for source in [Google, LinkedIn, exhibitor_lists, competitor_customers]:
    results = search(source, keywords, market)
    for brand in results:
        # IF already blacklisted → skip
        IF csv_ops.check(brand.email) == "blacklisted":
            CONTINUE
        
        # IF confirmed out of business → skip
        IF company_status == "closed":
            CONTINUE
        
        # IF pure C2C / individual seller → skip
        IF business_type == "C2C":
            CONTINUE
        
        # ⚠️ never exclude by company name / category name!
        # a company whose name looks irrelevant may have an undiscovered need
        
        candidates.append({
            "brand": brand.name,
            "website": brand.website,
            "email": brand.email,
            "region": brand.region,
            "contact_person": brand.contact_name,  # if any
            "title": brand.contact_title,          # if any
            "whatsapp": brand.wa_number            # if any
        })

# output candidate list
save(candidates, "candidates.json")
```

**Mandatory fields**:
- ✅ company name, website URL, country / region
- ✅ contact e-mail (priority: named person > functional mailbox such as purchasing@/partners@ > info@)
- ✅ WhatsApp number (if any)
- ✅ decision-maker name + title (if any; used later for e-mail guessing)

**Search keyword templates**:
- Generic: `{market} {product} {customer_type}` (customer_type from `targeting.channel_keywords`, e.g. distributor / contractor / startup / clinic chain)
- Industry-specific: see `references/industry_playbooks.md`
- Detailed channels and workflow: see `references/SOP_search_workflow.md`

---

### Step 2: Background Research (⭐ core, never skipped)

**Input**: candidate list  
**Output**: research conclusion + need_tag + solution_tag per account

```python
# pseudocode
for candidate in candidates:
    
    # === data-layer de-dup (done together with research) ===
    check_result = csv_ops.check(candidate.email)
    
    IF check_result == "blacklisted":
        SKIP  # blacklisted, not developed
    ELIF check_result == "in_cooldown":
        SKIP  # in cooldown, not now
    ELIF check_result == "wa_only":
        SKIP  # moved to the WA channel, no e-mail
    
    # IF cross-brand de-dup fails → skip
    IF csv_ops.cross_brand_check(candidate.domain) == "duplicate":
        SKIP
    
    # === start research (5 information sources) ===
    research = {}
    
    # 1. website home page
    research["homepage"] = fetch(candidate.website)
    research["brand_positioning"] = extract_positioning(research["homepage"])
    research["main_categories"] = extract_categories(research["homepage"])
    
    # 2. product / service / solution pages (scope gate first)
    research["products"] = fetch(candidate.website + "/products|/services|/solutions")
    research["categories"] = extract_target_categories(research["products"], profile.targeting)  # need_tag values = positioning.need_tags
    research["solution_fit"] = detect_solution_fit(research["products"], profile.product)  # relation of their current solution to our differentiators
    IF NOT is_within_targeting(research["main_categories"], research["categories"], profile.targeting):
        REJECT(candidate, reason="outside the profile's targeting scope (hit an adjacent irrelevant business configured at install)")
    
    # 3. buying / compliance pages (wholesale · vendor · partners · procurement · RFP · sustainability · compliance · careers)
    IF has_buying_or_policy_page(candidate.website):
        research["policy"] = fetch(candidate.website + "/sustainability|/compliance|/procurement")
        research["certifications"] = extract_certifications(research["policy"])  # certifications really used in your industry (listed at install)
        research["buying_signal"] = extract_buying_signal(candidate.website)  # vendor application / partner program / RFP / hiring
    ELSE:
        research["policy"] = None
    
    # 4. news / social media
    research["news"] = search_news(candidate.brand_name)
    research["recent_moves"] = extract_recent_strategy(research["news"])  # new product / expansion / funding / new project / hiring
    
    # === three research questions ===
    conclusion = {
        "Q1_what_they_sell": research["categories"] + [research["solution_fit"]],
        "Q2_channel_and_stance": research["buying_signal"] or "not stated",
        "Q3_what_they_might_need": derive_need(research)
    }
    
    # === set the two tags ===
    need_tag = determine_need_tag(conclusion)
    candidate["need_tag"] = need_tag
    candidate["solution_tag"] = determine_solution_tag(conclusion)   # 11 generic decision drivers, see industry_playbooks §1
    candidate["research_notes"] = conclusion
    
    # save the research conclusion
    csv_ops.add_note(candidate.email, f"research done: {need_tag}")
```

**need_tag rules**:

```python
def determine_need_tag(conclusion):
    cats = conclusion["Q1_what_they_sell"]      # values from positioning.need_tags: <line_a>/<line_b>
    
    # scope gate first: outside the profile's targeting → not entered
    IF not is_within_targeting(cats, profile.targeting):
        RETURN None  # already blocked during research
    
    # need_tag by main category (several possible)
    IF len(cats) >= 2:
        base = "multi"
    ELSE:
        base = cats[0] if cats else "unknown"
    RETURN base


def determine_solution_tag(conclusion):
    fit     = conclusion.get("solution_fit", "")   # relation of their current solution to our differentiators
    signals = conclusion.get("Q3_signals", [])     # research signals: certification page / price comparison / small team / deadline / new direction / custom...
    tags = []
    IF "compliance_page" in signals or "tender_requires_cert" in signals: tags.append("compliance")
    IF fit == "uses_lower_grade_alternative":     tags.append("quality_upgrade")
    IF "small_or_first_time" in signals:          tags.append("low_commitment")
    IF "deadline" in signals:                     tags.append("speed")
    IF "new_initiative" in signals:               tags.append("innovation")
    IF "wants_custom" in signals:                 tags.append("exclusive_custom")
    # keep only tags whose capability you really have in the profile (solution_capabilities.md §2)
    tags = [t for t in tags if capability_exists(t, profile)]
    RETURN "+".join(tags) or "unknown"
```

**Research tools**:
- `csv_ops.check <email>` — de-dup + blacklist + cooldown
- `csv_ops.cross_brand_check <domain>` — cross-brand de-dup
- `research_guide.md` — detailed research methodology

---

### Step 3: Need Positioning (need_tag → what to pitch; solution_tag → which hook)

**Input**: need_tag + solution_tag  
**Output**: recommended line + e-mail template choice

```python
# pseudocode
for candidate in candidates:
    need_tag = candidate["need_tag"]
    
    # === need_tag → which line (values and meaning from positioning.need_tags / product_knowledge.md §1) ===
    line_map = {
        "<line_a>": "lead with <offer-line-A>, stress <differentiator>",
        "<line_b>": "lead with <offer-line-B>",
        "multi":    "pitch the overall solution / multi-line combination (only when really available)",
        "unknown":  "conservative generic entry, confirm the need during follow-up",
    }
    # === solution_tag → e-mail template (email_templates.md §1, cross-industry) ===
    template_map = {
        "compliance": "1.1", "sustainability": "1.1",
        "quality_upgrade": "1.2", "exclusive_custom": "1.2",
        "low_commitment": "1.3", "cost": "1.3",
        "speed": "1.4", "innovation": "1.5", "one_stop": "1.5",
        "dedicated_service": "1.6", "strategic_scale": "1.6",
        "open": "1.7", "unknown": "1.7",
    }
    main_driver = candidate["solution_tag"].split("+")[0]
    candidate["product_strategy"] = line_map.get(need_tag, line_map["unknown"])
    candidate["template"] = template_map.get(main_driver, "1.7")
```

**Output**: `product_strategy` + `template` fixed for every account

---

### Step 4: Write Content (e-mail)

**Input**: candidate + product_strategy + template  
**Output**: personalised e-mail (subject + body)

```python
# ========== Step 4.0: product-fact confirmation (if/else decision logic) ==========
# product facts must be confirmed before any hook template is used

# ⭐ single source of truth: config/company_profile.json created at first install (see the Install Gate in SKILL.md)
profile = config.load_profile(require_complete=True)   # exits when the profile is incomplete; no sending with placeholders
# the knowledge base references/product_knowledge.md is the human-readable expansion of these fields, for wording material
product_info = {
    "keywords":       profile["product"]["primary_keywords"],      # core product / service terms (filled at install)
    "one_liner":      profile["product"]["one_liner_en"],           # one-line positioning
    "entry_offer":    profile["offer"]["entry_offer"],              # low-commitment entry: sample / trial / diagnosis / pilot …
    "key_facts":      config.offer_facts(profile),                  # real short facts (MOQ / go-live time / certification / lead time …)
    "cta":            config.cta_question(profile),                 # closing question
    "usp":            profile["product"]["differentiators"],        # verifiable differentiators
    "certifications": profile["product"].get("certifications", [])  # certificates really held, else empty
}
# keys never in the profile: SMTP/IMAP credentials only via environment variables SMTP_* / IMAP_*

IF profile missing or key fields empty:
    → stop and guide the user through first install (onboarding_questions.md); never invent product facts / contact details

# === Step 4.1: pick the template + fill in product facts ===
for candidate in candidates:
    
    # === pick the template ===
    template = load_template(candidate["template"])
    
    # === personalisation variables (from product_info) ===
    variables = {
        "brand_name": candidate["brand"],
        "contact_name": candidate.get("contact_person", "there"),
        "region": candidate["region"],
        "product": product_info["keywords"][0],  # lead product keyword
        "product_hook": get_product_hook(candidate["solution_tag"], product_info),
        "entry_offer": product_info["entry_offer"],   # no default: must be a real fact from the profile
        "key_facts": product_info["key_facts"],
        "cta": product_info["cta"],
        "usp": product_info.get("usp", ""),
        "website": candidate.get("website", "")
    }
    
    # === multilingual localisation ===
    # core principle: write the WHOLE e-mail in the recipient's native language, not just the greeting!
    language_map = {
        "IT": "italian",
        "DE": "german", 
        "FR": "french",
        "ES": "spanish",
        "JP": "japanese",
        "NL": "dutch",
        "PT": "portuguese"
    }
    
    IF candidate["region"] in language_map:
        language = language_map[candidate["region"]]
        # use the full native-language template (see email_templates.md)
        email_body = load_localized_template(language, variables)
    ELSE:
        # English by default
        email_body = f"Hi {variables['contact_name']},\n\n{template.format(**variables)}"
    
    # === subject ===
    subject = f"{variables['product']} for {variables['brand_name']}"   # or the template's subject skeleton
    
    # === compliance check ===
    IF len(email_body) > 120 words:
        WARN "e-mail too long, shorten it"
    
    IF any(word in subject.lower() for word in ["partnership", "collaboration", "free", "discount", "oem"]):
        ERROR "subject contains a banned word, replace it"
    
    IF any(word in email_body.lower() for word in ["competitive pricing", "partner", "oem", "factory direct"]):
        ERROR "body contains a banned word, replace it"
    
    # === output ===
    candidate["email_subject"] = subject
    candidate["email_body"] = email_body
```

**Banned words**:
- **Subject**: Partnership / Collaboration / Free / Discount / OEM / ODM
- **Body**: competitive pricing / partner / OEM / factory direct / world-class / guaranteed / any absolute promise that cannot be proven
- **Industry-specific banned words** (medical efficacy, food health claims, financial return promises, process terms in your category that are easily misread) go into `rules.notes` and `soul_seven_kit/SOUL.md` and are blocked by the same rule

**Template bank**: `references/email_templates.md`

---

### Step 5: Send

**Input**: candidates + e-mail content  
**Output**: sending records + data write-back

**Send by recipient-local time (enforced by the scripts)**: when a contact carries `region` (or `tz`), `batch_sender.py` / `decision_maker_sender.py` send only inside the recipient's local **working-day** window `rules.local_send_window` (default `09:00-11:00,14:00-16:00`); outside the window the contact is deferred for this run (reported as `deferred_window`, no sending history written).

| Market | Local window | How to convert to your local time |
|---|---|---|
| US East / Canada East | 09:00-11:00, 14:00-16:00 | `python3 scripts/send_window.py table --me <your tz>` real-time conversion (DST included) |
| UK / Ireland / Portugal | same | same |
| Continental Europe (DE/FR/IT/ES/NL …) | same | same |
| Middle East (UAE / Saudi Arabia) | same (mind the Friday / Saturday weekend; adjust with `SEND_WINDOW` when needed) | same |
| Australia / New Zealand | same | same |
| Japan / Korea / South-East Asia | same | same |

> No more hard-coded "send to country X at hour Y of your local time": daylight-saving time breaks a fixed offset table twice a year. The real-time output of `send_window.py table` is authoritative; `send_window.py check DE` tells whether a single market can be sent to right now.

```python
# === the three pre-send checks (none may be skipped) ===

for candidate in candidates:
    
    # ========== check 1: mailbox verification ==========
    
    # IF generic mailbox (info@/contact@ …) → block
    IF is_generic_email(candidate["email"]):
        # a generic mailbox does not map to a decision maker: this skill's rule is no cold e-mail to it (experience rule, not a statistic)
        # a named decision-maker mailbox is required
        IF candidate.get("contact_person"):
            # derive the named mailbox with the e-mail guesser
            guessed = email_guesser.guess(candidate["contact_person"], candidate["domain"])
            candidate["email"] = guessed
        ELSE:
            SKIP "no decision-maker info, find the person on LinkedIn first"
    
    # DNS/MX verification
    mx_valid = dns_validator.validate(candidate["email"])
    IF not mx_valid:
        SKIP "mailbox domain has no valid MX"
    
    # ========== check 2: de-dup ==========
    
    check_result = csv_ops.check(candidate["email"])
    
    IF check_result == "blacklisted":
        SKIP "blacklisted"
    ELIF check_result == "in_cooldown":
        SKIP "in cooldown"
    ELIF check_result == "wa_only":
        SKIP "moved to the WA channel"
    ELIF check_result == "duplicate":
        SKIP "duplicate send"
    
    # cross-brand de-dup
    IF csv_ops.cross_brand_check(candidate["domain"]) == "duplicate":
        SKIP "cross-brand duplicate"
    
    # ========== check 3: notes ==========
    
    notes = csv_ops.get_notes(candidate["email"])
    
    IF notes:
        # IF there are historical notes, adjust the strategy accordingly
        IF "customer said contact again in Q3" in notes:
            IF current_month < 7:  # Q3 = July–September
                SKIP "wait until Q3"
        IF "customer is price-sensitive" in notes:
            adjust_pricing_hook(candidate)
        IF "bounce reason: mailbox does not exist" in notes:
            SKIP "mailbox invalid"
    
    # IF research not done → do not send
    IF not candidate.get("need_tag"):
        SKIP "research not done"
    
    # IF content not compliant → do not send
    IF not is_compliant(candidate["email_body"]):
        SKIP "e-mail content not compliant"
    
    # === final confirmation ===
    IF len(candidate["email_body"]) > 120 words:
        ERROR "e-mail too long"
    IF same_day_sent_count(candidate["email"]) >= 1:
        SKIP "same customer already contacted today"
    
    # === start sending ===
    
    # mode A: manual sending (small batch)
    IF batch_size < 50:
        send_email_manual(candidate)
        csv_ops.add_sent(candidate["email"], candidate["brand"], candidate["subject"], candidate["need_tag"])
    
    # mode B: SMTP batch sending (large batch)
    ELSE:
        # named decision-maker sending (recommended)
        IF candidate.get("contact_person"):
            decision_maker_sender.send([candidate])
        ELSE:
            batch_sender.send([candidate])
        
        # sending iron rules:
        # - 30-second interval against spam filters
        # - daily limit 200 e-mails
        # - **send by recipient-local time** (local 9:00-11:00 or 14:00-16:00, see the window table above)
        # - never batch-send on the sender's time zone
    
    # === write back after sending, always ===
    csv_ops.add_sent(candidate["email"], candidate["brand"], candidate["subject"], candidate["need_tag"])
```

**⚠️ Sending-time iron rule**: every outreach e-mail follows the working hours of the recipient's country (local 9:00-11:00 or 14:00-16:00); never send on the sender's time zone. Use `python3 scripts/send_window.py table --me <your tz>` for the live conversion instead of a fixed offset table.

**Sending tools**:
- `dns_validator.py` — MX verification
- `email_guesser.py` — e-mail pattern guessing
- `decision_maker_sender.py` — named decision-maker sending (recommended)
- `batch_sender.py` — batch sending
- `send_window.py` — recipient-local window check

---

### Step 6: Follow-up Management

**Input**: list of contacted customers  
**Output**: follow-up e-mails + data updates

**Two cadences with separate roles, never stacked**: e-mail follows the 5-level cooldown below (computed by `csv_ops.py cooldown`); social DMs (manual) follow **1-3-7-21** (Day 1 ice-breaker → Day 3 value → Day 7 case → Day 21 switch channel), see `references/social_media_playbooks.md` section 6. One customer, one channel per day.

```python
# === daily ===

# 1. scan bounces / replies (IMAP, automatic)
imap_scanner.scan()  # updates the blacklist + marks bounced/replied

# 2. check cooldowns
for email in sent_history:
    record = csv_ops.check(email)
    
    IF record["status"] == "bounced":
        # bounce = permanent blacklist, no follow-up
        CONTINUE
    
    IF record["status"] == "replied":
        # reply received → manual follow-up
        NOTIFY "reply received, handle manually"
        CONTINUE
    
    IF record["status"] == "wa_only":
        # moved to WA → no e-mail
        CONTINUE
    
    # === cooldown decision ===
    followup_count = record["followup_count"]
    days_since_last = days_since(record["last_followup_date"])
    
    # 5-level progressive cooldown rules (authoritative: COOLDOWN_RULES / MAX_GENERIC_FOLLOWUP /
    # MAX_TOTAL_FOLLOWUP in csv_ops.py; followup_count starts at 0 = the latest e-mail is number N+1)
    # the real decision always calls: csv_ops.py cooldown <email>, reading the returned action / can_followup
    IF followup_count == 0:          # 1st e-mail sent
        cooldown_days = 3            # COOLDOWN_RULES[0]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="different_angle")
    ELIF followup_count == 1:        # 2nd e-mail sent
        cooldown_days = 3            # COOLDOWN_RULES[1]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="new_information")
    ELIF followup_count == 2:        # 3rd e-mail sent
        cooldown_days = 10           # COOLDOWN_RULES[2]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="last_attempt")
    ELIF followup_count == 3:        # 4 e-mails sent → action = stop_generic
        # stop generic mailboxes → LinkedIn / personal mailbox only
        IF has_linkedin(email):
            reach_via_linkedin(email)
    ELIF followup_count >= 4:        # 5+ e-mails sent → action = stop_all
        # e-mail stopped permanently → WA / personal mailbox only; record with csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact>
        IF has_whatsapp(email):
            reach_via_whatsapp(email)
    
    # === Follow-up content must differ ===
    IF sending_followup:
        IF content == previous_content:
            ERROR "follow-up content must be completely different"
        IF not has_new_information(content):
            ERROR "a follow-up must carry new information"
```

**Follow-up iron rules**:
- ✅ every follow-up carries new information (new case / new data / new version / new angle / industry news)
- ✅ completely different wording, never reuse earlier phrasing
- ✅ 4 e-mails without reply → LinkedIn / personal mailbox
- ✅ 5 e-mails without reply → WA
- ❌ no follow-up after a bounce (permanent blacklist)

---

### When a customer closes: collect the full customer file

**Trigger**: customer confirms the order / payment  
**Output**: complete customer background file

```python
# === after the deal, collect the full background ===

# 1. basic info (already known)
basic_info = {
    "email": contact.email,
    "brand": contact.brand,
    "contact": contact.contact_name,
    "region": contact.region,
    "order_amount": order.amount,
    "order_date": today,
    "source_channel": contact.source_channel  # which channel this customer came from
}

# 2. company background (research to complete)
company_info = {
    "company_name": "",  # full legal name
    "founded_year": "",  # year founded
    "company_size": "",  # headcount / annual revenue
    "main_business": "",  # main business
    "business_model": "",  # B2B / B2C / mixed
    "target_market": ""  # target market (who they sell to)
}

# 3. contact details (to complete)
contact_info = {
    "contact_phone": "",  # decision-maker phone
    "company_address": "",  # company address
    "whatsapp": "",  # WhatsApp number
    "wechat": "",  # WeChat (if any)
    "other_contact": ""  # other channels
}

# 4. social accounts (search to complete)
social_media = {
    "website": "",  # website
    "social_linkedin": "",  # LinkedIn company page / profile
    "social_instagram": "",  # Instagram
    "social_facebook": "",  # Facebook
    "social_twitter": "",  # Twitter/X
    "social_pinterest": "",  # Pinterest
    "social_youtube": "",  # YouTube
    "social_tiktok": ""  # TikTok
}

# 5. business info (research)
products_info = {
    "main_offerings": "",  # main products / services
    "size_or_budget": "",  # size / price band / budget signals
    "current_solution": "",  # current solution or supplier (relation to your differentiators)
    "positioning": "",  # positioning (premium / mid / mass; enterprise / SME)
    "key_categories": ""  # core business lines
}

# === how to collect ===
# way 1: collected during research (completed in Step 2)
IF research_complete:
    company_info = extract_from_research(research_data)
    social_media = extract_social_from_website(candidate.website)

# way 2: completed after the deal (customer provides it or further research)
IF customer_confirmed_order:
    # ask the customer
    ASK customer: "Could you share your website, address and WhatsApp for easier communication?"
    # or search
    social_media = search_social_media(brand_name)

# === write the success case ===
csv_ops.add_success(
    email=email,
    brand=brand,
    contact=contact_name,
    order_amount=amount,
    success_points=confirmed_pain_points,  # pain points confirmed by the user
    company_info=json.dumps(company_info),
    contact_phone=contact_phone,
    company_address=company_address,
    website=website,
    social_linkedin=social_linkedin,
    social_instagram=social_instagram,
    whatsapp=whatsapp,
    products_info=json.dumps(products_info),
    source_channel=source_channel,
    notes=notes
)
```

**What the customer file is for**:
1. **Review and learning**: common traits of won customers
2. **Second development**: other brands / contacts of the same company
3. **Referrals**: full background when a customer refers a new one
4. **Long-term follow-up**: knowing their background when sharing industry news, new versions / cases

> ⭐ **Always tag the winning channel at close**: `add_success` must carry `--won_channel email` or `--won_channel wa`. It is the only basis for the WA review (Step 7 below) to tell "won by e-mail" from "won by WA"; without it the WA contribution cannot be computed.

---

### Step 7: WhatsApp Trigger + bulk send + dedicated review (closing the e-mail chain, self-looping) ⭐

**Role**: the e-mail chain does "broadcast reach", the WA chain "closes the hard accounts that never replied to e-mail"; both share one customer table, forming a loop. Full methodology in `references/wa_bulk_guide.md` (7.2 template bank / 7.3 trigger chain / 15 review loop).

```python
# === WA trigger: any signal hit in the dashboard → WA list ===
FOR record IN dashboard:
    IF (record.followup_count >= 2 AND record.status != "replied")   # ① several e-mail rounds, no reply
       OR record.status == "bounced"                                 # ② bounced / invalid mailbox
       OR (record.high_value AND record.public_wa)                   # ③ high value + public WA
       OR record.wa_from_expo:                                       # ④ trade show / number given voluntarily
        SUGGEST add_to_wa_targets(record)     # suggestion only, you decide (meta-need 2); weak signal → need_review

# === trigger chain (five steps) ===
# ① export the WA list: email_dashboard.py filter pending / no reply → wa_targets.json
# ② apply templates:   7.2 WA versions of the 7 hooks, {intro} generated per account (anti-ban core) → Format B contacts.json
# ③ bulk send:         wa_bulk_sender.py validate → preview → send (screenshot verification per message, 200/day anti-ban)
# ④ write back:        csv_ops.py mark_wa_only; customer replies → wa_contacts.csv status → replied
# ⑤ review:            wa_review.py review --html --compare-email (read-only, 14 iron rules)

# === self-loop: the review feeds the next trigger round ===
review = wa_review.review()
#   which region / hook_type / need_tag wins most on WA → weight the next WA list towards it
#   wa_review --compare-email tells you: e-mail vs WA, which channel deserves more budget
```

**WA loop iron rules**:
- ✅ a trigger hit is only a "suggestion to list"; whether / how many / who first is your call (meta-need 2)
- ✅ a different `{intro}` per person (anti-ban core); the outreach number only; no wa.me in the body
- ✅ wins must carry `--won_channel wa`, otherwise the review is wrong
- ✅ wa_review is read-only on customer data (per the 14 iron rules); conclusions are advisory
- ❌ never bypass the 4 trigger signals and bulk-send "because we feel like WA"

---

### Step 8: Win Review + Kit Write-back (closing the loop · weekly)

**Input**: won customers (e-mail or WA), this week's send / bounce / reply data, this week's AI mistakes
**Output**: success cases stored, omni-channel attribution, kit rules updated → the starting point of the next Step 0

```python
# 1. store the win: the AI gives evidence-backed pain-point candidates only; written after user confirmation (see "When a customer closes" above)
csv_ops.add_success(..., won_channel="email" | "wa")
# 2. omni-channel review (read-only)
csv_ops.review_success()                 # by region / need_tag / hook_type
email_dashboard.py                       # e-mail funnel + success-case module
wa_review.py review --compare-email      # e-mail vs WA, which channel wins more
# 3. weekly kit write-back (references/soul_kit/weekly_writeback.md)
#    wrong answer / missed step / overreach → attributed to exactly one file → change the rule (not just the sentence) → update HEARTBEAT
onboarding.py kit-check                  # must be 7/7; after editing a file, read back, confirm → attest
# 4. conclusions into soul_seven_kit/MEMORY.md "This week's conclusions" → back to Step 0 for the next round
```

---

## 📊 Daily / weekly routines

### Daily (sending time decided by the recipient's local window; run send_window.py table first to see which markets are open)

```python
# 1. batch sending (daily target default 100, hard limit 200; the script skips recipients outside their local window and retries next run)
batch_sender.send(max_count=100)

# 2. IMAP bounce scan (24–48 hours later)
imap_scanner.scan()

# 3. refresh the dashboard
email_dashboard.generate(sent_history, blacklist)

# 4. check cooldowns + send follow-ups
followup_manager.check_and_send()

# 5. ⭐ daily report (mandatory after the task)
# generate the tracking dashboard + distil 3–5 points, report the day's results to the user
daily_report()
```

**Daily report flow**:

```python
def daily_report():
    """after the task: generate the dashboard + distil 3–5 points"""
    
    # 1. today's tracking dashboard
    dashboard = email_dashboard.generate(sent_history, blacklist, title="Daily sending tracker")
    
    # 2. today's numbers
    today_data = {
        "sent_count": count_sent_today(),
        "bounced_count": count_bounced_today(),
        "replied_count": count_replied_today(),
        "blacklist_added": count_new_blacklist_today(),
        "pipeline_ready": csv_ops.pipeline_check()["ready_count"]
    }
    
    # 3. distil 3–5 key points
    key_points = []
    key_points.append(f"Sent today: {today_data['sent_count']}")
    
    IF today_data['bounced_count'] > 0:
        key_points.append(f"Bounces: {today_data['bounced_count']} (blacklisted automatically)")
    
    IF today_data['replied_count'] > 0:
        key_points.append(f"Replies: {today_data['replied_count']} (manual follow-up needed)")
    
    # business insights from success cases / research
    insights = extract_daily_insights(today_data)
    FOR insight IN insights[:2]:  # at most 2 business insights
        key_points.append(insight)
    
    IF today_data['pipeline_ready'] < 100:
        key_points.append(f"⚠️ Reserve pool low: {today_data['pipeline_ready']} accounts, replenish")
    
    # 4. report to the user
    REPORT_TO_USER(
        dashboard=dashboard,
        summary="📊 Today's customer development report",
        key_points=key_points[:5]  # 3–5 points
    )
```

### Weekly

```python
# 1. review success cases (check pending pain points)
csv_ops.review_success()

# 1.5 ⭐ Soul Seven Kit weekly write-back (references/soul_kit/weekly_writeback.md)
#     wrong answer / missed step / overreach → attributed to one file → change the rule → update HEARTBEAT → onboarding.py kit-check

# 2. tracking dashboard (with the success-case review module)
email_dashboard.generate(weekly_data)

# 3. blacklist review + stale-data cleanup
blacklist_review()

# 4. ⭐ reserve pool check (Sunday / Monday)
pipeline_status = csv_ops.pipeline_check()
IF pipeline_status["ready_count"] < 100:  # minimum 100 accounts (7-day reserve)
    shortage = 100 - pipeline_status["ready_count"]
    PRINT f"⚠️ Reserve pool low! {pipeline_status['ready_count']} accounts, {shortage} needed"
    # start the replenish task: search + research + need positioning
    create_supplement_task(count=shortage)
```

### ⭐ Reserve pool management

**Minimum reserve**: 100 accounts (7-day reserve); recommended 300–500 (monthly reserve)

**Check frequency**:
- Sunday 22:00 — full reserve pool check
- before each daily send — confirm enough sendable accounts
- below 50% of the reserve — replenish immediately

**Reserve pool commands**:
```bash
# reserve pool status
python3 scripts/csv_ops.py pipeline_check

# add to the reserve pool (research done)
python3 scripts/csv_ops.py add_pipeline <email> <brand> <region> <need_tag> [priority]

# list the reserve pool
python3 scripts/csv_ops.py list_pipeline [--status ready] [--region US]

# take from the reserve pool for sending
python3 scripts/csv_ops.py use_pipeline <email>
```

**Reserve pool and sending together**:
```
reserve pool (100) → daily sending consumes (100/day) → reserve drops to 0 → replenish task starts
     ↑                                                                      ↓
     └──────────────────────── replenish done ──────────────────────────────┘
```

---

## 🚫 Absolute prohibitions (the 14 iron rules)

1. **Company / brand name never decides the need; research does** — no coarse filtering
2. **Never pitch what the customer clearly cannot use** — solution_tag=compliance customers only get lines with the matching credentials; forbidden combinations in `positioning.tag_rules` are never sent
3. **WA-only customers never get e-mail** — wa_only status blocks e-mail
4. **Check the data layer + do research before sending** — sending without checking = violation
5. **Write the data layer after sending** — sending without writing = data gap
6. **Never judge the customer's size for them** — show capability, no subjective judgement
7. **Payment reminders are never sent automatically** — manual confirmation required
8. **Never contact across brands twice** — one owner with several brands is contacted once
9. **"Pause / stop / no more" = stop everything immediately** — user instructions prevail
10. **CSV operations only through csv_ops.py** — no manual editing
11. **Deleting skills / files needs the boss's consent** — never delete on your own
12. **Generic mailboxes (info@/contact@ …) never get cold e-mail** — they map to no decision maker and cold e-mail there is usually not followed up (this skill's experience rule, not a statistic)
13. **Bounce = permanent blacklist, never retry** — bounced = never contacted again
14. **Plain text, no tracking pixel, with an unsubscribe route** — this skill quotes no unsourced "inbox rate" numbers; the verifiable hard requirements are Google's sender guidelines: every sender needs at least SPF or DKIM and a spam rate below 0.3%; bulk senders of about 5,000+ e-mails a day to Gmail need SPF+DKIM+DMARC and one-click unsubscribe for marketing mail ([Google sender guidelines](https://support.google.com/mail/answer/81126?hl=en)). The scripts add the `List-Unsubscribe` header and a body unsubscribe line automatically, see `references/mail_setup.md`

---

## 🛠️ Tool quick reference

| Step | Tool | Command |
|------|------|------|
| de-dup + blacklist | csv_ops.py | `check <email>` |
| cross-brand de-dup | csv_ops.py | `cross_brand_check <domain>` |
| record a send | csv_ops.py | `add_sent <email> <brand> <subject> <need_tag>` |
| add a note | csv_ops.py | `add_note <email> <note>` |
| mark bounce | csv_ops.py | `mark_bounced <email>` |
| mark reply | csv_ops.py | `mark_replied <email>` |
| move to WA | csv_ops.py | `mark_wa_only <email> <wa> <brand> <name>` |
| ⭐ WA review | wa_review.py | `review [--html out.html] [--compare-email]` / `funnel` (read-only) |
| ⭐ WA trigger | methodology | 4 dashboard signals → WA list (wa_bulk_guide 7.3) |
| cooldown query | csv_ops.py | `cooldown <email>` |
| statistics | csv_ops.py | `stats` |
| add success case | csv_ops.py | `add_success <email> <brand> <contact> <amount> <success_points> [--won_channel email\|wa --region --need_tag --hook_type --whatsapp --website ...]` |
| list success cases | csv_ops.py | `list_success [--region XX] [--need_tag XX] [--channel XX]` |
| review success cases | csv_ops.py | `review_success` |
| MX verification | dns_validator.py | `<input.json> [output.json]` |
| e-mail guessing | email_guesser.py | `<input.json> [output.json]` |
| decision-maker sending | decision_maker_sender.py | `<contacts.json> [report_dir]` |
| batch sending | batch_sender.py | `[max] [input.json] [report_dir]` |
| IMAP scan | imap_scanner.py | `[max_scan]` |
| tracking dashboard | email_dashboard.py | `<data.json> [output.html] [title]` |

---

## 📚 Reference documents

- `references/product_knowledge.md` — ⭐ your own product / service knowledge base template (the fact source to read before every development run once filled)
- `references/research_guide.md` — detailed research methodology
- `references/email_templates.md` — e-mail template bank (placeholder templates by need_tag / solution_tag; replace placeholders with profile facts before sending)
- `references/industry_playbooks.md` — generic B2B playbook (7 hook types + 8 regional strategies + product-fact confirmation flow)
- `references/SOP_search_workflow.md` — detailed customer search SOP, 15 methods
- `references/csv_guide.md` — CSV fields and script parameters
- `references/dashboard_guide.md` — dashboard guide

---

**SOP version**: v3.1  
**Last updated**: 2026-10-19  
**Changes**: three-check Install Gate (kit-check + content fingerprint), three discovery sources in Step 1 (incl. 10-platform social public search), S1/S2/S3 evidence tiers, recipient-local sending window, 1-3-7-21 and 3/3/10 separation, Step 8 weekly kit write-back; v3.1 adds the Data Access Layer (data_import / mail_setup / crm_sync), Data Triggers (triggers) and four-axis rotation replenishment (see CHANGELOG v3.1)  
**Maintainer**: B2B customer development AI co-pilot
