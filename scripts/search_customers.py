#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_customers.py  —  Industry-agnostic B2B customer search candidate generator + self-replenishing engine (skill v3.1, profile-driven)

[Industry-agnostic] This script embeds no product terms, customer tiers or exclusion words for any
specific industry; it works for physical goods, software, services and project businesses. Optional
industry packs (references/industry_packs.json, written into the profile by onboarding.py apply-pack) only supply method-level hints: intent terms, site terms, recommended channels.
All business vocabulary is read at runtime from config/company_profile.json:
  - core product terms       product.primary_keywords + product.alt_keywords
  - decision-maker titles    targeting.buyer_titles
  - channel terms            targeting.channel_keywords
  - customer tiers           targeting.customer_levels (each with name/desc/keyword_suffixes)
                             when undefined, buyer_titles + channel_keywords form one default tier
  - non-target exclusions    targeting.exclude_keywords (hit = blocked; empty = no industry exclusion)
  - competitor markers       targeting.competitor_markers (hit = blocked; empty = no competitor exclusion)
  - target regions           targeting.target_regions (can be overridden with --regions)
  - flank axes               optional search.scene_terms / intent_terms / channel_site_terms /
                             niche_terms / cert_terms (if unset, intent/site axes use neutral generic
                             terms and the other three axes stay off)
Without a profile, or with required fields missing, every business sub-command is rejected by the config.py gate (exit 2).

Self-replenishing engine (never runs dry · fully automatic · pool floor):
  1) Pool floor (never dry): A-tier sendable pool < red line (default 100) → auto-replenish + warning.
  2) Four-axis rotation state machine: depth (d1/d2/d3) → reach (regions near→far) → height (customer tiers high→low) → breadth (core/wide/max), stepped rotation (progress kept in state.json).
  3) Built-in scheduler (daemon): schedule mode runs once a day at a fixed time:
     check pool → replenish if low → rotate search → back to pool, as one closed loop.

  breadth has three levels:
  - core = {region} × {core product term} × {tier role term}, full combination
  - wide = core + scene axis / intent axis (industry-specific axes must be configured in the profile)
  - max  = core + all 5 flank axes
  Search only widens the candidate funnel; how to win the account is decided by the later research step.

Commands:
  A. Generate queries only:   python3 search_customers.py queries [--out queries.txt]
  B. Channel discovery:       python3 search_customers.py channels [--ch social maps ...] [--out ch.txt]
  C. Filter + grade:          python3 search_customers.py filter results.json \
                                 --against customer_db.csv [--since 2026-04-01] [--out candidates.csv]
  D. Check floor & replenish: python3 search_customers.py replenish --pool customer_db.csv
  E. Resident scheduler:      python3 search_customers.py schedule --pool customer_db.csv
  F. Rotation progress:       python3 search_customers.py status
  G. Non-target review:       python3 search_customers.py audit-exclude candidates.csv
                              (audit-category is kept as a backward-compatible alias)
  I. 10-platform social search: python3 search_customers.py social [--platforms linkedin instagram ...]
                        [--tier decision|execution|influence|all] [--regions UK,DE] [--out social.txt]
                              (only generates public site: queries usable on Google/Bing; no login, no sign-up,
                               no DMs; --titles prints the 30 procurement-chain job titles only)
  H. Tag conflict check:      python3 search_customers.py conflict-check --against customer_db.csv \
                        [--new new.json] [--since 2026-04-01] [--out conflicts.csv]
                              (new research conclusion vs. old tag in the DB; flags only, never edits; human decides)

Expected structure of results.json:
  [{"url": "...", "title": "...", "snippet": "...", "emails": ["..."]}, ...]
(emails may be omitted; when omitted they are extracted heuristically from the text)
"""

import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import re
import json
import csv
import argparse
from urllib.parse import urlparse

# ============================================================
# 0. Shared config gate (config.py, used by every business script)
# ============================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import config as _cfg
except ImportError:
    _cfg = None

# Runtime business context: filled from company_profile.json after main() passes the gate.
# Engine functions only read this dict; the module keeps no industry vocabulary of its own.
RUNTIME = {
    "categories": [],        # core product terms (primary + alt)
    "spectrum": {},          # customer tiers {tier name: [role/channel terms]}
    "regions": [],           # target regions
    "exclude_keywords": [],  # non-target exclusion terms
    "competitor_markers": [],# peer/competitor markers (hit = blocked)
    "competitors": [],       # reference/competitor brand names (for the "competitor reverse" channel; not used for blocking)
    "axes": {                # flank search axes (scene/niche/cert default empty, supplied by the profile)
        "scene": [], "intent": [], "channel": [], "niche": [], "cert": [],
    },
    "default_level": False,  # fallback single-tier flag when the profile defines no customer_levels
}

# ============================================================
# 1. Flank axes: industry-neutral generic intent terms / channel site terms
# ============================================================
# These two lists are not tied to any industry. They describe the generic buying intent
# "a buyer is looking for a supplier" and the generic "where to find people" sites. Scene/
# audience/certification axes are industry-specific and must be configured in profile.search.*_terms.
GENERIC_INTENT_TERMS = [
    # Industry-neutral "looking for a supplier" signals; shared by goods/software/services/projects.
    # Industry-specific intent terms (e.g. low MOQ / free trial / tender) come from the industry pack or profile.search.intent_terms.
    "looking for supplier", "looking for vendor", "new vendor", "vendor application",
    "request for proposal", "request for quotation", "seeking partner", "partner program",
    "alternative to", "switching provider",
]
GENERIC_CHANNEL_SITES = [
    "site:linkedin.com", "site:instagram.com",
    "site:facebook.com", "site:pinterest.com",
]
EMPTY_AXES = {
    "scene": [], "intent": list(GENERIC_INTENT_TERMS),
    "channel": list(GENERIC_CHANNEL_SITES), "niche": [], "cert": [],
}


def build_profile_context(profile):
    """Build the runtime vocabulary context from the company profile (the only source of business data)."""
    def _dedup(seq):
        seen, out = set(), []
        for x in seq:
            x = str(x).strip()
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    # ① Core terms:
    #   offer anchor    = primary_keywords + alt_keywords (your category words appear on the customer's site: goods/industrial/project)
    #   customer anchor = targeting.customer_industries (customers are found by *their own* industry: common for software/services,
    #                     e.g. selling HR software you search "logistics company", not "HR software" — that would find competitors)
    offer_terms = _dedup(
        list(_cfg.get(profile, "product.primary_keywords", []) or [])
        + list(_cfg.get(profile, "product.alt_keywords", []) or [])
    )
    customer_inds = _dedup(_cfg.get(profile, "targeting.customer_industries", []) or [])
    offer_type = (_cfg.get(profile, "business.offer_type", "") or "other").strip()
    anchor = (_cfg.get(profile, "search.query_anchor", "") or "auto").strip().lower()
    if anchor not in ("offer", "customer"):
        anchor = "customer" if (offer_type in ("software", "service") and customer_inds) else "offer"
    if anchor == "customer" and not customer_inds:
        anchor = "offer"
    categories = customer_inds if anchor == "customer" else offer_terms

    # ② Customer tiers = customer_levels[].keyword_suffixes; if undefined, role terms + channel terms form one fallback tier
    titles = list(_cfg.get(profile, "targeting.buyer_titles", []) or [])
    channels_kw = list(_cfg.get(profile, "targeting.channel_keywords", []) or [])
    levels = _cfg.get(profile, "targeting.customer_levels", []) or []
    spectrum = {}
    for lv in levels:
        if not isinstance(lv, dict):
            continue
        name = str(lv.get("name") or "").strip()
        if not name:
            continue
        suffixes = _dedup(lv.get("keyword_suffixes") or [])
        if suffixes:
            spectrum[name] = suffixes
    default_level = False
    if not spectrum:
        fallback = _dedup(titles + channels_kw) or ["buyer"]
        spectrum = {"L1_default": fallback}
        default_level = True

    # ③ Non-target exclusions + competitor markers (whatever the user lists is excluded; empty = no industry filter)
    exclude_keywords = _dedup(_cfg.get(profile, "targeting.exclude_keywords", []) or [])
    competitor_markers = _dedup(_cfg.get(profile, "targeting.competitor_markers", []) or [])

    # ④ Target regions
    regions = _dedup(_cfg.get(profile, "targeting.target_regions", []) or [])

    # ⑤ Flank axes: profile > industry pack > industry-neutral generic terms
    pack = _cfg.active_pack(profile) or {}
    axes = {
        "scene": _dedup(_cfg.get(profile, "search.scene_terms", []) or []),
        "intent": (_dedup(_cfg.get(profile, "search.intent_terms", []) or [])
                   or _dedup(pack.get("intent_terms") or [])
                   or list(GENERIC_INTENT_TERMS)),
        "channel": (_dedup(_cfg.get(profile, "search.channel_site_terms", []) or [])
                    or _dedup(pack.get("channel_site_terms") or [])
                    or list(GENERIC_CHANNEL_SITES)),
        "niche": _dedup(_cfg.get(profile, "search.niche_terms", []) or []),
        "cert": _dedup(_cfg.get(profile, "search.cert_terms", []) or []),
    }

    return {
        "categories": categories,
        "offer_terms": offer_terms,
        "anchor": anchor,
        "spectrum": spectrum,
        "regions": regions,
        "exclude_keywords": exclude_keywords,
        "competitor_markers": competitor_markers,
        "competitors": _dedup(_cfg.get(profile, "targeting.reference_brands", []) or []),
        "axes": axes,
        "default_level": default_level,
        "offer_type": offer_type,
        "default_channels": _dedup(_cfg.get(profile, "search.channels", []) or [])
                            or _dedup(pack.get("recommended_channels") or []),
        "positioning": _cfg.get(profile, "positioning", {}) or {},
        "buyer_titles": titles,
        "social_platforms": _dedup(_cfg.get(profile, "search.social_platforms", []) or []),
    }


# ============================================================
# 1.3 Channel recipe library (new discovery sources, not just Google/LinkedIn)
# ============================================================
# Template placeholders: {region}=region  {cat}=core product/service term  {role}=tier role / customer-type term
# src  = "offer" means {cat} uses your category words (tenders/hiring/reviews/customs describe "what you sell");
#        default uses the current anchor term (under the customer anchor = the customer's industry).
# fits = applicable delivery types (business.offer_type). When no channels are specified in profile.search.channels
# or the industry pack, the channels sub-command picks recipes whose fits match offer_type; "all" = generic.
ALL = "all"
PHYS = ("physical_product",)
CHANNEL_RECIPES = {
    "social": {
        "name": "Social / professional network discovery (10 platforms, public search without login; full version in the social sub-command)", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "Find target companies and decision-maker profiles by keyword/region → website → named mailbox",
        "tmpl": [
            'site:linkedin.com/company {cat} {role} {region}',
            'site:linkedin.com/in {role} {cat} {region}',
            'site:instagram.com {cat} {role} {region}',
            'site:facebook.com {cat} {role} {region}',
        ],
    },
    "maps": {
        "name": "Google Maps / local business directories", "star": "⭐⭐⭐⭐",
        "fits": ("physical_product", "service", "project"),
        "use": "Find companies with a physical address by city + customer type (stores/showrooms/contractors/clinics/warehouses); get website and phone",
        "tmpl": [
            '{role} {region} - Google Maps',
            '{cat} {role} {region} - Google Maps',
        ],
    },
    "customs": {
        "name": "Customs / import-export trade data", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "service"),
        "use": "Reverse-look real importers by product term / HS code (no-signup path first: ImportYeti basic search / site:importyeti.com; paid platforms optional); see references/customs_data_guide.md",
        "tmpl": [
            '{cat} importer {region} customs data',
            '{cat} import records {region}',
            'who imports {cat} in {region}',
            'site:importyeti.com "{cat}"',
        ],
    },
    "rfq": {
        "name": "B2B marketplace buyer side / RFQ", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "project"),
        "use": "Look at buyers, not sellers: find active buyers who are looking for a supplier from RFQ / sourcing-request pages",
        "tmpl": [
            '{cat} RFQ buyer {region}',
            '{cat} sourcing request {region}',
            'looking for {cat} supplier {region}',
        ],
    },
    "tender": {
        "name": "Public tenders / government & institutional procurement", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ALL,
        "use": "Tender = confirmed budget + confirmed need; search public procurement portals (TED, SAM.gov, local government portals) by keyword",
        "tmpl": [
            '{cat} tender {region}',
            '{cat} request for proposal {region}',
            '{cat} procurement notice {region}',
        ],
    },
    "hiring": {
        "name": "Hiring signals (a job post = budget + pain)", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ALL,
        "use": "Hiring for roles related to the problem you solve → they are investing in it; good for software, services, equipment and consumables",
        "tmpl": [
            '{cat} job {region} site:linkedin.com/jobs',
            'hiring {cat} specialist {region}',
            '{cat} manager job opening {region}',
        ],
    },
    "directory": {
        "name": "Industry directories / association member lists", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "Trade associations, chambers of commerce and directories (Kompass, Thomasnet, Europages, Clutch, etc.) list similar companies in one place",
        "tmpl": [
            '{cat} {role} directory {region}',
            '{cat} association members {region}',
            '{role} association {region}',
        ],
    },
    "review": {
        "name": "Review / comparison sites (software & services)", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ("software", "service"),
        "use": "G2/Capterra/Clutch review pages show who uses competitors and who is comparing solutions",
        "tmpl": [
            '{cat} reviews site:g2.com',
            '{cat} alternatives {region}',
            '{cat} agencies {region} site:clutch.co',
        ],
    },
    "partners": {
        "name": "Partner / integration ecosystem", "star": "⭐⭐⭐", "src": "offer", "fits": ("software", "service", "project"),
        "use": "Ecosystem marketplaces, implementation and reseller partner pages → partners who can refer or co-deliver",
        "tmpl": [
            '{cat} implementation partner {region}',
            '{cat} reseller program {region}',
            '{cat} integration partners',
        ],
    },
    "events": {
        "name": "Industry conferences / summits (sponsors · speakers · attendees)", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "The sponsors / speakers / exhibitors pages of a conference site are a high-quality decision-maker list",
        "tmpl": [
            '{cat} conference {region} speakers',
            '{cat} summit {region} sponsors',
        ],
    },
    "media": {
        "name": "Trade media / rankings / funding & expansion news", "star": "⭐⭐⭐", "fits": ALL,
        "use": "New store / new project / funding / new market entry = a buying window",
        "tmpl": [
            '{cat} {role} expansion {region}',
            '{role} raised funding {region}',
            'top {cat} {role} {region}',
        ],
    },
    "exhibition": {
        "name": "Trade show directories (exhibitor / buyer lists)", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "project"),
        "use": "Lock onto the shows of your target market and pull concentrated, on-target customers from exhibitor lists / buyer directories",
        "tmpl": [
            '{cat} trade fair exhibitor list {region}',
            '{cat} trade show exhibitors {region}',
            '{cat} expo buyer directory {region}',
        ],
    },
    "competitor": {
        "name": "Competitor reverse (a competitor's customers / dealer network)", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "Start from the competitor / reference brands in your profile and find their dealers, case-study customers and integration partners",
        "tmpl": [
            '"{competitor}" distributors {region}',
            '"{competitor}" customers case study {region}',
            '"{competitor}" partner {region}',
        ],
        "needs_competitor": True,
    },
    "ecommerce": {
        "name": "DTC / independent e-commerce sellers (Shopify etc.)", "star": "⭐⭐⭐⭐", "src": "offer", "fits": PHYS,
        "use": "Find brands selling similar/adjacent products on their own site (not marketplace sellers); dig purchasing contacts from about/contact/LinkedIn",
        "tmpl": [
            '{cat} brand shopify {region}',
            '{cat} "powered by shopify" {region}',
            '{cat} online store brand {region} -amazon -ebay -etsy',
        ],
    },
    "gift": {
        "name": "Gifting / corporate gift channel (optional, must be specified manually)", "star": "⭐⭐⭐", "src": "offer", "fits": PHYS,
        "opt_in": True,
        "use": "Only when the product has gift appeal: gift shops, corporate gifting companies, lifestyle stores",
        "tmpl": [
            'gift shop {cat} supplier {region}',
            'corporate gifts {cat} {region}',
        ],
    },
}


def default_channels():
    """profile.search.channels > industry pack recommended_channels > recipes whose fits match offer_type."""
    chosen = [c for c in (RUNTIME.get("default_channels") or []) if c in CHANNEL_RECIPES]
    if chosen:
        return chosen
    ot = RUNTIME.get("offer_type") or "other"
    return [k for k, r in CHANNEL_RECIPES.items()
            if not r.get("opt_in")
            and (r.get("fits") == ALL or ot in (r.get("fits") or ()) or ot == "other")]


def _top_roles(limit=6):
    """Take the leading role terms from each tier for the {role} placeholder (avoids combinatorial explosion)."""
    out = []
    for words in RUNTIME["spectrum"].values():
        for w in words:
            if w not in out:
                out.append(w)
    return out[:limit]


def build_channel_queries(channels=None, regions=None, cats=None, roles=None):
    """Generate discovery queries per channel. channels=None = all channels; cats=None = leading core product terms."""
    chans = channels or default_channels()
    regs = regions or RUNTIME["regions"]
    all_cats = RUNTIME["categories"]
    offer_cats = RUNTIME.get("offer_terms") or all_cats
    top_roles = roles or _top_roles()
    out = []
    # The competitor-reverse channel needs reference/competitor brands in the profile; without them nothing can be generated
    competitors = list(RUNTIME.get("competitors") or [])
    for ch in chans:
        recipe = CHANNEL_RECIPES.get(ch)
        if not recipe:
            continue
        if recipe.get("needs_competitor") and not competitors:
            print(f"# skipping channel [{ch}] {recipe['name']}: no reference/competitor brands configured "
                  f"(fill targeting.reference_brands in company_profile)",
                  file=__import__("sys").stderr)
            continue
        pool = offer_cats if recipe.get("src") == "offer" else all_cats
        use_cats = cats or pool[:8]
        for tmpl in recipe["tmpl"]:
            for region in regs:
                # Competitor reverse: expand from each reference brand, independent of the product-term cartesian product
                if "{competitor}" in tmpl:
                    for comp in competitors[:6]:
                        out.append(tmpl.format(region=region, cat="", role="", competitor=comp))
                    continue
                for cat in use_cats:
                    if "{role}" in tmpl:
                        for role in top_roles:
                            out.append(tmpl.format(region=region, cat=cat, role=role))
                    else:
                        out.append(tmpl.format(region=region, cat=cat, role=""))
    seen, uniq = set(), []
    for q in out:
        q = " ".join(q.split())
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


# ============================================================
# 4. Industry-agnostic technical filter rules (not aimed at any specific industry)
# ============================================================
# 4.1 Platforms / B2B marketplaces (not end-customer sites → excluded)
PLATFORM_BLOCKLIST = [
    "alibaba.", "aliexpress.", "made-in-china.", "1688.", "globalsources.",
    "dhgate.", "amazon.", "ebay.", "wish.", "temu.", "shein.",
    "indiamart.", "tradeindia.", "ec21.", "tradekey.", "go4worldbusiness.",
    "etsy.com",
]
# 4.2 URL patterns of directory pages / blogs / media / junk pages (excluded)
#     Note: directory, tender, review and event pages found via those channels are "lead source pages",
#     not customer websites — a human/AI must first pull company names from the page and look up the site, so they are excluded here as usual and never enter the candidate pool.
NONLEAD_URL_PATTERNS = [
    "/blog/", "/news/", "/press/", "/article/", "/wiki/", "wikipedia.org",
    "/category/", "/tag/", "pinterest.", "youtube.", "reddit.",
    "/directory/", "yellowpages.", "yelp.",
]
# 4.3 Generic mailbox prefixes (→ B-tier entry instead of being discarded)
GENERIC_EMAIL_PREFIXES = set(_cfg.GENERIC_MAILBOX_PREFIXES) if _cfg is not None else {
    "info", "contact", "sales", "hello", "support", "office",
}
# 4.4 Free personal e-mail domains (not corporate → never counts as an A-tier named mailbox)
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "msn.com", "icloud.com", "me.com", "mail.com", "gmx.com",
    "proton.me", "protonmail.com",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# ============================================================
# 5. Query generation (full combination, no truncation)
# ============================================================
def build_queries(spectrum_keys=None, regions=None, breadth="core"):
    """Generate the full query set (core full combination + sampled flank axes).

    breadth:
        core = {region} × {core product term} × {tier role term}   full combination
        wide = core + scene axis + intent axis                       only axes configured in the profile / with generic terms
        max  = core + all 5 flank axes                               empty axes are skipped automatically
    """
    spectrum = RUNTIME["spectrum"]
    all_categories = RUNTIME["categories"]
    axes = RUNTIME["axes"]
    keys = spectrum_keys or list(spectrum.keys())
    regs = regions or RUNTIME["regions"]
    queries = []

    # ① Core full combination: {region} × {core product term} × {tier role term}
    for region in regs:
        for cat in all_categories:
            for key in keys:
                for role in spectrum.get(key, []):
                    queries.append(f"{region} {cat} {role}")

    # ② Flank axes (sampled; not multiplied against the core set, to avoid explosion)
    if breadth in ("wide", "max"):
        rep_cats = all_categories[:8] if len(all_categories) >= 8 else all_categories
        offer_terms = RUNTIME.get("offer_terms") or all_categories
        rep_offer = offer_terms[:8]
        if breadth == "wide":
            active_axes = [a for a in ("scene", "intent") if axes.get(a)]
        else:
            active_axes = [a for a in ("scene", "intent", "channel", "niche", "cert")
                           if axes.get(a)]
        for region in regs:
            for axis_name in active_axes:
                for term in axes[axis_name]:
                    if axis_name == "channel":
                        for cat in rep_cats:
                            queries.append(f"{term} {cat} {region}")
                    else:
                        # The intent axis describes "looking for your kind of thing", so it always pairs with your category words
                        use = rep_offer if axis_name == "intent" else rep_cats
                        for cat in use:
                            queries.append(f"{region} {term} {cat}")

    # de-duplicate, keep order
    seen, uniq = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


# ============================================================
# 6. Result filtering + full domain de-duplication + graded entry
# ============================================================
def domain_of(url):
    try:
        net = urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return ""


def is_platform(url):
    u = url.lower()
    return any(p in u for p in PLATFORM_BLOCKLIST)


def is_nonlead(url):
    u = url.lower()
    if any(p in u for p in NONLEAD_URL_PATTERNS):
        return True
    host = domain_of(url)
    return (host.startswith(("blog.", "news.", "wiki.", "press."))
            or host.endswith((".gov", ".mil")))


def is_non_target(rec):
    """Non-target category block: title/body hits profile targeting.exclude_keywords.
    With no exclusion terms configured, no industry exclusion is applied (technical filters only)."""
    keywords = RUNTIME["exclude_keywords"]
    if not keywords:
        return False
    blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('text','')}".lower()
    return any(str(k).lower() in blob for k in keywords)


def is_competitor(rec):
    """Peer/competitor block: hits profile targeting.competitor_markers,
    or the record is explicitly flagged is_competitor=True (legacy field has_own_factory supported; only active when competitor markers are configured).
    With no competitor markers configured, no competitor exclusion is applied."""
    markers = RUNTIME["competitor_markers"]
    if not markers:
        return False
    blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('url','')}".lower()
    if rec.get("is_competitor") is True or rec.get("has_own_factory") is True:
        return True
    return any(str(k).lower() in blob for k in markers)


def extract_emails(rec):
    """Pull e-mails from a record: explicit emails field first, otherwise regex-extract from snippet/title."""
    emails = list(rec.get("emails") or [])
    if not emails:
        blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('text','')}"
        emails = EMAIL_RE.findall(blob)
    clean = []
    for e in emails:
        e = e.strip().lower()
        if e and not e.endswith((".png", ".jpg", ".gif")) and e not in clean:
            clean.append(e)
    return clean


def grade_email(emails):
    """Grade: A = corporate named mailbox, send directly; B = generic/free mailbox only, find a decision maker; none = no e-mail."""
    if not emails:
        return "none", ""
    named = []
    for e in emails:
        local = e.split("@")[0].split("+")[0]
        dom = e.split("@")[1] if "@" in e else ""
        if local not in GENERIC_EMAIL_PREFIXES and dom not in FREE_EMAIL_DOMAINS:
            named.append(e)
    if named:
        return "A", named[0]
    return "B", emails[0]


# ============================================================
# 6.1  Incremental de-duplication against the customer DB
# ============================================================
def domain_from_website(website):
    """Take the domain from the website field (tolerates missing http prefix / www)."""
    if not website:
        return ""
    w = website.strip().lower()
    if "://" not in w:
        w = "http://" + w
    return domain_of(w)


def load_customer_db(csv_path, since=None):
    """Load the customer DB and build three indexes: e-mail / domain / customer_code."""
    emails, domains, codes = set(), set(), set()
    loaded = 0
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if since:
                ts = (row.get("added_date") or row.get("created_at")
                      or row.get("updated_at") or "")[:10]
                if ts and ts < since:
                    continue
            loaded += 1
            em = (row.get("email") or "").strip().lower()
            if em:
                emails.add(em)
            dom = domain_from_website(row.get("website") or "")
            if dom:
                domains.add(dom)
            code = (row.get("customer_code") or "").strip()
            if code:
                codes.add(code)
    return emails, domains, codes, loaded


def in_customer_db(rec, dom, emails_set, domains_set, codes_set):
    """Decide whether a record is already in the DB, by e-mail → website domain → customer_code."""
    for e in extract_emails(rec):
        if e in emails_set:
            return True
    if dom and dom in domains_set:
        return True
    code = (rec.get("customer_code") or "").strip()
    if code and code in codes_set:
        return True
    return False


def filter_and_grade(results, db_index=None):
    """Core: incremental DB de-dup + full domain de-dup + platform/directory/government/media technical filters
    + non-target / competitor filters (all profile-driven) + grading."""
    stats = {
        "input": len(results), "platform_skip": 0, "nonlead_skip": 0,
        "nontarget_skip": 0, "competitor_skip": 0,
        "dup_domain_skip": 0, "dup_in_db_skip": 0,
        "A": 0, "B": 0, "no_email": 0, "candidates": 0,
    }
    emails_set, domains_set, codes_set = db_index or (set(), set(), set())
    seen_domains = set()
    candidates = []
    for rec in results:
        url = rec.get("url", "")
        if not url:
            continue
        if is_platform(url):
            stats["platform_skip"] += 1
            continue
        if is_nonlead(url):
            stats["nonlead_skip"] += 1
            continue
        dom = domain_of(url)
        if not dom:
            continue
        if dom in seen_domains:
            stats["dup_domain_skip"] += 1
            continue
        seen_domains.add(dom)
        if db_index and in_customer_db(rec, dom, emails_set, domains_set, codes_set):
            stats["dup_in_db_skip"] += 1
            continue
        if is_non_target(rec):
            stats["nontarget_skip"] += 1
            continue
        if is_competitor(rec):
            stats["competitor_skip"] += 1
            continue

        emails = extract_emails(rec)
        grade, best = grade_email(emails)
        if grade == "A":
            stats["A"] += 1
        elif grade == "B":
            stats["B"] += 1
        else:
            stats["no_email"] += 1

        candidates.append({
            "domain": dom,
            "url": url,
            "brand": rec.get("title", "").strip()[:120],
            "email_grade": grade,
            "best_email": best,
            "all_emails": ";".join(emails),
            "region_hint": rec.get("region_hint", ""),
            "customer_type_hint": rec.get("customer_type_hint", ""),
            "next_action": {
                "A": "send directly (corporate named mailbox)",
                "B": "enter DB + find decision maker on LinkedIn / fill named mailbox with email_guesser",
                "none": "enter DB + fill e-mail from website/LinkedIn",
            }[grade],
            "note": "B-tier = generic/free mailbox only (info@/gmail.com etc.)" if grade == "B" else "",
        })
    stats["candidates"] = len(candidates)
    return candidates, stats


# ============================================================
# 6.2  Search funnel diagnostics
# ============================================================
FUNNEL_DUP_DB_RED = 0.40      # in-DB duplicate rate >40% → red
FUNNEL_NAMED_EMAIL_RED = 0.20 # named-mailbox rate <20% → red


def build_funnel(stats):
    """Turn filter stats into a funnel diagnosis."""
    total = max(stats["input"], 1)
    after_platform = stats["input"] - stats["platform_skip"] - stats["nonlead_skip"]
    after_dupdom = after_platform - stats["dup_domain_skip"]
    after_db = after_dupdom - stats["dup_in_db_skip"]
    after_nt = after_db - stats["nontarget_skip"]
    after_comp = after_nt - stats["competitor_skip"]
    cand = stats["candidates"]
    a = stats["A"]

    def pct(n):
        return f"{n/total*100:.0f}%"

    def step_pct(n, prev):
        return f"{n/max(prev,1)*100:.0f}%"

    rows = [
        ("Search results",        stats["input"], "—", "100%"),
        ("- platforms/directories", after_platform, step_pct(after_platform, stats["input"]), pct(after_platform)),
        ("- duplicate domains",     after_dupdom, step_pct(after_dupdom, after_platform), pct(after_dupdom)),
        ("- already in DB",         after_db, step_pct(after_db, after_dupdom), pct(after_db)),
        ("- non-target terms",      after_nt, step_pct(after_nt, after_db), pct(after_nt)),
        ("- competitor markers",    after_comp, step_pct(after_comp, after_nt), pct(after_comp)),
        ("Candidates entered",      cand, step_pct(cand, after_comp), pct(cand)),
        ("  └ A-tier sendable",     a, step_pct(a, cand), pct(a)),
    ]

    dup_db_rate = stats["dup_in_db_skip"] / total
    named_rate = a / max(cand, 1)
    ratios = {
        "total": total,
        "in_db_rate": dup_db_rate,
        "candidate_rate": cand / total,
        "named_email_rate": named_rate,
        "sendable_rate": a / total,
    }

    diagnostics = []
    if dup_db_rate > FUNNEL_DUP_DB_RED:
        diagnostics.append(
            f"🔴 In-DB duplicate rate {dup_db_rate*100:.0f}% (>{FUNNEL_DUP_DB_RED*100:.0f}%): "
            f"queries mostly hit customers already worked → switch to uncovered regions / product terms / tiers")
    if named_rate < FUNNEL_NAMED_EMAIL_RED and cand > 0:
        diagnostics.append(
            f"🔴 Named-mailbox rate only {named_rate*100:.0f}% (<{FUNNEL_NAMED_EMAIL_RED*100:.0f}%): "
            f"too few directly sendable → run email_guesser on B-tier accounts; do not drop good accounts just because they only show info@")
    if stats["platform_skip"] + stats["nonlead_skip"] > total * 0.5:
        diagnostics.append(
            f"🟡 Platforms/directories share {(stats['platform_skip']+stats['nonlead_skip'])/total*100:.0f}%: "
            f"queries too broad → narrow keywords, add -site:<platform domain> exclusions")
    if stats["nontarget_skip"] > total * 0.3:
        diagnostics.append(
            f"🟡 Non-target hits share {stats['nontarget_skip']/total*100:.0f}%: "
            f"many off-target results → add exclusion terms to profile targeting.exclude_keywords, "
            f"or add -keyword exclusions to the queries")
    if not diagnostics:
        diagnostics.append("✅ Conversion is healthy at every stage; no obvious bottleneck.")
    return rows, diagnostics, ratios


def print_funnel(stats):
    rows, diagnostics, ratios = build_funnel(stats)
    print("\n===== Search funnel diagnostics (conversion) =====")
    print(f"{'Stage':<26}{'Count':>7}{'Step':>10}{'Cumulative':>12}")
    for name, n, step, cum in rows:
        print(f"{name:<14}{n:>7}{step:>10}{cum:>10}")
    print("-------------------------------")
    print(f"Final conversion: entered {ratios['candidate_rate']*100:.0f}% | directly sendable {ratios['sendable_rate']*100:.0f}%")
    print("\n💡 Bottleneck diagnosis and suggestions:")
    for d in diagnostics:
        print(f"  {d}")
    return ratios


def save_funnel_history(state_path, stats, ratios):
    from datetime import datetime as _dt
    state = _load_state(state_path)
    entry = {
        "t": _dt.now().strftime("%Y-%m-%d %H:%M"),
        "input": stats["input"], "candidates": stats["candidates"],
        "A": stats["A"], "in_db_skip": stats["dup_in_db_skip"],
        "candidate_rate": round(ratios["candidate_rate"], 3),
        "sendable_rate": round(ratios["sendable_rate"], 3),
        "in_db_rate": round(ratios["in_db_rate"], 3),
    }
    state.setdefault("funnel_history", []).append(entry)
    _save_state(state_path, state)


# ============================================================
# 7. CLI commands
# ============================================================
def _resolve_regions(cli_regions):
    """--regions on the command line wins; otherwise profile target_regions; refuse if both are empty."""
    if cli_regions:
        return [r.strip() for r in cli_regions.split(",") if r.strip()]
    regs = RUNTIME["regions"]
    if not regs:
        print("ERROR: no target regions. Fill targeting.target_regions in company_profile.json, "
              "or pass --regions USA,UK for this run.")
        sys.exit(2)
    return regs


def _print_level_hint():
    if RUNTIME.get("default_level"):
        print("# Note: the profile defines no targeting.customer_levels; "
              "falling back to a single tier L1_default built from buyer_titles + channel_keywords. "
              "You can define multiple customer tiers in the profile.", file=sys.stderr)


def cmd_queries(args):
    levels = args.levels.split(",") if args.levels else None
    if levels:
        bad = [l for l in levels if l not in RUNTIME["spectrum"]]
        if bad:
            print(f"ERROR: tier {bad} does not exist. Available tiers (profile customer_levels.name): "
                  f"{list(RUNTIME['spectrum'].keys())}")
            sys.exit(2)
    regions = _resolve_regions(args.regions)
    breadth = getattr(args, "breadth", "core") or "core"
    qs = build_queries(spectrum_keys=levels, regions=regions, breadth=breadth)
    out = args.out
    reg_n = len(regions)
    lvl_n = len(levels) if levels else len(RUNTIME["spectrum"])
    cat_n = len(RUNTIME["categories"])
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(qs))
        print(f"OK: generated {len(qs)} queries → {out}  (breadth={breadth}, regions {reg_n}, tiers {lvl_n})")
    else:
        for q in qs:
            print(q)
        anchor_cn = "customer-industry terms" if RUNTIME.get("anchor") == "customer" else "product/service terms"
        print(f"\n# {len(qs)} queries in total (breadth={breadth}: {reg_n} regions × {cat_n} {anchor_cn} × {lvl_n} tiers + flank axes)",
              file=sys.stderr)
        if RUNTIME.get("anchor") == "offer" and RUNTIME.get("offer_type") in ("software", "service"):
            print("# Note: searching with your own category words for software/services tends to find competitors. "
                  "Fill targeting.customer_industries (e.g. logistics / manufacturing) and the script switches to the customer anchor.", file=sys.stderr)
    _print_level_hint()


def cmd_channels(args):
    chans = args.ch if getattr(args, "ch", None) else None
    regions = _resolve_regions(args.regions) if (chans or args.out) else None
    if not chans and not args.out:
        print("===== Customer search channel recipes (new discovery sources) =====")
        rec = set(default_channels())
        print(f"Current delivery type: {RUNTIME.get('offer_type') or 'other'}; ▶ = channels generated by default")
        for key, r in CHANNEL_RECIPES.items():
            mark = "▶" if key in rec else " "
            print(f"\n{mark} [{key}] {r['name']}  {r['star']}")
            print(f"    Use: {r['use']}")
            print(f"    Example query: {r['tmpl'][0]}")
        print("\n# Generate discovery queries:  channels --ch social maps   or   channels --out ch.txt")
        return
    qs = build_channel_queries(channels=chans, regions=regions)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(qs))
        picked = ",".join(chans) if chans else "default channels: " + ",".join(default_channels())
        print(f"OK: generated {len(qs)} channel discovery queries ({picked}) → {args.out}")
    else:
        for q in qs:
            print(q)
        print(f"\n# {len(qs)} channel discovery queries in total", file=sys.stderr)


def cmd_social(args):
    import social_platforms as _sp
    if args.titles:
        for tier, cn in _sp.TIER_CN.items():
            print(f"[{tier}] {cn}: " + " / ".join(_sp.TITLE_TIERS[tier]))
        print("# Profile targeting.buyer_titles are listed before the built-in vocabulary; --tier selects the level.")
        return
    plats = args.platforms or RUNTIME.get("social_platforms") or _sp.PLATFORM_ORDER
    bad = [x for x in plats if x not in _sp.PLATFORMS]
    if bad:
        print(f"ERROR: unknown platform {bad}. Available: {_sp.PLATFORM_ORDER}")
        sys.exit(2)
    if not args.platforms and not args.out and not args.all:
        print("===== 10 overseas social platforms · public search without login (read-only) =====")
        for pid in _sp.PLATFORM_ORDER:
            sp = _sp.PLATFORMS[pid]
            on = "▶" if pid in plats else " "
            print(f"\n{on} [{pid}] {sp['name']}  {sp['star']}  · {sp['stage']}")
            print(f"    Public query: {sp['tmpl'][0]}")
            print(f"    Take from results: {sp['extract']}")
            print(f"    Manual · login required (this skill does not do it): {sp['login']}")
        print("\n# Generate:  social --all   or   social --platforms linkedin instagram --out social.txt")
        print("# Each result → website → named mailbox → filter --against (DB check) → research (S1/S2 evidence) before any sending.")
        return
    regions = _resolve_regions(args.regions)
    titles = _sp.titles_for(args.tier, RUNTIME.get("buyer_titles") or [])
    qs = _sp.build(plats, regions, RUNTIME["categories"], _top_roles(), titles,
                   list(RUNTIME.get("competitors") or []))
    lines = []
    cur = None
    for pid, q in qs:
        if pid != cur:
            sp = _sp.PLATFORMS[pid]
            lines.append(f"# ---- {sp['name']} {sp['star']} · {sp['stage']} · take: {sp['extract']}")
            cur = pid
        lines.append(q)
        if pid == "youtube" and args.urls:
            lines.append("#   " + _sp.youtube_url(q))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"OK: generated {len(qs)} social public queries ({len(plats)} platforms · {len(regions)} regions · tier={args.tier}) → {args.out}")
    else:
        print("\n".join(lines))
        print(f"\n# {len(qs)} queries ({len(plats)} platforms). Read-only public search: no login, no DMs, no auto-connect.", file=sys.stderr)


def cmd_filter(args):
    with open(args.results, "r", encoding="utf-8-sig") as f:
        results = json.load(f)
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    db_index = None
    db_loaded = 0
    if args.against:
        emails_set, domains_set, codes_set, db_loaded = load_customer_db(args.against, since=args.since)
        db_index = (emails_set, domains_set, codes_set)
    else:
        print("=" * 48)
        print("⚠️  You did not pass --against for a DB check. You may be repeating work.")
        print("    These accounts are probably already in your customer DB; skipping the check = wasted search and research.")
        print("    Correct usage:  filter results.json --against customer_db.csv")
        print("=" * 48)

    candidates, stats = filter_and_grade(results, db_index=db_index)

    out = args.out or "candidates.csv"
    fields = ["domain", "url", "brand", "email_grade", "best_email",
              "all_emails", "region_hint", "customer_type_hint", "next_action", "note"]
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(candidates)

    print("===== Search candidate grading =====")
    print(f"Input results              : {stats['input']}")
    if args.against:
        since_txt = f" (recent data ≥{args.since})" if args.since else " (full)"
        print(f"Customer DB compared       : {db_loaded} rows loaded{since_txt}")
        print(f"Already in DB, removed     : {stats['dup_in_db_skip']}  ← avoids re-working existing accounts")
    print(f"Platforms/marketplaces     : {stats['platform_skip']}")
    print(f"Directories/media/gov      : {stats['nonlead_skip']}")
    print(f"Non-target terms           : {stats['nontarget_skip']}  ← profile exclude_keywords")
    print(f"Competitor markers         : {stats['competitor_skip']}  ← profile competitor_markers")
    print(f"Duplicate domains          : {stats['dup_domain_skip']}")
    print(f"-------------------------------")
    print(f"Candidates entered         : {stats['candidates']}")
    print(f"  ├─ A-tier (corporate named mailbox): {stats['A']}")
    print(f"  ├─ B-tier (generic/free mailbox)   : {stats['B']}")
    print(f"  └─ no e-mail (to fill)             : {stats['no_email']}")
    print(f"→ Candidate details written to: {out}")

    ratios = print_funnel(stats)
    save_funnel_history(args.state, stats, ratios)

    print("\nNext: take each A/B candidate through research → non-target review → de-dup, then into the pipeline.")


# ============================================================
# 8. Non-target category review (data quality: flags only, never edits; driven by profile exclusion terms)
# ============================================================
def cmd_audit_exclude(args):
    """Pick records in the candidate CSV that look like non-target / competitor hits, for human confirmation.
    Never changes data automatically (deletion/edits require the owner's approval)."""
    rules = [("exclude_keywords", k) for k in RUNTIME["exclude_keywords"]]
    rules += [("competitor_markers", k) for k in RUNTIME["competitor_markers"]]
    if not rules:
        print("The profile has no targeting.exclude_keywords / competitor_markers, "
              "so there are no industry filter terms to review.")
        print("(Technical filters such as platforms/directories/government/media/free mailboxes are outside this review.)")
        return
    suspicious = []
    with open(args.csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 2):
            blob = " ".join([
                row.get("brand", ""), row.get("customer_type_hint", ""),
                row.get("note", ""), row.get("url", ""), row.get("domain", ""),
            ]).lower()
            hits = [f"{src}:{k}" for src, k in rules if str(k).lower() in blob]
            if hits:
                suspicious.append((i, row.get("brand") or row.get("domain"), hits))
    print(f"===== Non-target / competitor review (scanned {args.csv}) =====")
    if not suspicious:
        print("No suspicious records hit non-target or competitor terms.")
    else:
        print(f"Found {len(suspicious)} suspicious records (please verify by research; this tool does not edit):")
        for ln, brand, hits in suspicious:
            print(f"  row {ln}: {brand} | hits: {', '.join(sorted(set(hits)))}")
        print("\n→ Move confirmed non-targets/competitors to the blacklist or skip them; do not send.")


# ============================================================
# 9. Self-replenishing engine (pool floor + four-axis rotation: height / breadth / depth / reach + built-in scheduler)
# ============================================================
# Four axes (each run takes one level per axis and steps forward; long-run full coverage, never all at once):
#   depth   —— how deep to dig in one market: d1 company-level discovery → d2 decision-maker penetration (procurement-chain titles)
#              → d3 installed-base deep dive (peers of won customers / reference brands, other roles at sent-but-silent accounts); turns fastest,
#              the same region × tier is dug shallow→deep over three consecutive runs, then the next slice.
#   reach   —— market radius: the order of profile.targeting.target_regions is "near → far"
#              (put won / most familiar / closest-time-zone markets first); after one depth cycle, move to the next region.
#   height  —— customer value tier: the order of profile.targeting.customer_levels is "high → low"
#              (high-value / key-account tiers first); after all regions complete one cycle, step down one tier.
#   breadth —— how wide the search is: core combinations → wide (+scene/intent axes) → max (+all flank axes); turns slowest.
DEFAULT_STATE = "search_state.json"
DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
DEFAULT_POOL = os.path.join(DATA_DIR, "customer_db.csv")
DEPTHS = ["d1_company", "d2_decision", "d3_stock"]
BREADTHS = ["core", "wide", "max"]
DIM_LABELS = {"region": "reach", "level": "height", "depth": "depth", "breadth": "breadth"}
# These relations in the customer DB never enter the cold-outreach sendable pool (existing customers go through lifecycle, not cold outreach)
NON_COLD_RELATIONS = {"existing_customer", "do_not_contact", "competitor", "lost_do_not_contact"}


def _load_state(path):
    state = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                state = json.load(f)
        except Exception:
            state = None
    if not isinstance(state, dict):
        state = {}
    # compatibility with v3.0 state files (no depth_idx): fill the field, keep history
    for k, v in (("region_idx", 0), ("level_idx", 0), ("depth_idx", 0), ("breadth_idx", 0),
                 ("run_count", 0), ("last_run", ""), ("history", [])):
        state.setdefault(k, v)
    return state


def _save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _rotate_plan(state):
    """Four-axis stepped rotation: depth (d1/d2/d3, fastest) × reach (regions) × height (tiers) × breadth (core/wide/max, slowest)."""
    regions = RUNTIME["regions"]
    levels = list(RUNTIME["spectrum"].keys())
    r = state["region_idx"] % len(regions)
    l = state["level_idx"] % len(levels)
    d = state.get("depth_idx", 0) % len(DEPTHS)
    b = state["breadth_idx"] % len(BREADTHS)
    return {"region": regions[r], "level": levels[l], "depth": DEPTHS[d], "breadth": BREADTHS[b],
            "region_idx": r, "level_idx": l, "depth_idx": d, "breadth_idx": b}


def _advance_state(state):
    """Depth turns fastest (same market dug d1→d2→d3) → reach (regions near→far) → height (tiers high→low) → breadth (slowest)."""
    regions_n = len(RUNTIME["regions"])
    levels_n = len(RUNTIME["spectrum"])
    state["depth_idx"] = (state.get("depth_idx", 0) + 1) % len(DEPTHS)
    if state["depth_idx"] == 0:
        state["region_idx"] = (state["region_idx"] + 1) % regions_n
        if state["region_idx"] == 0:
            state["level_idx"] = (state["level_idx"] + 1) % levels_n
            if state["level_idx"] == 0:
                state["breadth_idx"] = (state["breadth_idx"] + 1) % len(BREADTHS)
    return state


def _cycle_len():
    return (max(1, len(RUNTIME["regions"])) * max(1, len(RUNTIME["spectrum"]))
            * len(DEPTHS) * len(BREADTHS))


def _read_rows(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _stock_seeds():
    """Seeds for the d3 installed-base deep dive: won customer brands + reference brands + accounts with ≥2 e-mails sent and no reply."""
    won = [r.get("brand", "").strip() for r in _read_rows(os.path.join(DATA_DIR, "success_cases.csv"))]
    refs = list(RUNTIME.get("competitors") or [])
    quiet = []
    for r in _read_rows(os.path.join(DATA_DIR, "sent_history.csv")):
        st = (r.get("status") or "").lower()
        try:
            fu = int(r.get("followup_count") or 0)
        except ValueError:
            fu = 0
        if st in ("sent", "") and fu >= 1 and r.get("brand"):
            quiet.append(r["brand"].strip())

    def _u(seq):
        seen, out = set(), []
        for x in seq:
            k = x.lower()
            if x and k not in seen:
                seen.add(k)
                out.append(x)
        return out
    return _u(won), _u(refs), _u(quiet)


def _depth_titles(limit=8):
    import social_platforms as _sp
    titles = list(RUNTIME.get("buyer_titles") or [])
    titles += _sp.TITLE_TIERS.get("decision", [])[:4] + _sp.TITLE_TIERS.get("execution", [])[:4]
    out, seen = [], set()
    for t in titles:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t.strip())
    return out[:limit]


def build_depth_queries(depth, region, level, breadth):
    """Generate today's queries for the current depth level. Returns (queries, note)."""
    base = build_queries(spectrum_keys=[level], regions=[region], breadth=breadth)
    cats = RUNTIME["categories"][:3]
    if depth == "d1_company":
        return base, "d1 company-level discovery: find the right companies first"
    titles = _depth_titles()
    d2 = []
    for cat in cats:
        for t in titles:
            d2.append(f'site:linkedin.com/in "{t}" {cat} {region}')
            d2.append(f'{region} {cat} "{t}" contact')
    if depth == "d2_decision":
        return _dedup_keep(base[:40] + d2), "d2 decision-maker penetration: find the actual approver/operator inside the known company types"
    won, refs, quiet = _stock_seeds()
    d3 = []
    for seed in (won + refs)[:10]:
        d3 += [f"companies like {seed} {region}", f"{seed} competitors {region}",
               f"{seed} customers OR clients {region}"]
    for brand in quiet[:10]:
        for t in titles[:3]:
            d3.append(f'site:linkedin.com/in "{brand}" "{t}"')
    if not d3:
        return _dedup_keep(base[:40] + d2), ("d3 installed-base deep dive has no seeds yet (no won cases / reference brands / sent-but-silent accounts)"
                                             "→ falling back to d2 for this run; it activates automatically after a DB import or the first win")
    return _dedup_keep(d3 + d2[:20]), "d3 installed-base deep dive: peers of won customers / reference brands + other roles at sent-but-silent accounts"


def _dedup_keep(seq):
    seen, out = set(), []
    for q in seq:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _count_sendable_pool(pool_csv):
    """Count cold-outreach candidates in the customer DB that are sendable now: has e-mail + never sent + not an existing customer / do-not-contact."""
    sendable = 0
    total = 0
    if not os.path.exists(pool_csv):
        return 0, 0
    already = {(r.get("email") or "").strip().lower() for r in _read_rows(os.path.join(DATA_DIR, "sent_history.csv"))}
    with open(pool_csv, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            total += 1
            email = (row.get("email") or "").strip()
            est = (row.get("email_status") or "").strip().lower()
            rel = (row.get("relation") or "").strip().lower()
            sent = est in ("sent", "已发", "replied", "已回复", "bounced", "退信")  # Chinese aliases accepted in imported data
            if email and "@" in email and not sent and rel not in NON_COLD_RELATIONS \
                    and email.lower() not in already:
                sendable += 1
    return sendable, total


def cmd_replenish(args):
    """Pool floor: check whether the sendable pool is below the red line; if so, generate today's search round by four-axis rotation."""
    if not RUNTIME["regions"]:
        print("ERROR: the profile has no targeting.target_regions, so the reach axis (regions) cannot rotate. "
              "Fill the target regions in company_profile.json first (ordered near → far).")
        sys.exit(2)
    floor = args.floor
    daily = args.daily_target
    state = _load_state(args.state)
    sendable, total = _count_sendable_pool(args.pool)

    print("===== Customer pool floor check (self-replenishing engine) =====")
    print(f"Customer DB            : {args.pool}" + ("" if os.path.exists(args.pool) else
          " (missing: run data_import.py at install to import your own customer DB, or declare none in the profile)"))
    print(f"Total rows             : {total}")
    print(f"Sendable cold candidates (has e-mail · never sent · not existing customer): {sendable}")
    print(f"Floor red line         : {floor}   | daily send target: {daily}")

    days_left = sendable // daily if daily else 0
    below_floor = sendable < floor
    below_ahead = days_left < args.ahead_days
    need_replenish = below_floor or below_ahead
    if below_floor:
        print(f"\n[!] Below the hard red line: sendable {sendable} < {floor}, only ~{days_left} days left; replenish now.")
    elif below_ahead:
        print(f"\n[!] Below the advance reserve line: only ~{days_left} days of sending left (< {args.ahead_days} days ahead); replenishing early.")
    else:
        print(f"\n[OK] Pool is sufficient: supports ~{days_left} days of sending.")

    plan = _rotate_plan(state)
    if need_replenish or args.force:
        qs, note = build_depth_queries(plan["depth"], plan["region"], plan["level"], plan["breadth"])
        print(f"\n[Today's four-axis rotation] reach={plan['region']} × height={plan['level']} × "
              f"depth={plan['depth']} × breadth={plan['breadth']}")
        print(f"  {note}")
        print(f"Generated {len(qs)} queries (stepped four-axis rotation, no repeats; one full cycle = {_cycle_len()} runs)")
        if args.emit:
            with open(args.emit, "w", encoding="utf-8") as f:
                f.write("\n".join(qs))
            print(f"→ Today's queries written to: {args.emit}")
        print("  Next: after collecting results, run filter --against this DB (de-dup + grading) → non-target review → research → pipeline.")
        from datetime import datetime as _dt
        state["run_count"] += 1
        state["last_run"] = _dt.now().strftime("%Y-%m-%d %H:%M")
        state["history"] = (state.get("history", []) + [
            {"t": state["last_run"], "region": plan["region"], "level": plan["level"],
             "depth": plan["depth"], "breadth": plan["breadth"],
             "queries": len(qs), "sendable_before": sendable}])[-60:]
        _advance_state(state)
        _save_state(args.state, state)
    else:
        print("\nNo replenishment needed today (add --force to rotate the search anyway).")

    if need_replenish and args.warn_file:
        reason = f"sendable {sendable} < hard red line {floor}" if below_floor else f"only {days_left} days left < {args.ahead_days} days ahead"
        with open(args.warn_file, "w", encoding="utf-8") as f:
            f.write(f"[{state.get('last_run','')}] Customer pool floor warning: {reason}. Replenishment rotation triggered.")
        print(f"→ Warning written to: {args.warn_file}")
    _print_level_hint()


def cmd_status(args):
    """Show four-axis rotation progress: where the next run goes + history."""
    if not RUNTIME["regions"]:
        print("ERROR: the profile has no targeting.target_regions; no rotation plan.")
        sys.exit(2)
    state = _load_state(args.state)
    plan = _rotate_plan(state)
    print("===== Four-axis rotation progress (height / breadth / depth / reach) =====")
    print(f"Runs so far       : {state.get('run_count',0)}   | one full cycle = {_cycle_len()} runs")
    print(f"Last run          : {state.get('last_run','') or 'never'}")
    print(f"Next run          : reach={plan['region']} × height={plan['level']} × "
          f"depth={plan['depth']} × breadth={plan['breadth']}")
    print(f"Reach ladder      : {' → '.join(RUNTIME['regions'])} (profile order = near → far)")
    print(f"Height ladder     : {' → '.join(RUNTIME['spectrum'].keys())} (profile order = high → low)")
    print(f"Depth ladder      : {' → '.join(DEPTHS)} (turns fastest: three levels in the same market)")
    print(f"Breadth ladder    : {' → '.join(BREADTHS)}")
    hist = state.get("history", [])
    if hist:
        print("\nLast 8 rotations:")
        for h in hist[-8:]:
            print(f"  {h['t']}  {h['region']:<10} {h['level']:<14} {h.get('depth','d1_company'):<12} "
                  f"{h['breadth']:<5} → {h['queries']} queries (sendable at the time: {h.get('sendable_before','?')})")
    else:
        print("\nNo rotation history yet. Run replenish or schedule first.")
    _print_level_hint()


# ============================================================
# Mutually exclusive tag groups: within one field these values cannot coexist; old ≠ new = conflict.
# variant_tag is a generalised product-variant tag (meaning defined by the user);
# need_tag is the customer-need tag.
# No industry exclusivity is pre-set; it is defined by profile.positioning.conflict_groups, e.g.
#   {"need_tag": [["line_a"], ["line_b"]], "variant_tag": [["variant_a"], ["variant_b"]]}
# Fields not defined there: any old/new difference is flagged (still flag-only, never edited).
CONFLICT_GROUPS = {"need_tag": [], "variant_tag": [], "solution_tag": []}


def _load_conflict_config():
    pos = RUNTIME.get("positioning") or {}
    groups = dict(CONFLICT_GROUPS)
    for fld, gs in (pos.get("conflict_groups") or {}).items():
        groups[fld] = [set(_norm_tag(x) for x in g) for g in gs if g]
    rules = [r for r in (pos.get("tag_rules") or []) if isinstance(r, dict)]
    return groups, rules


def _norm_tag(v):
    return (v or "").strip().lower()


def _tags_conflict(field, old, new):
    """Decide whether the old tag and the new research conclusion for the same field contradict each other.
    Both non-empty, different, and in different exclusive groups → conflict. need_review / empty never counts."""
    o, n = _norm_tag(old), _norm_tag(new)
    if not o or not n or o == n:
        return False
    if n in ("review", "need_review", "unknown"):
        return False
    groups = CONFLICT_GROUPS.get(field)
    if groups:
        for ga in groups:
            for gb in groups:
                if ga is not gb and o in ga and n in gb:
                    return True
    return o != n


def _load_db_rows(csv_path, since=None):
    """Load full customer DB rows and index email/domain/customer_code → row (old tags kept for comparison)."""
    by_email, by_domain, by_code = {}, {}, {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if since:
                ts = (row.get("updated_at") or row.get("created_at") or "")[:10]
                if ts and ts < since:
                    continue
            em = (row.get("email") or "").strip().lower()
            if em:
                by_email.setdefault(em, row)
            web = row.get("website") or row.get("domain") or ""
            dom = domain_of(web) if "//" in web else web.strip().lower().replace("www.", "")
            if dom:
                by_domain.setdefault(dom, row)
            code = (row.get("customer_code") or "").strip()
            if code:
                by_code.setdefault(code, row)
    return by_email, by_domain, by_code


def _match_db_row(new_rec, by_email, by_domain, by_code):
    """Find the old row of the same customer in the DB, by email → domain → customer_code."""
    direct = (new_rec.get("email") or "").strip().lower()
    cand_emails = ([direct] if direct else []) + extract_emails(new_rec)
    for e in cand_emails:
        if e in by_email:
            return by_email[e]
    web = new_rec.get("website") or new_rec.get("domain") or new_rec.get("url") or ""
    dom = domain_of(web) if "//" in web else web.strip().lower().replace("www.", "")
    if dom and dom in by_domain:
        return by_domain[dom]
    code = (new_rec.get("customer_code") or "").strip()
    if code and code in by_code:
        return by_code[code]
    return None


def cmd_conflict_check(args):
    """Tag conflict check: new research conclusion vs. old tag in the DB.
    Two modes:
      (A) with --new: compare a new research-conclusion file (JSON/CSV with variant_tag/need_tag)
          against the --against DB row by row, and find customers whose old and new tags contradict.
      (B) without --new: scan the --against DB alone for internal variant_tag vs need_tag contradictions.
    Always flag-only: outputs a conflict list for human sign-off (AI suggests, a human decides)."""
    by_email, by_domain, by_code = _load_db_rows(args.against, since=args.since)
    db_rows = list({id(r): r for r in list(by_email.values())
                    + list(by_domain.values()) + list(by_code.values())}.values())
    conflicts = []
    groups, rules = _load_conflict_config()
    CONFLICT_GROUPS.update(groups)
    fields = list(CONFLICT_GROUPS.keys())

    if args.new:
        if args.new.lower().endswith(".json"):
            with open(args.new, "r", encoding="utf-8-sig") as f:
                new_data = json.load(f)
            if isinstance(new_data, dict) and "results" in new_data:
                new_data = new_data["results"]
        else:
            with open(args.new, "r", encoding="utf-8-sig", newline="") as f:
                new_data = list(csv.DictReader(f))
        for rec in new_data:
            old_row = _match_db_row(rec, by_email, by_domain, by_code)
            if not old_row:
                continue
            name = rec.get("brand") or old_row.get("brand") or old_row.get("customer_name") or "?"
            for fld in fields:
                new_v = rec.get(fld)
                old_v = old_row.get(fld)
                if _tags_conflict(fld, old_v, new_v):
                    conflicts.append((name, fld, old_v, new_v,
                                      "new research conclusion contradicts the old tag in the DB"))
    else:
        # Internal consistency check: all rules come from profile.positioning.tag_rules; no industry rules are built in
        if not rules:
            print("ℹ️  profile.positioning.tag_rules is not configured: no rules for the internal check; "
                  "only the --new old-vs-new comparison is possible.")
        for row in db_rows:
            name = row.get("brand") or row.get("customer_name") or "?"
            for r in rules:
                a = _norm_tag(row.get(r.get("if_field", "")))
                bval = _norm_tag(row.get(r.get("forbid_field", "")))
                if a and a == _norm_tag(r.get("equals")) and bval in {_norm_tag(x) for x in r.get("values", [])}:
                    conflicts.append((name, f"{r['if_field']}×{r['forbid_field']}", f"{r['if_field']}={a}",
                                      f"{r['forbid_field']}={bval}", r.get("reason") or "violates tag_rules"))
    print("=" * 52)
    print("Tag conflict check: research conclusion vs. old tag in the DB (flag only, never edit)")
    print("=" * 52)
    if not conflicts:
        print("✅ No tag conflicts found.")
    else:
        print(f"⚠️  Found {len(conflicts)} tag conflicts (this tool never edits automatically; verify by research and decide):\n")
        for name, fld, old_v, new_v, why in conflicts:
            print(f"  ▸ {name} | {fld}: old=[{old_v or 'empty'}] ≠ new=[{new_v or 'empty'}] → {why}")
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "field", "old_tag", "new_tag", "reason", "decision"])
                for name, fld, old_v, new_v, why in conflicts:
                    w.writerow([name, fld, old_v, new_v, why, "pending_human_decision"])
            print(f"\n→ Conflict list written to: {args.out} (decision column left empty; write back only after each case is decided)")
    print("\nPrinciple: tag conflicts are flagged, never auto-edited; AI suggests, a human makes the final call.")


def cmd_funnel(args):
    """Show the cumulative conversion trend across past searches (is search efficiency improving?)."""
    state = _load_state(args.state)
    hist = state.get("funnel_history", [])
    if not hist:
        print("No funnel history yet. Run filter (with --against) a few times to collect data.")
        return
    print("===== Search funnel conversion trend =====")
    print(f"{'Time':<18}{'Input':>6}{'Entered':>8}{'Entry%':>8}{'Sendable%':>10}{'DB dup%':>9}")
    for h in hist[-15:]:
        print(f"{h['t']:<18}{h['input']:>6}{h['candidates']:>6}"
              f"{h['candidate_rate']*100:>7.0f}%{h['sendable_rate']*100:>8.0f}%{h['in_db_rate']*100:>8.0f}%")
    n = len(hist)
    avg_cand = sum(h["candidate_rate"] for h in hist) / n
    avg_send = sum(h["sendable_rate"] for h in hist) / n
    avg_db = sum(h["in_db_rate"] for h in hist) / n
    print("-" * 56)
    print(f"{'Average':<18}{'':>6}{'':>8}{avg_cand*100:>7.0f}%{avg_send*100:>9.0f}%{avg_db*100:>8.0f}%")
    print("\n💡 Trend reading:")
    if avg_db > FUNNEL_DUP_DB_RED:
        print(f"  🔴 Average DB duplicate rate {avg_db*100:.0f}% is high → queries keep hitting worked territory; move to new regions / product terms.")
    if avg_send < FUNNEL_NAMED_EMAIL_RED:
        print(f"  🔴 Average sendable rate {avg_send*100:.0f}% is low → named mailboxes are chronically short; lean on email_guesser.")
    if avg_db <= FUNNEL_DUP_DB_RED and avg_send >= FUNNEL_NAMED_EMAIL_RED:
        print("  ✅ Historical conversion is healthy.")


def cmd_schedule(args):
    import time
    from datetime import datetime as _dt

    class _Args:
        pool = args.pool
        floor = args.floor
        daily_target = args.daily_target
        ahead_days = args.ahead_days
        state = args.state
        emit = args.emit
        warn_file = args.warn_file
        force = True

    def _job():
        print(f"\n⏰ [{_dt.now().strftime('%Y-%m-%d %H:%M')}] Self-replenishing run: check pool → replenish → rotate")
        cmd_replenish(_Args())

    print("===== Built-in scheduler started (self-replenishing engine) =====")
    print(f"Runs the replenish loop daily at {args.at} | floor red line {args.floor} | DB {args.pool}")
    print("Ctrl+C to stop. Runs once immediately on start.\n")
    _job()
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
        hh, mm = args.at.split(":")
        sched = BlockingScheduler()
        sched.add_job(_job, "cron", hour=int(hh), minute=int(mm))
        print("(using APScheduler cron)")
        sched.start()
    except ImportError:
        print("(APScheduler not installed; using a zero-dependency sleep loop; pip install apscheduler to upgrade)")
        last_day = _dt.now().strftime("%Y-%m-%d")
        target_h, target_m = map(int, args.at.split(":"))
        while True:
            time.sleep(60)
            now = _dt.now()
            today = now.strftime("%Y-%m-%d")
            if today != last_day and (now.hour, now.minute) >= (target_h, target_m):
                last_day = today
                _job()


def _build_parser():
    p = argparse.ArgumentParser(
        description="Industry-agnostic B2B customer search candidate generator + self-replenishing engine (skill v3.1 · profile-driven)")
    sub = p.add_subparsers(dest="cmd")

    pq = sub.add_parser("queries", help="Generate the full query set (product terms × tier role terms × regions; vocabulary from the profile)")
    pq.add_argument("--out")
    pq.add_argument("--levels", help="Only some tiers, comma-separated; names from profile customer_levels[].name")
    pq.add_argument("--regions", help="Only some regions, comma-separated; default = profile target_regions")
    pq.add_argument("--breadth", choices=["core", "wide", "max"], default="core")
    pq.set_defaults(func=cmd_queries)

    pc = sub.add_parser("channels", help="New discovery sources: generate discovery queries per channel (social/maps/customs/tenders/hiring/directories/reviews/events/competitors…); default picks channels by industry pack / delivery type")
    pc.add_argument("--ch", nargs="+",
                    choices=list(CHANNEL_RECIPES.keys()),
                    help="Only the given channels (leave empty to list all channel descriptions)")
    pc.add_argument("--regions", help="Only some regions, comma-separated")
    pc.add_argument("--out")
    pc.set_defaults(func=cmd_channels)

    pso = sub.add_parser("social", help="Public search queries for 10 social platforms without login (LinkedIn/IG/FB/YouTube/TikTok/Pinterest/X/Threads/WhatsApp/Lemon8)")
    pso.add_argument("--platforms", nargs="+", help="Only the given platforms (default = profile search.social_platforms, else all 10)")
    pso.add_argument("--all", action="store_true", help="Generate for all 10 platforms")
    pso.add_argument("--tier", choices=["decision", "execution", "influence", "all"], default="all",
                     help="Job-title level: decision / execution / influence (for LinkedIn boolean queries)")
    pso.add_argument("--regions", help="Only some regions, comma-separated")
    pso.add_argument("--titles", action="store_true", help="Print only the 30 procurement-chain job titles")
    pso.add_argument("--urls", action="store_true", help="Also output YouTube on-site search links (public pages, no login)")
    pso.add_argument("--out")
    pso.set_defaults(func=cmd_social)

    pf = sub.add_parser("filter", help="Filter + incremental DB de-dup + domain de-dup + non-target/competitor gate + grading")
    pf.add_argument("results")
    pf.add_argument("--out")
    pf.add_argument("--against", help="Customer DB CSV (check the DB before working a lead)")
    pf.add_argument("--since", help="Only compare DB rows from this date on")
    pf.add_argument("--state", default=DEFAULT_STATE, help="State file (stores funnel history)")
    pf.set_defaults(func=cmd_filter)

    # Tag conflict check: new research conclusion vs. old DB tag (flag only, human decides)
    pcc = sub.add_parser("conflict-check", help="Conflict check: new research conclusion vs. old tag in the DB (flag only, human sign-off)")
    pcc.add_argument("--against", required=True, help="Customer DB CSV path (source of old tags)")
    pcc.add_argument("--new", help="New research-conclusion file (JSON/CSV with need_tag/solution_tag/variant_tag); omit to scan the DB for internal contradictions per profile.positioning.tag_rules")
    pcc.add_argument("--since", help="Only compare DB rows with updated_at/created_at ≥ this date (YYYY-MM-DD)")
    pcc.add_argument("--out", help="Write the conflict list to CSV (decision column = pending_human_decision)")
    pcc.set_defaults(func=cmd_conflict_check)

    pfn = sub.add_parser("funnel", help="Cumulative conversion trend of past searches + bottleneck diagnosis")
    pfn.add_argument("--state", default=DEFAULT_STATE)
    pfn.set_defaults(func=cmd_funnel)

    pa = sub.add_parser("audit-exclude", aliases=["audit-category"],
                        help="Non-target / competitor review (pick suspicious rows by profile exclusion terms; never edits)")
    pa.add_argument("csv", help="Candidate / customer DB CSV path")
    pa.set_defaults(func=cmd_audit_exclude)

    pr = sub.add_parser("replenish", help="Pool floor: when the pool is below the red line, generate today's queries by four-axis rotation (height/breadth/depth/reach) + warning")
    pr.add_argument("--pool", default=DEFAULT_POOL, help="Customer DB CSV (default $B2B_DATA_DIR/customer_db.csv, produced by data_import.py)")
    pr.add_argument("--floor", type=int, default=100, help="Hard floor red line, default 100")
    pr.add_argument("--daily-target", type=int, default=100, dest="daily_target")
    pr.add_argument("--ahead-days", type=int, default=30, dest="ahead_days")
    pr.add_argument("--state", default=DEFAULT_STATE)
    pr.add_argument("--emit", help="Write today's queries to a file")
    pr.add_argument("--warn-file", dest="warn_file")
    pr.add_argument("--force", action="store_true")
    pr.set_defaults(func=cmd_replenish)

    ps = sub.add_parser("schedule", help="Built-in scheduler: resident process that runs the replenish loop daily at a fixed time")
    ps.add_argument("--pool", default=DEFAULT_POOL)
    ps.add_argument("--at", default="09:00")
    ps.add_argument("--floor", type=int, default=100)
    ps.add_argument("--daily-target", type=int, default=100, dest="daily_target")
    ps.add_argument("--ahead-days", type=int, default=30, dest="ahead_days")
    ps.add_argument("--state", default=DEFAULT_STATE)
    ps.add_argument("--emit", default="queries_today.txt")
    ps.add_argument("--warn-file", dest="warn_file", default="pool_warning.txt")
    ps.set_defaults(func=cmd_schedule)

    pst = sub.add_parser("status", help="Show four-axis rotation progress (height/breadth/depth/reach)")
    pst.add_argument("--state", default=DEFAULT_STATE)
    pst.set_defaults(func=cmd_status)

    return p


def main():
    p = _build_parser()
    args = p.parse_args()  # -h/--help prints usage and exits here; no profile needed
    if not getattr(args, "cmd", None):
        p.print_help()
        sys.exit(0)

    # Config gate: every business sub-command needs a complete company profile first
    if _cfg is None:
        print("ERROR: config.py gate not found; refusing to run.")
        sys.exit(2)
    try:
        profile = _cfg.load_profile(require_complete=True)
    except _cfg.ProfileNotConfigured as e:
        print("ERROR: company profile not ready; execution blocked.\n" + str(e))
        sys.exit(2)

    RUNTIME.update(build_profile_context(profile))
    args.func(args)


if __name__ == "__main__":
    main()
