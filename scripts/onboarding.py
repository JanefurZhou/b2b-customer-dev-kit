#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
onboarding.py — first-time onboarding tool for the industry-agnostic B2B customer development skill

Sub-commands
------
  start       New-install checklist: one screen of "what to fill right after installing" with the current status of each item (read-only)
  init        Create a blank config/company_profile.json + soul_seven_kit/ (never overwrites existing files)
  check       Validate required profile fields + Soul Seven Kit content check + user attestation; reports the three gates one by one
  kit-check   Soul Seven Kit content check only (missing file / empty shell / untouched example / missing key section / placeholder)
  ask         Interactive interview: asks for each required field and writes it (can also fill only the missing ones)
  attest      Activate the profile after the user explicitly confirms it (configured=true)
  packs       List built-in industry packs (method-level hints: tiers / roles / channels / intent terms)
  pack <id>   Show all hints of one industry pack
  apply-pack <id>  Write the pack's hints into method-level profile fields that are STILL EMPTY (never touches company facts),
                   and reset user_confirmed to false so the profile must be read back and confirmed again

Important: this script only builds and validates the profile. It never invents company information —
every field must be supplied by the user. When the AI loads this skill for the first time it should
walk the user through this profile as described in the "Install gate" section at the top of SKILL.md;
until check passes, every search / send / replenish script is rejected by config.py.

Standard library only, no third-party dependencies.
"""

import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import datetime

try:
    import config as _cfg
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import config as _cfg

# ---- Soul Seven Kit: template directory → first-time instance directory ----
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_TEMPLATE_DIR = os.path.join(_SKILL_ROOT, "references", "soul_kit")
KIT_INSTANCE_DIR = os.path.join(_SKILL_ROOT, "soul_seven_kit")
KIT_FILES = ["IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md",
             "MEMORY.md", "USER.md", "HEARTBEAT.md"]


def blank_profile():
    """Blank profile template: every business field is empty and is filled by the user the first time."""
    return {
        "schema_version": 1,
        "configured": False,
        "user_confirmed": False,
        "confirmed_at": "",
        "filled_at": "",
        "business": {
            "industry": "",             # required: one-line industry / niche, e.g. "industrial valves export" / "HR SaaS"
            "offer_type": "",           # required: physical_product / software / service / project / other
            "industry_pack": "",        # optional: pack id from references/industry_packs.json
            "sales_motion": "",         # optional: export / domestic / both
            "deal_size": "",            # optional: typical deal size (facts only)
            "sales_cycle": ""           # optional: typical sales cycle
        },
        "company": {
            "brand_display": "",        # company / brand name used in the e-mail signature
            "legal_entity": "",         # optional: legal company name
            "website": "",              # optional: main website
            "product_site": "",         # optional: product site (if different from the main site)
            "headquarters_country": ""  # optional: country of the company
        },
        "contact": {
            "founder_name": "",         # external contact person name (required)
            "founder_title": "",        # optional: title
            "email": "",                # sending mailbox (required)
            "whatsapp": "",             # optional: WhatsApp in international format
            "signature_lines": []       # optional: extra signature lines; empty = default
        },
        "product": {                    # "product" means whatever you sell: product / software / service / project capability
            "one_liner_en": "",         # one-line product/service positioning (English, required)
            "one_liner_local": "",      # optional: version in another language
            "primary_keywords": [],     # core terms customers use to search for you (≥3, required), e.g. ["<your-core-offer>"]
            "alt_keywords": [],         # synonyms / category extensions
            "differentiators": [],      # differentiators (≥2, required, must be verifiable)
            "moq": "",                  # optional (physical goods): minimum order, e.g. "50 pcs"
            "sample_lead_time": "",     # optional (physical goods): sample lead time
            "bulk_lead_time": ""        # optional (physical goods): bulk lead time
        },
        "offer": {                      # industry-generic "deal entry" layer; e-mail and WhatsApp both read from here
            "entry_offer": "",          # low-barrier way to start: free sample / 14-day trial / free audit / pilot / site visit
            "cta_question": "",         # closing question of the e-mail (English), e.g. "Open to a 20-minute demo next week?"
            "key_facts": [],            # 2–4 short facts you can state publicly: MOQ / go-live time / certifications / delivery / customer count
            "min_commitment": "",       # minimum commitment: MOQ / minimum contract / shortest subscription
            "delivery_time": "",        # delivery / go-live / implementation time
            "proof_points": [],         # public case studies or data (authorised or anonymised)
            "repeat_hook": ""           # one-liner for repeat-order follow-ups (e.g. "our 2027 range is ready")
        },
        "positioning": {                # business definition of research tags (optional)
            "need_tags": [],            # your product / service line tags, e.g. ["line_a","line_b"]; the value set of need_tag
            "conflict_groups": {},      # mutually exclusive tag groups: {"need_tag": [["a"],["b"]]}, used by conflict-check
            "tag_rules": [],            # internal consistency rules: [{"if_field":"variant_tag","equals":"x",
                                        #   "forbid_field":"need_tag","values":["y"],"reason":"..."}]
            "hooks": {}                 # opening-line overrides per decision driver: {"cost": "...{one}...{lead}..."}
        },
        "targeting": {
            "customer_industries": [],  # the customer's own industry (strongly recommended for software/services), e.g. ["logistics","manufacturing"]
            "buyer_titles": [],         # decision roles (≥1, required), e.g. ["procurement manager"] / ["CTO"] / ["HR director"]
            "channel_keywords": [],     # customer type / channel terms, e.g. distributor / contractor / startup / clinic chain
            "customer_levels": [        # user-defined customer tiers (the search script builds vocabulary from them)
                # example placeholder (edit / add / remove freely):
                # {"name": "L1_core", "desc": "", "keyword_suffixes": ["<customer-type-1>","<customer-type-2>"]}
            ],
            "target_regions": [],       # target markets, e.g. ["USA","UK","DE"]
            "languages": [],            # outreach languages, e.g. ["en","fr","de"]
            "exclude_keywords": [],     # non-target exclusion terms (industry-agnostic, filled by the user)
            "competitor_markers": [],   # peer / competitor exclusion "markers" (hit = blocked, e.g. manufacturer / agency)
            "reference_brands": [],     # reference / competitor "brand names" (for the competitor-reverse channel; never block)
        },
        "search": {                     # flank search axes (optional; apply-pack can pre-fill intent / site terms)
            "query_anchor": "auto",     # auto / offer (search by your category words) / customer (search by the customer's industry)
            "scene_terms": [], "intent_terms": [], "channel_site_terms": [],
            "niche_terms": [], "cert_terms": [], "channels": [],
            "social_platforms": []       # empty = all 10 platforms (public search without login only); or list linkedin/instagram/...
        },
        "rules": {                      # sending and risk rules (defaults given, editable)
            "daily_limit": 200,
            "local_send_window": "09:00-11:00,14:00-16:00",   # recipient's local working-day window, enforced by send_window.py
            "same_contact_cooldown_hours": 24,
            "require_confirmed_email": True,
            "opt_out_line": "",          # opt-out line in the body; empty = default English sentence, "off" = none
            "notes": ""                 # custom red lines
        },
        "data_sources": {               # data access layer: the skill ships no customer DB; the user declares it at install
            "customer_db": "",          # required: imported / crm_sync / none
            "customer_db_files": [],    # optional: imported file names (data_import.py also logs import_log.csv)
            "saas_sources": [],         # optional: names of trade SaaS / customs data platforms in use (names only; exports go through data_import)
            "mail_route": "",           # recommended: smtp_env (single mailbox key) / mailboxes (hosted multi-mailbox) / mcp (connector) / not_yet
            "mail_provider": "",        # recommended: tencent_exmail / aliyun_qiye / netease_qiye / gmail / microsoft365 / custom
            "crm": "",                  # optional: hubspot / salesforce / okki / fumeng / other / none
            "crm_route": ""             # optional: csv / api / mcp
        },
        "credentials_note": "Never write SMTP/IMAP passwords or other secrets here; provide them at runtime via environment variables: "
                            "SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/IMAP_*; hosted mailboxes only record variable names in config/mailboxes.json"
    }


def scaffold_seven_kit():
    """Copy the Soul Seven Kit templates into editable instances (never overwrites). Returns (created, existing)."""
    os.makedirs(KIT_INSTANCE_DIR, exist_ok=True)
    created, existed = 0, 0
    for name in KIT_FILES:
        src = os.path.join(KIT_TEMPLATE_DIR, name)
        dst = os.path.join(KIT_INSTANCE_DIR, name)
        if os.path.exists(dst):
            existed += 1
            continue
        with open(src, "rb") as f:
            content = f.read()
        with open(dst, "wb") as f:
            f.write(content)
        created += 1
    return created, existed


def _kit_filled_map():
    """Return {file name: bool filled}. A missing file counts as not filled."""
    out = {}
    for name in KIT_FILES:
        p = os.path.join(KIT_INSTANCE_DIR, name)
        filled = False
        if os.path.exists(p):
            head = open(p, encoding="utf-8-sig", errors="replace").read(400)
            # only filled: true in the frontmatter counts
            m = re.search(r"(?im)^\s*filled\s*:\s*(true|false)\s*$", head)
            filled = bool(m and m.group(1).lower() == "true")
        out[name] = filled
    return out


def cmd_kit_check():
    health = _cfg.kit_health()
    bad = 0
    for name, probs in health.items():
        if probs:
            bad += 1
            print(f"  ✖ {name}: {'; '.join(probs)}")
        else:
            print(f"  ✔ {name}")
    print(f"Soul Seven Kit check: {7 - bad}/7 passed." + ("" if not bad else
          " Reference: references/soul_kit/fill_reference_customer_dev.md"))
    sys.exit(1 if bad else 0)


def cmd_start():
    """New-install checklist (read-only): list everything to fill right after installing, with the current status of each item."""
    path = _cfg.profile_path()
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    missing = dict(_cfg.missing_fields(data)) if data else None
    health = _cfg.kit_health()
    g = lambda k: _cfg.get(data, k, None) if data else None
    mark = lambda ok: "✔" if ok else "✖"
    print("New-install checklist (B2B customer development · industry-agnostic edition)")
    print("=" * 60)
    print("Gate 1 · Required company profile (config/company_profile.json) — until complete, every search/send script refuses to run")
    if missing is None:
        print("  ✖ Profile missing → run python3 scripts/onboarding.py init first")
    else:
        for key, label in _cfg.REQUIRED.items():
            print(f"  {mark(key not in missing)} {label}  [{key}]")
    print("Gate 2 · Soul Seven Kit (soul_seven_kit/) — the AI's identity, brakes, owner preferences and working notes")
    for name, probs in health.items():
        print(f"  {mark(not probs)} {name}" + ("" if not probs else f": {'; '.join(probs)}"))
    print("Gate 3 · User attestation (the AI reads everything back → you reply \"confirmed\" → attest)")
    fp_ok = bool(data) and data.get("confirmed_fingerprint") == _cfg.confirm_fingerprint(data)
    print(f"  {mark(bool(data.get('user_confirmed')) and fp_ok)} user_confirmed"
          + ("" if fp_ok or not data.get("user_confirmed") else " (profile / kit changed after attestation; attest again)"))
    print("-" * 60)
    print("Recommended right away (not blocking, but directly affects results)")
    rec = [
        ("targeting.target_regions", "target markets (drive search regions and sending time zones)"),
        ("targeting.buyer_titles", "procurement-chain titles (decision / execution / influence; see search_customers.py social --titles)"),
        ("targeting.reference_brands", "reference / competitor brands (competitor reverse and social public search)"),
        ("offer.key_facts", "verifiable short facts (e-mail evidence, S1-level source)"),
        ("offer.entry_offer", "low-barrier first order / trial / sample offer"),
        ("rules.local_send_window", "recipient-local sending window (default 09:00-11:00,14:00-16:00)"),
        ("search.social_platforms", "social platforms to use (default all 10, public search without login only)"),
    ]
    for key, label in rec:
        v = g(key)
        print(f"  {mark(not _cfg._is_empty(v))} {label}  [{key}]")
    print("-" * 60)
    print("Data access layer (configure right after install; every path is inside this skill, no external tutorial needed)")
    db_state = g("data_sources.customer_db") or ""
    db_file = os.path.join(os.environ.get("B2B_DATA_DIR", "data"), "customer_db.csv")
    print(f"  {mark(db_state in _cfg.CUSTOMER_DB_STATES)} Own customer DB [data_sources.customer_db] = {db_state or 'not declared'}"
          + ("" if db_state != "imported" or os.path.exists(db_file) else f" (declared imported, but {db_file} does not exist)"))
    print("      Import: python3 scripts/data_import.py inspect <Excel/CSV> → import --relation existing_customer|prospect --source own:excel")
    print("      SaaS / customs / CRM exports go through data_import as well; integration notes in references/saas_integration_guide.md")
    route = g("data_sources.mail_route") or ""
    env_ok = all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))
    try:
        import mail_setup as _ms
        n_mb = len(_ms.load_mailboxes()["mailboxes"])
    except Exception:
        n_mb = 0
    print(f"  {mark(route in ('smtp_env', 'mailboxes', 'mcp'))} Sending route [data_sources.mail_route] = {route or 'not chosen'}"
          f" | SMTP env vars {'set' if env_ok else 'not set'} | hosted mailboxes: {n_mb}")
    print("      Enterprise mailbox key: python3 scripts/mail_setup.py providers → env <provider> --user <mailbox> → test (login only, no sending)")
    print("      Hosted multi-mailbox + warm-up: mail_setup.py add <id> ...; MCP / connectors: references/mail_setup.md path B")
    crm = g("data_sources.crm") or ""
    print(f"  {mark(bool(crm))} CRM sync [data_sources.crm] = {crm or 'not chosen'}"
          "｜python3 scripts/crm_sync.py export --target <hubspot|salesforce|okki|fumeng|generic>")
    print("  ·  Data triggers: python3 scripts/triggers.py scan (once a day; scheduling in automation_setup.md)")
    print("-" * 60)
    if missing is None:
        print("Next: python3 scripts/onboarding.py init")
    elif missing:
        print("Next: python3 scripts/onboarding.py ask (or let the AI interview you); optionally packs / apply-pack <id> first")
    elif any(health.values()):
        print("Next: fill the Soul Seven Kit per references/soul_kit/fill_reference_customer_dev.md → onboarding.py kit-check")
    elif not data.get("user_confirmed") or not fp_ok:
        print("Next: onboarding.py check → AI reads back → you confirm → onboarding.py attest")
    else:
        print("READY: all three gates passed. Daily work starts at SKILL.md \"Step 0 Omni-channel review\".")


def cmd_init():
    path = _cfg.profile_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print(f"EXISTS profile already exists, not overwritten: {path}")
        print("Delete the file manually if you want to start over.")
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blank_profile(), f, ensure_ascii=False, indent=2)
        print(f"CREATED blank profile: {path}")
    created, existed = scaffold_seven_kit()
    print(f"CREATED Soul Seven Kit instance directory: {KIT_INSTANCE_DIR} ({created} created, {existed} already existed, none overwritten)")
    print("Next: let the AI walk you through company_profile.json + the Soul Seven Kit per the SKILL.md install gate, "
          "or run python3 scripts/onboarding.py ask; then run check.")


def cmd_check():
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED profile missing. Run first: python3 scripts/onboarding.py init")
        sys.exit(2)
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    missing = _cfg.missing_fields(data)
    if missing:
        print(f"INCOMPLETE company_profile.json still lacks {len(missing)} required fields:")
        for key, label in missing:
            print(f"  - {label}  [{key}]")
        sys.exit(1)

    # Every Soul Seven Kit file must pass the content check (filled=true is self-reported; the check reads the real content)
    health = _cfg.kit_health()
    unfilled = [name for name, probs in health.items() if probs]
    if unfilled:
        print(f"INCOMPLETE {len(unfilled)} Soul Seven Kit files have not passed the content check:")
        for name in unfilled:
            print(f"  - {name}: {'; '.join(health[name])}")
        print("Let the AI guide you file by file per references/soul_kit/fill_reference_customer_dev.md (three to five lines each, "
              "replace every \"(e.g. …)\" with your real practice); then set filled to true at the top and run check again.")
        sys.exit(1)

    # Required fields + kit filled only means "content exists"; the user must still attest, so the AI cannot invent it.
    if not data.get("user_confirmed"):
        print("FILLED_NOT_CONFIRMED required fields and the Soul Seven Kit are filled, but the user has not attested yet.")
        print("")
        print("Next (the AI must not skip this or confirm on the user's behalf):")
        print("  1) Read all key information in config/company_profile.json and the 7 soul_seven_kit/ files")
        print("     back to the user verbatim; every contact detail, brand name and product fact must come from the user or their website,")
        print("     never guessed or invented by the AI.")
        print("  2) Only after the user explicitly replies \"confirmed\", run:")
        print("       python3 scripts/onboarding.py attest")
        print("  3) Until the user explicitly confirms, every search/send script stays blocked by the gate.")
        sys.exit(3)

    if data.get("confirmed_fingerprint") != _cfg.confirm_fingerprint(data):
        print("CHANGED_AFTER_CONFIRM the profile or the Soul Seven Kit was modified after attestation (content fingerprint mismatch).")
        print("Read the changes back to the user; after an explicit \"confirmed\", run python3 scripts/onboarding.py attest again.")
        sys.exit(3)

    print("READY profile + Soul Seven Kit complete and attested by the user (user_confirmed=true). Search/send may start.")
    biz = data.get("business", {})
    print("Company:", data["company"]["brand_display"], "| Industry:", biz.get("industry", ""),
          "| Type:", biz.get("offer_type", ""), "| Pack:", biz.get("industry_pack") or "none",
          "| Positioning:", data["product"]["one_liner_en"])
    _soft_warnings(data)


def _soft_warnings(data):
    """Non-blocking reminders: optional fields that affect cross-industry results."""
    biz, tg, of = data.get("business", {}), data.get("targeting", {}), data.get("offer", {})
    tips = []
    if biz.get("offer_type") in ("software", "service") and not tg.get("customer_industries"):
        tips.append("Software/service businesses should fill targeting.customer_industries (the customer's industry); otherwise search tends to find competitors.")
    if not (of.get("entry_offer") or of.get("cta_question")):
        tips.append("offer.entry_offer / cta_question are both empty: e-mails will use a neutral closing question, which usually converts worse.")
    if not of.get("key_facts") and not (data.get("product", {}).get("moq")):
        tips.append("offer.key_facts is empty: e-mails will contain no verifiable short facts.")
    ds = data.get("data_sources", {})
    if ds.get("customer_db") in ("imported", "crm_sync"):
        dbf = os.path.join(os.environ.get("B2B_DATA_DIR", "data"), "customer_db.csv")
        if not os.path.exists(dbf):
            tips.append(f"You declared an own customer DB, but {dbf} does not exist yet: python3 scripts/data_import.py import <file> "
                        "--relation existing_customer --source own:excel (existing customers never enter the cold pool).")
    if not ds.get("mail_route") or ds.get("mail_route") == "not_yet":
        tips.append("Sending route not configured: python3 scripts/mail_setup.py providers (enterprise mailbox key) or references/mail_setup.md path B (MCP).")
    for t in tips:
        print("TIP " + t)


def cmd_attest():
    """Called by the AI only after the user's explicit confirmation reply; formally activates the profile."""
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED profile missing. Run init first.")
        sys.exit(2)
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    missing = _cfg.missing_fields(data)
    if missing:
        print(f"REFUSED {len(missing)} required fields are still empty; cannot attest. Complete them first.")
        sys.exit(1)
    unfilled = _cfg.unfilled_kit_files()
    if unfilled:
        print("REFUSED the Soul Seven Kit has not fully passed the content check; cannot attest:", ", ".join(unfilled),
              "(run onboarding.py kit-check for the reasons)")
        sys.exit(1)
    data["user_confirmed"] = True
    data["configured"] = True
    today = datetime.date.today().isoformat()
    data["confirmed_at"] = today
    data.setdefault("filled_at", today)
    data["confirmed_fingerprint"] = _cfg.confirm_fingerprint(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("ACTIVATED user attestation recorded, configured=true. The skill is now usable.")
    print("NOTE content fingerprint of profile + kit recorded: any later change makes the scripts ask for a read-back and a new attest.")


def _ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def _ask_list(prompt, min_n=0):
    print(f"{prompt} (comma-separated, at least {min_n}; press Enter to finish)")
    while True:
        raw = input("> ").strip()
        items = [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]
        if len(items) >= min_n:
            return items
        print(f"  At least {min_n} required, please enter again.")


def cmd_ask():
    path = _cfg.profile_path()
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = blank_profile()
        print("No profile found; loaded the blank template.")
    else:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        print("Loaded the existing profile; press Enter to keep a value.")

    for k, v in blank_profile().items():           # add sections introduced after the old profile was created
        if isinstance(v, dict):
            data.setdefault(k, {})
            for kk, vv in v.items():
                data[k].setdefault(kk, vv)
    c, p_, t = data["company"], data["product"], data["targeting"]
    ct, b, o = data["contact"], data["business"], data["offer"]
    b["industry"] = _ask("Industry / niche (one line)", b.get("industry", ""))
    while True:
        b["offer_type"] = _ask("Delivery type: physical_product / software / service / project / other",
                               b.get("offer_type", ""))
        if b["offer_type"] in _cfg.OFFER_TYPES:
            break
        print("  Please choose one of the 5 values above.")
    c["brand_display"] = _ask("Company / brand display name", c["brand_display"])
    c["website"] = _ask("Company website (optional)", c.get("website", ""))
    ct["founder_name"] = _ask("External contact person name", ct.get("founder_name", ""))
    ct["email"] = _ask("Sending mailbox", ct.get("email", ""))
    ct["whatsapp"] = _ask("WhatsApp (international format, optional)", ct.get("whatsapp", ""))
    p_["one_liner_en"] = _ask("One-line product/service positioning (English)", p_.get("one_liner_en", ""))
    if not p_.get("primary_keywords"):
        p_["primary_keywords"] = _ask_list("Core keywords customers use when searching for your kind of product/service", min_n=3)
    if not p_.get("differentiators"):
        p_["differentiators"] = _ask_list("Differentiators", min_n=2)
    if not t.get("buyer_titles"):
        t["buyer_titles"] = _ask_list("Target decision roles (e.g. procurement manager / CTO / HR director)", min_n=1)
    if b.get("offer_type") in ("software", "service") and not t.get("customer_industries"):
        t["customer_industries"] = _ask_list("Which industries are your customers in? (software/services find people by customer industry; optional)", min_n=0)
    o["entry_offer"] = _ask("Low-barrier way to start (optional: sample / trial / audit / pilot…)", o.get("entry_offer", ""))
    o["cta_question"] = _ask("Closing question of the e-mail (English, optional)", o.get("cta_question", ""))
    if not o.get("key_facts"):
        o["key_facts"] = _ask_list("2–4 short public facts (MOQ / go-live / certifications / delivery…; optional)", min_n=0)
    ds = data.setdefault("data_sources", {})
    print("—— Data access layer: the skill ships no customer DB; declare your own situation ——")
    while True:
        ds["customer_db"] = _ask("Own customer DB: imported (have Excel/CSV, import now with data_import.py)"
                                 " / crm_sync (export from CRM then import) / none (none yet, start from zero)",
                                 ds.get("customer_db", ""))
        if ds["customer_db"] in _cfg.CUSTOMER_DB_STATES:
            break
        print("  Please choose one of imported / crm_sync / none.")
    ds["mail_route"] = _ask("Sending route: smtp_env (enterprise mailbox + key) / mailboxes (hosted multi-mailbox warm-up) / mcp (connector) / not_yet",
                            ds.get("mail_route", ""))
    if ds["mail_route"] in ("smtp_env", "mailboxes"):
        ds["mail_provider"] = _ask("Mail provider: tencent_exmail / aliyun_qiye / netease_qiye / gmail / microsoft365 / custom",
                                   ds.get("mail_provider", ""))
    ds["crm"] = _ask("CRM (optional): hubspot / salesforce / okki / fumeng / other / none", ds.get("crm", ""))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSAVED written to {path}")
    print("Run python3 scripts/onboarding.py check to validate; after filling the kit, reading back to the user and getting explicit confirmation, "
          "run python3 scripts/onboarding.py attest to activate.")
    print("Tip: tiers (customer_levels), exclusion terms, target markets etc. can be edited directly in the JSON, but the user must confirm again afterwards.")


# ---------------- Industry packs ----------------
# Only method-level fields are written; company facts (brand, contacts, keywords, differentiators, offer.*) are never filled by a pack.
_PACK_TARGETS = [
    ("targeting.buyer_titles", "buyer_titles"),
    ("targeting.channel_keywords", "channel_keywords"),
    ("targeting.customer_levels", "customer_levels"),
    ("targeting.exclude_keywords", "exclude_keyword_examples"),
    ("search.intent_terms", "intent_terms"),
    ("search.channel_site_terms", "channel_site_terms"),
    ("search.channels", "recommended_channels"),
]


def _set_path(d, dotted, value):
    cur = d
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _no_placeholder(v):
    """Drop suggested values containing <placeholders> so template text never lands in the profile."""
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                x = dict(x)
                x["keyword_suffixes"] = [w for w in x.get("keyword_suffixes", []) if "<" not in str(w)]
                if x["keyword_suffixes"]:
                    out.append(x)
            elif "<" not in str(x):
                out.append(x)
        return out
    return v


def cmd_packs():
    packs = _cfg.load_packs()
    print(f"{len(packs)} built-in industry packs (method-level hints, no company facts):")
    for pid, p in packs.items():
        print(f"  {pid:<24} {p.get('name','')}  [{p.get('offer_type','')}]")
        print(f"  {'':<24} Suits: {p.get('suits','')}")
    print("\nView: python3 scripts/onboarding.py pack <id>    Apply: python3 scripts/onboarding.py apply-pack <id>")


def cmd_pack(pid):
    p = _cfg.load_packs().get(pid)
    if not p:
        print(f"UNKNOWN no industry pack \"{pid}\". Run packs to list all.")
        sys.exit(1)
    print(json.dumps(p, ensure_ascii=False, indent=2))


def cmd_apply_pack(pid):
    p = _cfg.load_packs().get(pid)
    if not p:
        print(f"UNKNOWN no industry pack \"{pid}\". Run packs to list all.")
        sys.exit(1)
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED profile missing. Run init first.")
        sys.exit(2)
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    filled, kept = [], []
    for dotted, key in _PACK_TARGETS:
        val = _no_placeholder(p.get(key))
        if not val:
            continue
        if _cfg._is_empty(_cfg._get_path(data, dotted)):
            _set_path(data, dotted, val)
            filled.append(dotted)
        else:
            kept.append(dotted)
    biz = data.setdefault("business", {})
    biz["industry_pack"] = pid
    if not (biz.get("offer_type") or "").strip():
        biz["offer_type"] = p.get("offer_type", "")
        filled.append("business.offer_type")
    # Any change must be confirmed by the user again
    data["user_confirmed"] = False
    data["configured"] = False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"APPLIED industry pack {pid} ({p.get('name','')})")
    print("  Written (were empty): " + (", ".join(filled) or "none"))
    print("  Kept your values: " + (", ".join(kept) or "none"))
    print("  For reference only, not written (company facts the user must provide): entry_offer / cta / key_facts / competitor_markers")
    for k in ("entry_offer_examples", "cta_examples", "key_fact_examples", "competitor_marker_examples"):
        if p.get(k):
            print(f"    - {k}: {', '.join(p[k])}")
    if p.get("compliance_notes"):
        print(f"  Compliance note: {p['compliance_notes']}")
    print("NEXT user_confirmed reset to false: read the written content back to the user, adapt each item to their business, "
          "then attest.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd == "packs":
        return cmd_packs()
    if cmd in ("pack", "apply-pack"):
        if not arg:
            print(f"Usage: python3 onboarding.py {cmd} <pack_id> (run packs first to list them)")
            sys.exit(1)
        return cmd_pack(arg) if cmd == "pack" else cmd_apply_pack(arg)
    if cmd == "start":
        return cmd_start()
    if cmd == "kit-check":
        return cmd_kit_check()
    if cmd == "init":
        cmd_init()
    elif cmd == "check":
        cmd_check()
    elif cmd == "ask":
        cmd_ask()
    elif cmd == "attest":
        cmd_attest()
    else:
        print(__doc__)
        print("Usage: python3 onboarding.py [start|init|check|kit-check|ask|attest|packs|pack <id>|apply-pack <id>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
