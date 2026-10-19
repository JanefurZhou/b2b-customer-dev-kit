#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — shared company-profile loader + first-time configuration gate (used by every business script)

Design principles
--------
1. This skill is a **generic, de-identified template**: it embeds no real company name, product, contact or keyword.
2. All business information comes from the `company_profile.json` the user fills in on first use.
3. Every business script must call `load_profile(require_complete=True)` before doing any work:
   - no profile / required fields empty → raises `ProfileNotConfigured`, the script stops immediately
     and prints a clear "run onboarding.py / let the AI onboard you" instruction.
4. Sending credentials (SMTP/IMAP passwords etc.) are secrets: **never** stored in the profile, always environment variables.

Path resolution: the profile lives at `config/company_profile.json` under the skill root by default,
overridable with the B2B_PROFILE environment variable. Standard library only.
"""

import os
import re
import json
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---- profile location (resolved relative to this file, no hard-coded absolute path) ----
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_HERE)
DEFAULT_PROFILE = os.path.join(_SKILL_ROOT, "config", "company_profile.json")


def profile_path():
    return os.environ.get("B2B_PROFILE") or DEFAULT_PROFILE


class ProfileNotConfigured(RuntimeError):
    """Profile missing or required fields incomplete. Business scripts catch this, stop, and guide onboarding."""


# Required fields: dotted key path -> human-readable label (must be collected at first onboarding)
REQUIRED = {
    "business.industry": "industry / niche (one line, e.g. \"industrial valves export\", \"HR SaaS\", \"cross-border logistics\")",
    "business.offer_type": "delivery type (physical_product / software / service / project / other)",
    "company.brand_display": "company / brand display name (used in the e-mail signature)",
    "contact.founder_name": "external contact person name",
    "contact.email": "sending mailbox",
    "product.one_liner_en": "one-line product/service positioning (English)",
    "product.primary_keywords": "core keywords customers use when searching for your kind of product/service (at least 3)",
    "product.differentiators": "differentiators (at least 2)",
    "targeting.buyer_titles": "target decision roles (at least 1)",
    "data_sources.customer_db": "own customer DB (imported = imported with data_import.py / crm_sync = exported from CRM then imported / none = none yet, start from zero)",
}

# Allowed values of the customer-DB declaration (the skill ships no customer DB; the user declares and imports at install)
CUSTOMER_DB_STATES = ("imported", "crm_sync", "none")
MAIL_ROUTES = ("smtp_env", "mailboxes", "mcp", "not_yet")


def _get_path(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _is_empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def load_profile(require_complete=True):
    """Load and (by default) validate the company profile.

    With require_complete=True a missing profile or empty required fields raise ProfileNotConfigured.
    With require_complete=False the raw dict (possibly the blank template) is returned for tools/checks.
    """
    path = profile_path()
    if not os.path.exists(path):
        if require_complete:
            raise ProfileNotConfigured(
                "Company profile company_profile.json not found.\n"
                "This is a generic template skill: onboarding must be completed before first use.\n"
                "Run: python3 scripts/onboarding.py init  to create a blank profile, "
                "or let the AI guide you through it per the SKILL.md install gate, then run this task again."
            )
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ProfileNotConfigured(f"Company profile cannot be parsed: {e}. Run onboarding.py init again.")

    if require_complete and not data.get("configured"):
        raise ProfileNotConfigured(not_ready_message(data))
    if require_complete and data.get("confirmed_fingerprint") != confirm_fingerprint(data):
        raise ProfileNotConfigured(
            "The company profile or the Soul Seven Kit was modified after user attestation (content fingerprint mismatch); business tasks are blocked.\n"
            "Run python3 scripts/onboarding.py check, read the changes back to the user, "
            "and after an explicit \"confirmed\" run python3 scripts/onboarding.py attest.")
    return data


_VOLATILE_KEYS = ("user_confirmed", "configured", "confirmed_at", "confirmed_fingerprint", "filled_at")


def confirm_fingerprint(data, kit_dir=None):
    """sha256 of the profile (minus attestation fields) + full text of the kit. Written at attest; any later change breaks the match."""
    import hashlib
    h = hashlib.sha256()
    core = {k: v for k, v in (data or {}).items() if k not in _VOLATILE_KEYS}
    h.update(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    kit_dir = kit_dir or os.path.join(_SKILL_ROOT, "soul_seven_kit")
    for name in _KIT_FILES:
        fp = os.path.join(kit_dir, name)
        h.update(name.encode())
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


_KIT_FILES = ["IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md",
              "MEMORY.md", "USER.md", "HEARTBEAT.md"]


# Soul Seven Kit content check (rules from soul-seven-kit: missing file / empty shell / untouched example / missing key section)
KIT_REQUIRED_KEYWORDS = {
    "IDENTITY.md": ("Role", "Serves", "Red line"),
    "SOUL.md": ("Tone", "Priorit", "Decision"),
    "AGENTS.md": ("SOP", "Human confirmation", "Never"),
    "TOOLS.md": ("When to use", "How to use", "breaks"),
    "MEMORY.md": ("Conclusion", "To-do", "Next step"),
    "USER.md": ("Report", "Approval", "Sensitive"),
    "HEARTBEAT.md": ("Run", "Completion rate", "Error"),
}
KIT_MIN_SUBSTANTIVE = 3   # at least 3 lines of real content per file (three to five is enough)


def _kit_body(text):
    text = re.sub(r"(?s)\A---.*?---\s*", "", text, count=1)      # frontmatter
    return re.sub(r"(?s)<!--.*?-->", "", text)                   # HTML comments


def _substantive(line):
    t = line.strip()
    if not t or t.startswith("#") or t.startswith("_Last updated") or t.startswith("_最后更新"):
        return False
    t = re.sub(r"^(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)、]\s*)", "", t).strip()
    if not t or t.startswith("(e.g.") or t.startswith("（例") or t.startswith("(例"):
        return False
    # A bare label with nothing after the colon (e.g. "- Time:" / "Completion rate: / (actual / planned)") does not count as content
    if re.fullmatch(r"[^：:]{0,20}[：:]\s*(?:/\s*)?(?:（[^）]*）)?\s*", t):
        return False
    return len(t) >= 4


def kit_health(kit_dir=None):
    """Return {file name: [problems…]}; empty list = this file passes. Read-only."""
    kit_dir = kit_dir or os.path.join(_SKILL_ROOT, "soul_seven_kit")
    out = {}
    for name in _KIT_FILES:
        fp = os.path.join(kit_dir, name)
        probs = []
        if not os.path.exists(fp):
            out[name] = ["missing: file does not exist (run onboarding.py init first)"]
            continue
        with open(fp, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        m = re.search(r"(?im)^\s*filled\s*:\s*(true|false)\s*$", text[:400])
        if not (m and m.group(1).lower() == "true"):
            probs.append("filled at the top is not true")
        body = _kit_body(text)
        lines = body.splitlines()
        n_sub = sum(1 for ln in lines if _substantive(ln))
        if n_sub < KIT_MIN_SUBSTANTIVE:
            probs.append(f"empty shell: only {n_sub} lines of real content (at least {KIT_MIN_SUBSTANTIVE})")
        left = [ln.strip() for ln in lines if re.match(r"^\s*(?:[-*]\s*)?(?:\(e\.g\.|[（(]例)", ln)]
        if left:
            probs.append(f"{len(left)} example lines \"(e.g. …)\" not yet replaced with your real situation")
        ph = find_placeholder_text(body)
        if ph:
            probs.append("leftover placeholders: " + ", ".join(ph[:5]))
        miss = [k for k in KIT_REQUIRED_KEYWORDS.get(name, ()) if k not in body]
        if miss:
            probs.append("missing key sections: " + " / ".join(miss))
        out[name] = probs
    return out


def unfilled_kit_files():
    """Return the names of Soul Seven Kit files that fail the content check (missing directory = all unfilled)."""
    return [n for n, probs in kit_health().items() if probs]


def not_ready_message(data):
    """Report the step that is actually blocking, following the three gates (required fields → kit → attestation)."""
    head = "Company profile not ready (configured != true); business tasks are blocked.\n"
    missing = missing_fields(data)
    if missing:
        return (head + "Blocked at gate 1: company_profile.json still lacks these required fields:\n" +
                "\n".join(f"  - {label} ({key})" for key, label in missing) +
                "\nLet the AI fill them one by one per the SKILL.md install gate, then run "
                "python3 scripts/onboarding.py check。")
    unfilled = unfilled_kit_files()
    if unfilled:
        health = kit_health()
        return (head + "Required fields complete; blocked at gate 2: "
                f"{len(unfilled)} Soul Seven Kit files have not passed the content check:\n" +
                "\n".join(f"  - soul_seven_kit/{n}: {'; '.join(health[n])}" for n in unfilled) +
                "\nIf the directory does not exist, run python3 scripts/onboarding.py init first; "
                "after filling, run python3 scripts/onboarding.py check.")
    if not data.get("user_confirmed"):
        return (head + "Required fields and the Soul Seven Kit are ready; blocked at gate 3: not yet attested by the user.\n"
                "Run python3 scripts/onboarding.py check, read the profile back to the user verbatim, "
                "and after an explicit \"confirmed\" run python3 scripts/onboarding.py attest.")
    return (head + "All three checks pass but the configured flag is still false. "
            "Run python3 scripts/onboarding.py attest to activate.")


OFFER_TYPES = ("physical_product", "software", "service", "project", "other")

# Template placeholders: text like <your-moq> / {intro} landing in the profile or an outgoing e-mail is an incident
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>@\n]{1,60}>|\{[A-Za-z_][A-Za-z0-9_.\[\]]{1,40}\}")
_PLACEHOLDER_SECTIONS = ("business", "company", "contact", "product", "offer")


def find_placeholder_text(text):
    """Return the template placeholders left in the text (de-duplicated, order kept)."""
    out = []
    for m in PLACEHOLDER_RE.findall(text or ""):
        if m not in out:
            out.append(m)
    return out


def find_placeholders(data):
    """Scan externally used sections of the profile; return [(dotted_path, placeholder), ...]."""
    hits = []

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")
        elif isinstance(v, str):
            for ph in find_placeholder_text(v):
                hits.append((path, ph))
    for sec in _PLACEHOLDER_SECTIONS:
        walk((data or {}).get(sec, {}), sec)
    return hits


def missing_fields(data):
    """Return [(key, label), ...] for every empty required field (an invalid offer_type value also counts)."""
    out = []
    for key, label in REQUIRED.items():
        v = _get_path(data, key)
        if _is_empty(v):
            out.append((key, label))
        elif key == "business.offer_type" and str(v).strip() not in OFFER_TYPES:
            out.append((key, label + f" — current value \"{v}\" is not an allowed value"))
        elif key == "data_sources.customer_db" and str(v).strip() not in CUSTOMER_DB_STATES:
            out.append((key, label + f" — current value \"{v}\" is not an allowed value"))
    for path, ph in find_placeholders(data):
        out.append((path, f"contains an unreplaced template placeholder {ph} (replace with the user's real value, or delete the item)"))
    return out


# ============================================================
# Industry packs (method-level hints, no company facts)
# ============================================================
PACKS_FILE = os.path.join(_SKILL_ROOT, "references", "industry_packs.json")


def load_packs():
    """Return {pack_id: pack_dict}; empty dict if the file is missing."""
    try:
        with open(PACKS_FILE, encoding="utf-8-sig") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {p["id"]: p for p in doc.get("packs", []) if p.get("id")}


def active_pack(profile):
    """Read the pack referenced by profile.business.industry_pack; None if unset."""
    pid = (get(profile or {}, "business.industry_pack", "") or "").strip()
    return load_packs().get(pid) if pid else None


# ============================================================
# Generic / functional mailbox prefixes (all industries): hit = not a named mailbox, B-tier only or find a decision maker
# ============================================================
GENERIC_MAILBOX_PREFIXES = frozenset({
    # generic inbound
    "info", "contact", "hello", "hi", "mail", "email", "office", "general", "team",
    "enquiry", "enquiries", "inquiry", "inquiries", "reception", "admin", "webmaster",
    "noreply", "no-reply", "newsletter",
    # sales / support
    "sales", "support", "help", "service", "customercare", "customerservice", "orders",
    # physical-goods channels
    "wholesale", "trade", "export", "import", "shop", "store",
    # purchasing / partnerships / projects
    "purchasing", "procurement", "buying", "sourcing", "partners", "partnerships",
    "projects", "tenders", "bids", "vendors", "suppliers",
    # functional departments
    "marketing", "press", "media", "pr", "hr", "careers", "jobs", "recruiting",
    "billing", "accounts", "finance", "invoices", "legal", "privacy", "compliance", "it",
})


# ============================================================
# Fact layer for copy: "key facts + closing question" shared by all industries
# ============================================================
NEUTRAL_CTA = "Is this worth a short reply?"


def offer_facts(profile, limit=3):
    """Return the list of short public facts (only values the user entered at onboarding; nothing inferred).

    offer.key_facts first (generic, e.g. "MOQ 50 pcs" / "setup in 2 days" /
    "ISO 13485 certified"); if empty, fall back to legacy product.moq / sample_lead_time /
    bulk_lead_time (physical goods)."""
    facts = [str(x).strip() for x in (get(profile, "offer.key_facts", []) or []) if str(x).strip()]
    facts = [f[0].upper() + f[1:] for f in facts]
    if not facts:
        p = (profile or {}).get("product", {}) or {}
        if (p.get("moq") or "").strip():
            facts.append(f"MOQ {p['moq'].strip()}")
        if (p.get("sample_lead_time") or "").strip():
            facts.append(f"Samples in {p['sample_lead_time'].strip()}")
        if (p.get("bulk_lead_time") or "").strip():
            facts.append(f"Production in {p['bulk_lead_time'].strip()}")
    return facts[:limit]


def cta_question(profile):
    """Closing question: offer.cta_question (user-confirmed) > assembled from offer.entry_offer > neutral fallback."""
    q = (get(profile, "offer.cta_question", "") or "").strip()
    if q:
        return q if q.endswith("?") else q.rstrip(".") + "?"
    entry = (get(profile, "offer.entry_offer", "") or "").strip()
    if entry:
        return f"Worth a {entry}?" if not entry.lower().startswith(("a ", "an ", "the ")) else f"Worth {entry}?"
    return NEUTRAL_CTA


# ============================================================
# Decision-driver tags (solution_tag / hook_type) — 11 industry-generic values
# ============================================================
DRIVER_TAGS = ("compliance", "sustainability", "quality_upgrade", "cost", "speed",
               "low_commitment", "innovation", "exclusive_custom", "one_stop",
               "dedicated_service", "strategic_scale", "open", "unknown")
# Legacy (v1.x) tags map automatically to the new values so historical data stays valid
LEGACY_TAG_ALIASES = {
    "eco_only": "compliance", "regulated": "compliance", "eco_prefer": "sustainability",
    "traditional": "quality_upgrade", "category_only": "open", "low_moq": "low_commitment",
    "upgrade_opportunity": "quality_upgrade", "exclusive_design": "exclusive_custom",
    "strategic_partner": "strategic_scale", "seasonal": "speed", "category_expand": "one_stop",
}


def normalize_driver(tag):
    t = (tag or "").strip().lower()
    t = LEGACY_TAG_ALIASES.get(t, t)
    return t if t in DRIVER_TAGS else "unknown"


def get(profile, dotted, default=None):
    """Safely read a dotted path from the profile."""
    v = _get_path(profile, dotted)
    return default if _is_empty(v) else v


if __name__ == "__main__":
    # self-check entry point: python3 config.py
    try:
        p = load_profile(require_complete=True)
        print("OK profile ready:", get(p, "company.brand_display"))
    except ProfileNotConfigured as e:
        print("NOT_CONFIGURED")
        print(e)
        sys.exit(2)
