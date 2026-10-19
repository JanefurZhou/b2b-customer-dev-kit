#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crm_sync.py — customer DB ⇄ CRM two-way sync (skill v3.1)

Three paths (choose by what you have)
----------------------------
  Path 1 · CSV export / import (works with any CRM, no setup)
      export --target <crm>  export customer_db + send/reply/bounce status with column names that CRM's import wizard maps easily
      pull <crm_export.csv>  pull stage / owner / relation edited by humans in the CRM back into the local customer DB
  Path 2 · HubSpot official API (when you have a private-app token)
      push-hubspot           batch upsert contacts (email as the unique key); DRY_RUN by default,
                             a real push requires CRM_PUSH=1 and HUBSPOT_TOKEN
  Path 3 · MCP (when the runtime supports MCP)
      mcp-payload            generate reports/crm_mcp_payload.json for the AI to create/update records one by one
                             through the CRM's MCP service (e.g. HubSpot's official remote MCP: https://mcp.hubspot.com),
                             with human confirmation before execution

target options: hubspot / salesforce / okki / fumeng / generic
  hubspot / salesforce use the English column names common in their import wizards; okki / fumeng / generic use generic Chinese column names
  (those CRMs are Chinese-language products); map the fields once in the target system's import wizard (its current template wins).
Keys live only in environment variables (HUBSPOT_TOKEN) and are never written to a file. Zero third-party dependencies.
"""

import os
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import csv
import json
import argparse
import datetime
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_import as _di  # noqa: E402

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")

EN_COLS = [("Email", "email"), ("First Name", "_first"), ("Last Name", "_last"),
           ("Company Name", "brand"), ("Job Title", "title"), ("Website URL", "website"),
           ("Country/Region", "region"), ("Phone Number", "phone"), ("Lead Status", "_lead_status"),
           ("Lifecycle Stage", "_lifecycle"), ("Contact Owner", "owner"), ("Notes", "_note")]
SF_COLS = [("Email", "email"), ("First Name", "_first"), ("Last Name", "_last"),
           ("Company", "brand"), ("Title", "title"), ("Website", "website"), ("Country", "region"),
           ("Phone", "phone"), ("Lead Status", "_lead_status"), ("Lead Source", "_source"),
           ("Description", "_note")]
# Generic English columns (any CRM import wizard)
GENERIC_COLS = [("Email", "email"), ("Contact", "contact_person"), ("Company", "brand"), ("Title", "title"),
                ("Website", "website"), ("Country/Region", "region"), ("Phone", "phone"), ("WhatsApp", "whatsapp"),
                ("Relation", "_relation_en"), ("Stage", "_lead_status_en"), ("Owner", "owner"),
                ("Last Contact", "last_contact_date"), ("Source", "_source"), ("Notes", "_note")]
# Chinese column names for Chinese-language trade CRMs (OKKI / Fumeng); kept in Chinese on purpose
CN_COLS = [("邮箱", "email"), ("联系人", "contact_person"), ("公司名称", "brand"), ("职位", "title"),
           ("官网", "website"), ("国家/地区", "region"), ("电话", "phone"), ("WhatsApp", "whatsapp"),
           ("客户类型", "_relation_cn"), ("跟进阶段", "_lead_status_cn"), ("负责人", "owner"),
           ("最近联系", "last_contact_date"), ("来源", "_source"), ("备注", "_note")]
TARGETS = {"hubspot": EN_COLS, "salesforce": SF_COLS, "okki": CN_COLS, "fumeng": CN_COLS, "generic": GENERIC_COLS}

REL_CN = {"existing_customer": "老客户", "prospect": "潜在客户", "lost": "流失客户",
          "do_not_contact": "禁止联系", "competitor": "同行"}
REL_EN = {"existing_customer": "Existing customer", "prospect": "Prospect", "lost": "Lost customer",
          "do_not_contact": "Do not contact", "competitor": "Competitor"}
STATUS_EN = {"new": "Not contacted", "sent": "Emailed", "replied": "Replied", "bounced": "Bounced",
             "wa": "Moved to WhatsApp", "won": "Won"}
STATUS_CN = {"new": "未联系", "sent": "已发信", "replied": "已回复", "bounced": "退信",
             "wa": "转WhatsApp", "won": "成交"}
# HubSpot's 8 default hs_lead_status values: NEW/OPEN/IN_PROGRESS/OPEN_DEAL/UNQUALIFIED/ATTEMPTED_TO_CONTACT/CONNECTED/BAD_TIMING;
# if your portal has customised the options, adjust accordingly (or remap in the import wizard).
STATUS_HS = {"new": "NEW", "sent": "ATTEMPTED_TO_CONTACT", "replied": "CONNECTED",
             "bounced": "UNQUALIFIED", "wa": "IN_PROGRESS", "won": "OPEN_DEAL"}


def _status_index():
    """email → latest outreach status (sent_history + success_cases + wa_contacts)."""
    idx = {}
    for r in _di.load_db(os.path.join(DATA_DIR, "sent_history.csv")):
        e = (r.get("email") or "").lower()
        st = (r.get("status") or "sent").lower()
        if e:
            idx[e] = {"replied": "replied", "bounced": "bounced", "wa_only": "wa"}.get(st, "sent")
    for r in _di.load_db(os.path.join(DATA_DIR, "success_cases.csv")):
        e = (r.get("email") or "").lower()
        if e:
            idx[e] = "won"
    return idx


def _split(name):
    parts = (name or "").strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def _rows_for_export(only_changed_since=None):
    db = _di.load_db(os.path.join(DATA_DIR, _di.DB_NAME))
    st = _status_index()
    out = []
    for r in db:
        if only_changed_since and (r.get("updated_at") or "") < only_changed_since:
            continue
        e = (r.get("email") or "").lower()
        status = st.get(e, (r.get("email_status") or "new").lower() or "new")
        if status not in STATUS_CN:
            status = "sent"
        f, l = _split(r.get("contact_person"))
        rr = dict(r)
        rr.update({"_first": f, "_last": l, "_status": status,
                   "_lead_status": ("UNQUALIFIED" if r.get("relation") in ("do_not_contact", "competitor")
                                    else STATUS_HS.get(status, "NEW")),
                   "_lifecycle": "customer" if (r.get("relation") == "existing_customer" or status == "won") else "lead",
                   "_relation_cn": REL_CN.get(r.get("relation", ""), r.get("relation", "")),
                   "_lead_status_cn": STATUS_CN[status],
                   "_relation_en": REL_EN.get(r.get("relation", ""), r.get("relation", "")),
                   "_lead_status_en": STATUS_EN[status],
                   "_source": r.get("source", ""),
                   "_note": r.get("notes", "")})
        out.append(rr)
    return out


def cmd_export(a):
    cols = TARGETS[a.target]
    rows = _rows_for_export(a.since)
    path = a.out or os.path.join("reports", f"crm_export_{a.target}_{datetime.date.today().isoformat()}.csv")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    enc = "utf-8-sig" if cols is CN_COLS else "utf-8"
    with open(path, "w", encoding=enc, newline="") as f:
        w = csv.writer(f)
        w.writerow([c for c, _ in cols])
        for r in rows:
            w.writerow([r.get(k, "") for _, k in cols])
    print(f"Exported {len(rows)} rows → {path} (target: {a.target})")
    print("Check the field mapping once in the CRM import wizard; de-dup by e-mail as the unique key.")
    _log("export", a.target, len(rows))


def cmd_pull(a):
    """CRM export → update only stage / owner / relation / last contact of existing local records (never adds strangers)."""
    headers, rows = _di.read_table(a.file)
    mapping = _di.build_mapping(headers, a.map)
    if "email" not in mapping.values():
        raise SystemExit("ERROR: no e-mail column recognised in the CRM export; cannot align. Use --map original_column=email.")
    db_path = os.path.join(DATA_DIR, _di.DB_NAME)
    db = _di.load_db(db_path)
    by_email = {(r.get("email") or "").lower(): r for r in db if r.get("email")}
    changed = 0
    today = datetime.date.today().isoformat()
    for raw in rows:
        n = _di.normalize(raw, mapping, "prospect", "crm")
        hit = by_email.get(n["email"])
        if not hit:
            continue
        upd = False
        for k in ("stage", "owner", "last_contact_date"):
            if n.get(k) and n[k] != hit.get(k):
                hit[k] = n[k]
                upd = True
        rel_col = [c for c, f in mapping.items() if f == "relation"]
        if rel_col and raw.get(rel_col[0]):
            rel = _di._relation_from(raw[rel_col[0]], hit.get("relation", "prospect"))
            if rel != hit.get("relation"):
                hit["relation"] = rel
                upd = True
        if upd:
            hit["updated_at"] = today
            changed += 1
    if a.dry_run:
        print(f"[DRY_RUN] would update {changed} local records (existing e-mails only).")
        return
    _di.save_db(db_path, db)
    _di._sync_blacklist(db)
    print(f"Pulled from CRM and updated {changed} records → {db_path}")
    _log("pull", os.path.basename(a.file), changed)


NO_PUSH = ("do_not_contact", "competitor")


def cmd_push_hubspot(a):
    rows = [r for r in _rows_for_export(a.since) if r.get("email") and r.get("relation") not in NO_PUSH]
    inputs = []
    for r in rows:
        props = {"email": r["email"], "firstname": r["_first"], "lastname": r["_last"],
                 "company": r.get("brand", ""), "jobtitle": r.get("title", ""),
                 "website": r.get("website", ""), "country": r.get("region", ""),
                 "phone": r.get("phone", "")}
        if not a.no_status:
            props["hs_lead_status"] = r["_lead_status"]
        inputs.append({"id": r["email"], "idProperty": "email",
                       "properties": {k: v for k, v in props.items() if v}})
    live = os.environ.get("CRM_PUSH") == "1" and os.environ.get("DRY_RUN") not in ("1", "true", "yes")
    token = os.environ.get("HUBSPOT_TOKEN", "")
    print(f"{len(inputs)} HubSpot contacts to push (upsert by email)")
    if not live:
        sample = json.dumps(inputs[:2], ensure_ascii=False, indent=2)
        print("[DRY_RUN] API not called. Preview of the first 2:\n" + sample)
        print("Real push: export HUBSPOT_TOKEN=<private app token>  CRM_PUSH=1  then run again.")
        return
    if not token:
        raise SystemExit("ERROR: HUBSPOT_TOKEN environment variable missing.")
    import config as _cfg   # a real push is an external write: must pass the install gate (READY + matching content fingerprint)
    _cfg.load_profile()
    url = "https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert"
    ok = fail = 0
    for i in range(0, len(inputs), a.batch):
        chunk = inputs[i:i + a.batch]
        req = urllib.request.Request(url, data=json.dumps({"inputs": chunk}).encode("utf-8"),
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8") or "{}")
                ok += len(body.get("results", chunk))
        except urllib.error.HTTPError as e:
            fail += len(chunk)
            print(f"  Batch {i // a.batch + 1} failed: HTTP {e.code} {e.read().decode('utf-8', 'ignore')[:300]}")
    print(f"Done: {ok} succeeded, {fail} failed")
    _log("push-hubspot", "api", ok)


def cmd_mcp_payload(a):
    rows = [r for r in _rows_for_export(a.since) if r.get("email") and r.get("relation") not in NO_PUSH]
    payload = [{"action": "upsert_contact", "match_by": "email", "approved": False,
                "properties": {"email": r["email"], "firstname": r["_first"], "lastname": r["_last"],
                               "company": r.get("brand", ""), "jobtitle": r.get("title", ""),
                               "website": r.get("website", ""), "country": r.get("region", "")},
                "outreach_status": r["_status"], "relation": r.get("relation", "")} for r in rows]
    path = a.out or os.path.join("reports", "crm_mcp_payload.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(payload, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Generated CRM MCP sync list with {len(payload)} items → {path}")
    print("Rules: the AI processes only approved=true items; check for duplicates by email before create/update; afterwards run export or pull to verify consistency.")
    print("HubSpot official remote MCP: https://mcp.hubspot.com (OAuth 2.1 + PKCE; create the app under HubSpot Development → MCP Auth Apps).")


def _log(action, target, n):
    p = os.path.join(DATA_DIR, "crm_sync_log.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    first = not os.path.exists(p)
    with open(p, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["time", "action", "target", "count"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), action, target, n])


def last_sync_date():
    p = os.path.join(DATA_DIR, "crm_sync_log.csv")
    if not os.path.exists(p):
        return ""
    rows = _di.load_db(p)
    return rows[-1]["time"][:10] if rows else ""


def main():
    p = argparse.ArgumentParser(description="Customer DB ⇄ CRM sync: CSV / HubSpot API / MCP (v3.1)")
    sub = p.add_subparsers(dest="cmd")
    pe = sub.add_parser("export")
    pe.add_argument("--target", required=True, choices=list(TARGETS))
    pe.add_argument("--since", help="export only records with updated_at ≥ this date (YYYY-MM-DD)")
    pe.add_argument("--out")
    pe.set_defaults(func=cmd_export)
    pp = sub.add_parser("pull")
    pp.add_argument("file")
    pp.add_argument("--map", nargs="*", default=[])
    pp.add_argument("--dry-run", action="store_true")
    pp.set_defaults(func=cmd_pull)
    ph = sub.add_parser("push-hubspot")
    ph.add_argument("--since")
    ph.add_argument("--batch", type=int, default=100)
    ph.add_argument("--no-status", action="store_true", help="do not write hs_lead_status (use when the portal has customised options)")
    ph.set_defaults(func=cmd_push_hubspot)
    pm = sub.add_parser("mcp-payload")
    pm.add_argument("--since")
    pm.add_argument("--out")
    pm.set_defaults(func=cmd_mcp_payload)
    a = p.parse_args()
    if not getattr(a, "cmd", None):
        p.print_help()
        sys.exit(0)
    a.func(a)


if __name__ == "__main__":
    main()
