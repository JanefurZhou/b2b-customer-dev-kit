#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_platforms.py — public, login-free search recipes for 10 overseas social platforms + a 30-title procurement-chain vocabulary (three tiers)

Does one thing: generates public search queries (site: operator) you can paste straight into Google / Bing,
to find target companies / decision-maker profiles / industry groups / comment-section signals on pages the search engines have already indexed.
- No login, no sign-up, no platform API calls, no automatic friend requests / DMs / group joins / follows.
- Anything that needs a login (connection requests, DMs, joining groups, viewing follower lists) is listed as "manual · login required";
  this skill does not perform it and only documents the method in references/social_media_playbooks.md.
- Every result still goes through: official website → named mailbox → filter --against de-dup → background research (S1/S2 evidence).

Called by the search_customers.py social sub-command; can also be imported on its own.
Standard library only.
"""

from urllib.parse import quote_plus
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------- Procurement-chain titles: decision / execution / influence tiers, 10 each ----------------
TITLE_TIERS = {
    "decision": [  # sign off, approve budget
        "Owner", "Founder", "CEO", "Managing Director", "General Manager",
        "Head of Purchasing", "Procurement Director", "VP Operations",
        "Commercial Director", "Category Director",
    ],
    "execution": [  # actually source suppliers, compare prices, place orders
        "Buyer", "Senior Buyer", "Purchasing Manager", "Procurement Manager",
        "Sourcing Manager", "Category Manager", "Supply Chain Manager",
        "Product Manager", "Merchandiser", "Vendor Manager",
    ],
    "influence": [  # raise needs, evaluate, influence selection
        "Operations Manager", "Quality Manager", "Technical Director",
        "Engineering Manager", "Project Manager", "Product Development Manager",
        "Brand Manager", "Marketing Manager", "IT Manager", "Office Manager",
    ],
}
TIER_CN = {"decision": "decision tier", "execution": "execution tier", "influence": "influence tier"}

# ---------------- 10-platform recipes ----------------
# tmpl placeholders: {cat} category / customer-industry term · {role} role term · {region} region · {t3} OR group of three titles
#           {tag} hashtag term (derived from the category term) · {competitor} reference / competitor brand
PLATFORMS = {
    "linkedin": {
        "name": "LinkedIn", "star": "⭐⭐⭐⭐⭐", "stage": "find decision makers",
        "tmpl": [
            'site:linkedin.com/in ({t3}) "{cat}" "{region}"',
            'site:linkedin.com/company "{cat}" {role} "{region}"',
            'site:linkedin.com/posts "{cat}" ("looking for" OR sourcing OR RFQ OR tender) "{region}"',
        ],
        "extract": "name, title, company name, company website (company page About); procurement / tender signals in posts",
        "login": "connection requests, InMail, full profile view, Sales Navigator filters",
    },
    "instagram": {
        "name": "Instagram", "star": "⭐⭐⭐⭐", "stage": "find brands / stores",
        "tmpl": [
            'site:instagram.com "{cat}" ({role} OR stockist OR wholesale OR distributor) "{region}"',
            'site:instagram.com "#{tag}" "{region}"',
            'site:instagram.com "{competitor}" (stockist OR retailer OR "available at" OR partner)',
        ],
        "extract": "website link in the bio, Email button text, city; whether stockist/wholesale is mentioned",
        "login": "viewing follower/following lists, scrolling hashtag pages, DMs, likes and comments",
    },
    "facebook": {
        "name": "Facebook", "star": "⭐⭐⭐", "stage": "find groups / business pages",
        "tmpl": [
            'site:facebook.com/groups "{cat}" (buyers OR wholesale OR B2B OR procurement OR sourcing) "{region}"',
            'site:facebook.com "{cat}" {role} "{region}" (email OR contact)',
        ],
        "extract": "public group names and topics (where buyers gather), website / e-mail / address in the business page About",
        "login": "joining groups, posting in groups, Messenger DMs",
    },
    "youtube": {
        "name": "YouTube", "star": "⭐⭐⭐", "stage": "buyers from comments / channels",
        "tmpl": [
            'site:youtube.com "{cat}" (review OR unboxing OR "how to choose" OR "factory tour" OR demo) "{region}"',
            'site:youtube.com "{cat}" {role}',
        ],
        "url": "https://www.youtube.com/results?search_query={q}",
        "extract": "business-enquiry e-mail in the channel About, channel website link; industry / region in video titles; self-identified buyers in comments",
        "login": "commenting, subscribing, community-post interaction",
    },
    "tiktok": {
        "name": "TikTok", "star": "⭐⭐⭐", "stage": "short-video / comment signals",
        "tmpl": [
            'site:tiktok.com "{cat}" (wholesale OR supplier OR "small business" OR {role}) "{region}"',
            'site:tiktok.com "#{tag}"',
        ],
        "extract": "website link in the bio, brand name; accounts asking \"where to source / supplier\" in comments",
        "login": "commenting, DMs, following",
    },
    "pinterest": {
        "name": "Pinterest", "star": "⭐⭐⭐", "stage": "boards / long-tail brand discovery",
        "tmpl": [
            'site:pinterest.com "{cat}" (wholesale OR catalog OR lookbook OR supplier OR {role})',
        ],
        "extract": "external domain the Pin points to (real brand / store website), sub-category in board names",
        "login": "saving, following, DMs",
    },
    "x": {
        "name": "X (Twitter)", "star": "⭐⭐", "stage": "listening for need conversations",
        "tmpl": [
            'site:x.com "{cat}" ("looking for" OR "recommend a" OR supplier OR vendor OR RFQ) "{region}"',
        ],
        "extract": "accounts posting needs and the website in their bio; company accounts under industry conference / trade-show hashtags",
        "login": "replying, DMs, following",
    },
    "threads": {
        "name": "Threads", "star": "⭐⭐", "stage": "linked with IG",
        "tmpl": [
            'site:threads.net "{cat}" ({role} OR supplier OR wholesale OR sourcing)',
        ],
        "extract": "account name (usually the same as IG; go back to the public IG page for the website)",
        "login": "replying, DMs",
    },
    "whatsapp": {
        "name": "WhatsApp", "star": "⭐⭐⭐⭐", "stage": "conversion / follow-up home base (not a search source)",
        "tmpl": [
            '"{cat}" {role} "{region}" ("wa.me" OR "WhatsApp Business" OR "WhatsApp us")',
        ],
        "extract": "WhatsApp business numbers published on websites / directories (record only, do not message yet; enter the WA list via the Step 7 WhatsApp Trigger conditions)",
        "login": "every sending action goes through the wa_bulk engine's human confirmation + anti-ban iron rules",
    },
    "lemon8": {
        "name": "Lemon8", "star": "⭐⭐", "stage": "visual posts / emerging brands",
        "tmpl": [
            'site:lemon8-app.com "{cat}" "{region}"',
        ],
        "extract": "brand / store names mentioned in posts → search back for the website",
        "login": "commenting, DMs, following",
    },
}
PLATFORM_ORDER = list(PLATFORMS.keys())


TAG_SUFFIXES = ("", "wholesale", "supplier", "b2b", "store", "brand", "design", "trade")


def tag_terms(cat, region=""):
    """Category term → 9 hashtag groups: #category / #categorywholesale / supplier / b2b / store / brand / design / trade / #regioncategory"""
    base = "".join(ch for ch in cat.lower() if ch.isalnum())
    if not base:
        return []
    tags = [base + suf for suf in TAG_SUFFIXES]
    reg = "".join(ch for ch in (region or "").lower() if ch.isalnum())
    if reg:
        tags.append(reg + base)
    return tags


def titles_for(tier="all", profile_titles=None):
    """Profile buyer_titles first; the vocabulary fills the gaps. tier=decision/execution/influence/all"""
    lib = []
    tiers = TIER_CN.keys() if tier in ("", "all", None) else [tier]
    for t in tiers:
        lib += TITLE_TIERS.get(t, [])
    out, seen = [], set()
    for t in list(profile_titles or []) + lib:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t.strip())
    return out


def build(platforms, regions, cats, roles, titles, competitors, max_cats=3, max_roles=2, max_tags=9):
    """Return [(platform_id, query)], de-duplicated."""
    out, seen = [], set()
    cats = [c for c in cats if c][:max_cats] or [""]
    roles = [r for r in roles if r][:max_roles] or [""]
    t3_groups = []
    for i in range(0, min(len(titles), 9), 3):
        grp = titles[i:i + 3]
        if grp:
            t3_groups.append(" OR ".join(f'"{t}"' for t in grp))
    t3_groups = t3_groups or ['"Buyer" OR "Purchasing Manager" OR "Owner"']
    for pid in platforms:
        spec = PLATFORMS.get(pid)
        if not spec:
            continue
        for tmpl in spec["tmpl"]:
            if "{competitor}" in tmpl:
                for comp in competitors[:6]:
                    out.append((pid, tmpl.format(competitor=comp)))
                continue
            for region in regions:
                for cat in cats:
                    tags = tag_terms(cat, region) if "{tag}" in tmpl else [""]
                    groups = t3_groups if "{t3}" in tmpl else [""]
                    rls = roles if "{role}" in tmpl else [""]
                    for tag in tags[:max_tags]:
                        for g in groups:
                            for role in rls:
                                out.append((pid, tmpl.format(cat=cat, role=role, region=region,
                                                             t3=g, tag=tag, competitor="")))
    uniq = []
    for pid, q in out:
        q = " ".join(q.split())
        if (pid, q) not in seen:
            seen.add((pid, q))
            uniq.append((pid, q))
    return uniq


def youtube_url(query):
    return PLATFORMS["youtube"]["url"].format(q=quote_plus(query.replace("site:youtube.com", "").strip()))
