# CHANGELOG

## v3.2 — decision chain, complaint hooks, purchase timing

- Step 2 Research (`references/research_guide.md` §5.6): key accounts get a three-role decision chain (decider / handler / influencer; unknown roles are "not obtained", never invented); end-customer complaints grouped into pain-point hook candidates, used only after the user confirms; purchase timing inferred from the median interval of customs records — first e-mail 4–6 weeks before the window, no unsourced "cycle ratio".
- New `scripts/customs_summary.py` (10 self-tests, standard library only, same logic as the customer-background-investigation skill): shipment count, last shipment, monthly TEU, scale tier, origin and supplier shares, median interval, inferred next window, import-stoppage / single-supplier / new-category / small-sample signals. `references/customs_data_guide.md` §2.5 shows how to run it.
- Step 4 Writing: case studies, ROI and percentages only from user-confirmed `success_cases`.
- Red Flags and Verification updated accordingly; SKILL.md states that post-inquiry risk vetting belongs to the separate customer-background-investigation skill.
- New one-page Chinese path diagram `references/assets/auto_dev_path_zh.png`. SOP flowchart nodes unchanged.

## v3.1 — four-axis rotation + Data Access Layer + Data Triggers

### Four-axis rotation (Height / Breadth / Depth / Reach)
- `search_customers.py replenish` now rotates on four axes: Depth d1 companies → d2 decision makers → d3 deep-mining the existing pool (turns fastest); Reach regions near to far; Height customer tier high to low; Breadth core → wide → max (turns slowest). Old state files migrate automatically. d3 seeds come from success cases, reference brands and sent-but-unanswered accounts; with no seeds it falls back to d2 and says so.
- `--pool` defaults to `$B2B_DATA_DIR/customer_db.csv`; the sendable count excludes existing customers / do-not-contact / already-sent addresses.

### Data Access Layer (set up right after install)
- Profile gains a `data_sources` section; `data_sources.customer_db` is now required at install (imported / crm_sync / none); the skill ships no customer database.
- New `scripts/data_import.py`: own customer DB and trade-SaaS / customs / CRM Excel/CSV exports imported into one `customer_db.csv` (inspect / import / stats / fields; English and Chinese column names recognised automatically; do-not-contact synced into the blacklist).
- New `scripts/mail_setup.py` and `references/mail_setup.md`: presets for Tencent / Alibaba / NetEase enterprise mail, Gmail and Microsoft 365 (every line with its official source); client keys only in environment variables; hosted multi-mailbox + warm-up ramp (tiers are adjustable defaults) + automatic pause when the bounce rate passes the threshold; `mcp-export` / `mcp-writeback` for drafting through MCP connectors.
- New `scripts/crm_sync.py`: export HubSpot / Salesforce / OKKI / Fumeng / generic CSV; `pull` reads back; `push-hubspot` is dry-run by default, a real push requires `CRM_PUSH=1` + `HUBSPOT_TOKEN` and the Install Gate; `mcp-payload` for CRM MCPs.
- New `references/saas_integration_guide.md`: integration paths for trade SaaS and the verified official APIs/MCPs; vendor-reported numbers carry their source.

### Data Triggers
- New `scripts/triggers.py` and `references/data_access_and_triggers.md`: pool low / new import file / follow-up due / new reply / bounce spike / WA lead / warm-up step / mailbox paused / CRM sync due / weekly review → `reports/trigger_queue.json`; the only automatic action is pausing a mailbox on a bounce spike, every other outbound action needs human sign-off.

### Sending compliance
- `batch_sender.py` / `decision_maker_sender.py` add a `List-Unsubscribe` header and an opt-out line to every e-mail (`rules.opt_out_line`, "off" disables).

### Unsourced numbers removed
- Removed claims such as "plain-text inbox rate 60–70%" and "bounce rate 99.5%" that had no source; replaced with the key points of Google's sender guidelines with a link; LinkedIn metrics are labelled as internal thresholds.

### Encoding compatibility (no garbled text on Chinese Windows)
- Every script forces stdout/stderr to UTF-8 at start-up (no errors or garbled text when redirected to a file or on a GBK console).
- All CSV reads accept files with or without a BOM; CSV writes include a BOM (UTF-8-SIG) so Excel opens non-ASCII text correctly. JSON / Markdown reads accept a BOM; writes stay BOM-free.

### Flowchart and audit
- Flowchart v3.1: a new "② Data Access Layer" band under the gate; the self-replenishing engine becomes the four-axis rotation.
- `consistency_audit.py` gains section O (Data Access Layer and four-axis rotation) and parses the sub-commands and arguments of the 4 new scripts.

### English edition
- All scripts, documents, flowchart labels and training materials are in English. The Chinese edition ships in the same repository under `zh/` (and on the `zh` branch / `v3.1-zh` tag). Chinese column aliases are kept in `data_import.py`, `crm_sync.py` (OKKI / Fumeng CSV columns) and `wa_bulk_sender.py` on purpose so Chinese-language spreadsheets still import. Chinese filenames were renamed (e.g. `SOP_search_workflow.md`, `self_replenishing_engine.md`, `soul_kit/weekly_writeback.md`). SKILL.md gains a "Record schema" section (where every CSV / JSON state file lives and its fields).

## v3.0 — merged edition: Install Gate + 10 social platforms + evidence grading + full-loop flowchart

Merged the Soul Seven Kit, the "10 overseas social platforms" prospecting method and reviewer suggestions into the universal edition; a new installer knows immediately what to fill in, and every stage of the loop has an exit and a return path.

### Install Gate (first thing after installing)
- New `onboarding.py start`: one screen listing "what to fill in right after installing" — check 1 required profile fields, check 2 Soul Seven Kit, check 3 confirmation by the user, plus recommended items (target markets, competitors, key_facts, sending window, social platforms, SMTP environment variables) and the next command (read-only).
- New `onboarding.py kit-check`: content health check of the seven files (rules from soul-seven-kit) — missing file / empty shell (<3 real lines) / unreplaced "(e.g. …)" examples / missing key section (3 keywords per file) / leftover placeholders. `check`, `attest` and the gate in every business script now use the health-check result; flipping `filled` to true no longer passes.
- **Changes after confirmation invalidate it automatically**: `attest` records a content fingerprint of profile + kit (`confirmed_fingerprint`); any later change makes `check` return `CHANGED_AFTER_CONFIRM`, business scripts refuse to run, and the content must be read back and confirmed again.
- New `references/soul_kit/fill_reference_customer_dev.md` (method-level wording for the customer-development role; company facts come from the user) and `references/soul_kit/weekly_writeback.md` (write each mistake back into the file where it belongs).

### Acquisition channels
- New `search_customers.py social`: **login-free public search query** generator for 10 overseas social platforms (LinkedIn / Instagram / Facebook / YouTube / TikTok / Pinterest / X / Threads / WhatsApp / Lemon8) — outputs only site: queries usable in Google / Bing; actions that need registration/login (connection requests, DMs, joining groups, viewing follower lists) are marked "manual · login required" and never executed by the script. Supports `--platforms` / `--all` / `--tier decision|execution|influence|all` / `--titles` / `--urls` / `--out`; profile gains `search.social_platforms` (empty = all).
- New 30-title procurement-chain vocabulary (decision / execution / influence tiers, 10 each); the profile's `targeting.buyer_titles` come first.
- Instagram 9 hashtag groups, public competitor @-relationship mining (instead of login-only follower lists), the Facebook five-step group method, the three-sentence DM, cross-platform coordination: `references/social_media_playbooks.md`.
- New `references/customs_data_guide.md`: HS code → country-level market choice → company-level importers → decision makers, no-registration path first; `channels --ch customs` adds a `site:importyeti.com` query.
- New 13th industry pack `packaging_materials` (packaging materials / containers; reviewer-suggested "glass packaging" belongs here).

### Research and follow-up
- New evidence grades S1 / S2 / S3 (`research_guide.md` §5.5): ≥1 S1 or 2 independent S2 before setting a tag; S3 only → need_review for the user to decide; e-mails quote S1/S2 facts only.
- New `scripts/send_window.py`: decides whether sending is allowed by the recipient's local time (zoneinfo computes daylight saving live; no weekends). `batch_sender.py` / `decision_maker_sender.py` enforce `rules.local_send_window` for contacts with `region`/`tz` (default now `09:00-11:00,14:00-16:00`); outside the window the contact is deferred, recorded in `deferred_window`, and not written to send history; the DRY_RUN report flags the window status of every e-mail. `SEND_WINDOW` overrides the window, `SEND_WINDOW_ENFORCE=0` disables it. The profile already had this field but no script enforced it.
- Social DM rhythm 1-3-7-21 and the 5-level e-mail cooldown (3 / 3 / 10 days) are clearly separated; one channel per customer per day.

### Safety (Skill-Self-Check findings)
- `imap_scanner.py`: new `DRY_RUN=1` (lists detected bounces only, writes nothing); mailbox opened read-only (`readonly=True`).
- `dns_validator.py`: new `DRY_RUN=1` (lists the domains to be queried, no network requests).
- `wa_bulk_guide.md`: two wrong `../csv_ops.py` paths fixed to `scripts/csv_ops.py`.
- SKILL.md: description rewritten in "Use when…" trigger style with extra trigger words; new Role contract (`references/role-contract.json`, single_context / single_role) and a Workflow-prompt not-applicable statement; the manual review record of the three PowerShell sending paths is in `references/ship_safety_review.md`.

### Final close-out (de-identification · version · flowchart consistency)
- Final de-identification review: all e-mails use `.example` reserved domains; the German example company is Musterfirma GmbH, example numbers are obviously fictional; CHANGELOG history no longer describes the original industry; the flowchart PDF metadata title is the flowchart name.
- Version unified to v3.0: SOP.md and SOP_search_workflow.md headers/footers, and the file headers of search_customers.py / csv_ops.py / email_dashboard.py drop their old module versions (v2.0 / v4.0 / v5.0 / v5.1) in favour of the skill version v3.0; "12 channels" corrected to the actual 15 methods.
- The nine step names are identical in the flowchart, SKILL.md, SOP.md and sop_flowchart.md: Step 0 Omni-channel Review · Step 1 Search Candidates · Step 2 Background Research · Step 3 Need Positioning · Step 4 Write Content · Step 5 Send · Step 6 Follow-up Management · Step 7 WhatsApp Trigger · Step 8 Win Review + Kit Write-back. SOP.md gains the missing Step 8 chapter; the overview diagram goes from steps 0–6 to 0–8.
- Cooldown wording corrected: flowchart and SKILL.md said "3 e-mails stop generic mailboxes / ≥4 stop all", which disagreed with the scripts; unified on `followup_count` (= e-mails sent − 1): after 4 e-mails stop generic mailboxes, after 5 or more stop e-mail entirely. The WA trigger signal became "≥3 e-mails sent, no reply".
- WhatsApp anti-ban pacing is now executed by the script: `send` waits a random 8–15 s between messages and cools down 30–60 s every 5 messages (`wa_pacing.json`); previously this was documentation only.
- `decision_maker_sender.py` daily cap aligned with `batch_sender.py`: `DAILY_LIMIT` > profile `rules.daily_limit` > 200.
- New `references/assets/sop_flowchart.json` (machine-readable flowchart spec) and `consistency_audit.py` section N "flowchart consistency": step names identical in four places, node commands really exist, 13 key numbers equal the script constants (channel count, platform count, title count, replenish red lines, funnel thresholds, cooldown days, stop counts, daily cap, send interval, WA pacing and cap).

### Flowchart
- Redrawn `references/assets/sop_flowchart.png/.pdf` (v3.0): Install Gate three checks on top, self-replenishing engine, three discovery sources, Three Iron Rules of Search, evidence-grade branch, local-window deferral loop, four-branch follow-up, WhatsApp sub-flow, win review + weekly kit write-back → back to Step 0.
- `references/sop_flowchart.md` gains section 4 "loop checklist": the normal exit and the exception/loop path of every node.

## v2.2 — script/documentation terminology audit

- New `scripts/consistency_audit.py` (read-only, standard library, `--json`, exit code 1 on FAIL): checks CLI sub-commands and arguments, profile field paths, the 11 solution_tags, legacy tag leftovers, discovery channels, industry packs, file references, environment variables, CSV headers, counts and version, cooldown rules, status values.
- CLI documentation fixes: removed the non-existent `csv_ops.py confirm_success` and `list_success --pending` (success pain points are written only via `add_success` after user confirmation); `schedule --time` → `--at`; `preview/validate --dry-run` → `preview` (read-only by itself); `queries --limit` → `queries --regions <country> | head -20`.
- Implemented the documented but missing `wa_bulk_sender.py convert <csv|xlsx|wa_targets.json> [out.json]` (CSV zero-dependency; xlsx needs optional openpyxl; converts only, never sends).
- WhatsApp environment variables unified: Python reads `WA_MESSAGE_DIR` (legacy `WA_MSG_DIR` accepted) and `WA_PROGRESS_FILE`, same as PowerShell.
- Implemented the documented but unenforced WhatsApp daily cap: `wa_daily_count.json` counter, `WA_DAILY_LIMIT` (default 200, can only be lowered); at the cap `send` returns STOP (exit code 3).
- `validate` now checks for unfilled placeholders (same rule as e-mail sending).
- Cooldown: SOP pseudocode aligned with `COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}`; the csv_guide FAQ "cooldown_rules default 14 days" corrected; the non-stored `cooldown` status removed from the status values.
- Fields: fb_strategy `targeting.regions` → `targeting.target_regions`; search_customers no longer reads the undefined `targeting.competitor_brands`.
- Data template headers match the csv_ops fields exactly; success_cases / pipeline templates added; the unused sent_history_updated.csv removed; industry pack field order unified.

## v2.1 — industry-leftover audit

File-by-file, script-by-script review including the flowchart PNG/PDF, removing traces of the original industry left over from v2.0:
- **Flowchart**: step 3 "set need_tag + variant_tag → product-line strategy" became "set need_tag + solution_tag → which line to pitch · which hook" (PNG and PDF).
- **Win-review pain-point examples** (two places in SOP.md): "eco materials / exclusive design" became "compliance credentials / faster delivery and launch / custom solution", each with its solution_tag.
- **csv_guide need_tag enum**: removed the legacy compliance-only / prefer / regulated examples; now custom product lines + multi/review/unknown.
- **Research information table**: materials "material/process" and style became main products/services, size/budget, current solution, positioning.
- **Generic mailbox detection**: three per-script, wholesale-leaning prefix lists unified into `config.GENERIC_MAILBOX_PREFIXES`, adding cross-industry functional mailboxes such as partners / procurement / projects / tenders / hr / careers / billing / legal.
- **Gift channel**: now requires explicit `--ch gift`; no longer a default channel for physical goods.
- **Competitor field**: `has_own_factory` became the generic `is_competitor` (old field still accepted).
- **Wording examples**: LinkedIn range/brands/sample/MOQ and factory visits, Facebook group terms, wholesale/shop store/sourcing in SOP queries, the "veteran exporter" and "MOQ, lead time" iron rules in SOUL.md — all made industry-neutral, with boolean and search examples added for software / services / projects.
- **Terminology**: "order amount" → "deal amount"; "inventory legacy tags" → "in-DB legacy tags".
- New note: directory / tender / review pages are lead-source pages and never enter the pool as customers.

## v2.0 — universal edition

Built on the v1.1 de-identified template, removing the remaining original-industry bias and wording so the structure works for any B2B industry.

### Added
- **Industry packs** `references/industry_packs.json`: 12 (physical goods export, industrial, brand distribution, SaaS, professional services, logistics, medical/lab, food/agriculture, building/engineering, new energy, training/education, custom). Method-level suggestions only (tiers, roles, channels, intent terms, signals, compliance notes); no company facts.
- `onboarding.py packs | pack <id> | apply-pack <id>`: writes only still-empty method-level fields and resets `user_confirmed` to false.
- New profile sections: `business` (industry, offer_type, industry pack), `offer` (entry_offer / cta_question / key_facts / proof_points / repeat_hook), `positioning` (custom need_tags, conflict groups, in-DB rules, hook overrides), `targeting.customer_industries`, `search.query_anchor`.
- New required fields `business.industry`, `business.offer_type`.
- **Placeholder gate**: a profile with leftover `<...>` / `{...}` cannot be attested; outbound e-mail with leftover placeholders is blocked, not sent.
- **Customer-anchor search**: software / service businesses generate queries by the customer's industry to avoid finding peers.
- 6 new discovery channels: tender, hiring signals, directory / association, review sites, partners / ecosystem, events (15 in total); default channels chosen by offer_type.
- `references/industry_adaptation_guide.md`: three-step adoption, terminology map, 4 industry examples.
- `examples/profiles/`: 3 fictional demo profiles (industrial parts / HR SaaS / SEO consultancy); cannot be activated directly.

### Changed
- Decision-driver tag `solution_tag` unified to 11 cross-industry values; legacy tags (eco_only / traditional / low_moq / seasonal etc.) mapped automatically; historical data needs no change.
- `need_tag` is now the user's own product / service lines; `conflict-check` has no built-in industry rules and reads `positioning.conflict_groups` / `tag_rules`.
- E-mail and WhatsApp fact lines and closing questions read `offer.*` (legacy `product.moq` / sampling cycle still accepted); the hard-coded "Worth sending you a sample?" and "new collection / lookbook" removed.
- Rewrote `industry_playbooks.md`, `email_templates.md`, `product_knowledge.md`, `solution_capabilities.md`; research, search, SOP, LinkedIn, Facebook and WhatsApp documents lose the original-industry examples and the industry-specific L1–L6 customer spectrum.
- `search_customers.py`: removed duplicated conflict-correction / funnel / schedule / argument-parsing blocks (the old file had two copies, the later one overriding the first).

### De-identification
- Re-checked: no real company names, people, e-mails, phones, domains or customer data; demo data uses `.example` domains and fictional names throughout.
