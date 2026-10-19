#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_import.py — own customer DB / trade-SaaS exports / CRM exports → one unified customer DB (skill v3.1)

Why it exists
------------
The skill ships no customer database. The user imports their own data at install:
  - existing customers and history (Excel/CSV exported from any CRM or spreadsheet)
  - lead lists exported from trade SaaS (customs data / e-mail finders / lead platforms)
Everything lands in $B2B_DATA_DIR/customer_db.csv, which search de-dup (filter --against),
pool floor (replenish --pool), triggers (triggers.py) and CRM sync (crm_sync.py) all read.

Sub-commands
------
  inspect <file>                         Read-only: detect headers → show field mapping + preview of the first 3 rows; writes nothing
  import  <file> --relation <relation> --source <source>
          [--map original_column=standard_field ...] [--dry-run]
                                         Merge into customer_db.csv (de-dup by e-mail → domain; existing rows only get empty fields filled)
  stats                                  DB overview: total / relation split / source split / cold-outreach capacity
  fields                                 List standard fields and the recognised column names (English and Chinese)

Relation --relation (decides whether cold outreach is allowed)
  existing_customer   existing customer (has ordered) → never enters the cold pool; lifecycle / repeat-order track
  prospect            lead / prospect (incl. SaaS exports) → enters the cold pool; still needs research before sending
  lost                churned customer → win-back track; not treated as a stranger
  do_not_contact      explicit refusal / complaint / unsubscribe → never contact again
  competitor          peer → reference only, never contacted

Formats: .csv (UTF-8 / UTF-8-BOM / GB18030 auto-detected), .xlsx (parsed with the standard library, first sheet).
Zero third-party dependencies. Reads and writes local files only; no network.
"""

import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import csv
import json
import zipfile
import argparse
import datetime
import xml.etree.ElementTree as ET

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
DB_NAME = "customer_db.csv"

DB_FIELDS = ["customer_code", "brand", "contact_person", "title", "email", "website",
             "region", "phone", "whatsapp", "linkedin", "industry", "relation", "stage",
             "email_status", "owner", "last_contact_date", "source", "notes",
             "added_date", "updated_at"]

RELATIONS = ("existing_customer", "prospect", "lost", "do_not_contact", "competitor")

# Standard field → recognised column names (lower-case match; common English and Chinese CRM / customs / e-mail-finder export headers)
ALIASES = {
    "customer_code": ["customer_code", "customer id", "客户编号", "客户编码", "客户id", "编号", "id"],
    "brand": ["brand", "company", "company name", "account", "account name", "organization",
              "公司", "公司名", "公司名称", "客户名称", "客户", "企业名称", "品牌", "采购商", "进口商", "买家"],
    "contact_person": ["contact", "contact name", "contact person", "full name", "name",
                       "联系人", "联系人姓名", "姓名", "决策人"],
    "first_name": ["first name", "firstname", "名"],
    "last_name": ["last name", "lastname", "surname", "姓"],
    "title": ["title", "job title", "position", "role", "职位", "职务", "头衔"],
    "email": ["email", "e-mail", "email address", "mail", "work email", "邮箱", "电子邮箱", "邮件地址", "联系邮箱"],
    "website": ["website", "website url", "domain", "company domain", "url", "web", "官网", "网站", "网址", "域名"],
    "region": ["region", "country", "country/region", "market", "nation", "国家", "国家/地区", "地区", "市场"],
    "phone": ["phone", "telephone", "tel", "mobile", "phone number", "电话", "手机", "联系电话"],
    "whatsapp": ["whatsapp", "wa", "whatsapp number", "whatsapp号码"],
    "linkedin": ["linkedin", "linkedin url", "领英", "领英链接"],
    "industry": ["industry", "sector", "行业", "所属行业"],
    "relation": ["relation", "customer type", "type", "关系", "客户类型", "客户状态"],
    "stage": ["stage", "lifecycle stage", "lead status", "deal stage", "status", "阶段", "跟进阶段", "商机阶段"],
    "owner": ["owner", "contact owner", "sales", "负责人", "业务员", "跟进人"],
    "last_contact_date": ["last contact", "last contacted", "last activity date", "最近联系", "最后联系时间", "最近跟进"],
    "notes": ["notes", "note", "remark", "remarks", "comment", "备注", "说明", "采购记录", "采购产品"],
}

# Common spellings of the relation column → standard relation (English and Chinese)
RELATION_WORDS = {
    "existing_customer": ["customer", "client", "existing", "成交", "老客户", "已成交", "客户"],
    "prospect": ["lead", "prospect", "潜客", "线索", "潜在客户", "意向"],
    "lost": ["lost", "churned", "流失", "丢单"],
    "do_not_contact": ["do not contact", "unsubscribed", "opt-out", "退订", "拒绝", "投诉", "黑名单", "禁联", "勿扰", "不要联系"],
    "competitor": ["competitor", "同行", "竞品", "竞争对手"],
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _norm(h):
    return re.sub(r"\s+", " ", str(h or "").strip().lower().replace("_", " "))


def build_mapping(headers, overrides=None):
    """Return {original column: standard field}; --map overrides win."""
    mapping, used = {}, set()
    ov = {}
    for item in overrides or []:
        if "=" not in item:
            raise SystemExit(f"ERROR: --map must be original_column=standard_field, got \"{item}\"")
        k, v = item.split("=", 1)
        if v not in DB_FIELDS + ["first_name", "last_name", "ignore"]:
            raise SystemExit(f"ERROR: --map target field \"{v}\" is not a standard field (see the fields sub-command)")
        ov[k.strip()] = v.strip()
    for h in headers:
        if h in ov:
            if ov[h] != "ignore":
                mapping[h] = ov[h]
                used.add(ov[h])
            continue
        nh = _norm(h)
        for field, names in ALIASES.items():
            if field in used:
                continue
            if nh in [_norm(n) for n in names]:
                mapping[h] = field
                used.add(field)
                break
    return mapping


def read_table(path):
    """Read CSV / XLSX → (headers, rows[dict])."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xlsx":
        return _read_xlsx(path)
    if ext in (".xls",):
        raise SystemExit("ERROR: legacy .xls is not supported; save as .xlsx or .csv in your spreadsheet app and import again.")
    raw = open(path, "rb").read()
    text = None
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit("ERROR: cannot detect the file encoding; save as UTF-8 CSV.")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(text.splitlines(), dialect)
    rows = [r for r in reader]
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        out.append({headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers))})
    return headers, out


def _read_xlsx(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        if not sheets:
            raise SystemExit("ERROR: the xlsx contains no worksheet.")
        root = ET.fromstring(z.read(sheets[0]))
    grid = []
    for row in root.iter(f"{{{ns['m']}}}row"):
        cells = {}
        for c in row.findall("m:c", ns):
            ref = c.get("r", "")
            col = re.match(r"[A-Z]+", ref)
            idx = 0
            if col:
                for ch in col.group(0):
                    idx = idx * 26 + (ord(ch) - 64)
                idx -= 1
            t = c.get("t")
            v = c.find("m:v", ns)
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{ns['m']}}}t"))
            else:
                val = v.text if v is not None else ""
            cells[idx] = (val or "").strip()
        if cells:
            grid.append([cells.get(i, "") for i in range(max(cells) + 1)])
    if not grid:
        return [], []
    headers = grid[0]
    rows = []
    for r in grid[1:]:
        if any(r):
            rows.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
    return headers, rows


def _domain(website, email=""):
    d = (website or "").strip().lower()
    for pre in ("https://", "http://"):
        if d.startswith(pre):
            d = d[len(pre):]
    d = d.split("/")[0].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    if not d and email and "@" in email:
        d = email.split("@")[-1].lower()
    return d


def _relation_from(value, default):
    v = (value or "").strip().lower()
    if not v:
        return default
    if v in RELATIONS:
        return v
    # Check the specific ones first (do-not-contact / lost / competitor / prospect) and "customer" last, so "potential customer" is not misread as existing
    for rel in ("do_not_contact", "lost", "competitor", "prospect", "existing_customer"):
        if any(w in v for w in RELATION_WORDS[rel]):
            return rel
    return default


def normalize(row, mapping, relation, source):
    rec = {f: "" for f in DB_FIELDS}
    first = last = ""
    for col, field in mapping.items():
        val = (row.get(col) or "").strip()
        if field == "first_name":
            first = val
        elif field == "last_name":
            last = val
        elif val:
            rec[field] = val
    if not rec["contact_person"] and (first or last):
        rec["contact_person"] = f"{first} {last}".strip()
    if rec["email"]:
        m = EMAIL_RE.search(rec["email"])
        rec["email"] = m.group(0).lower() if m else ""
    rec["relation"] = _relation_from(rec["relation"], relation)
    rec["source"] = source
    today = datetime.date.today().isoformat()
    rec["added_date"] = today
    rec["updated_at"] = today
    return rec


def load_db(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_db(path, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DB_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in DB_FIELDS})


def merge(db_rows, new_rows):
    """De-dup by e-mail → domain + company name; existing rows only get empty fields filled. Relation "upgrade" rules:
    do_not_contact is always kept; existing_customer is never overwritten by prospect."""
    by_email, by_dom = {}, {}
    for r in db_rows:
        if r.get("email"):
            by_email[r["email"].lower()] = r
        d = _domain(r.get("website", ""), "")
        if d:
            by_dom[(d, (r.get("brand") or "").lower())] = r
    rank = {"do_not_contact": 4, "existing_customer": 3, "lost": 2, "competitor": 2, "prospect": 1, "": 0}
    added = updated = skipped = 0
    for n in new_rows:
        if not (n.get("email") or n.get("website") or n.get("brand")):
            skipped += 1
            continue
        hit = by_email.get(n["email"]) if n.get("email") else None
        if hit is None:
            d = _domain(n.get("website", ""), "")
            if d:
                hit = by_dom.get((d, (n.get("brand") or "").lower()))
        if hit is None:
            db_rows.append(n)
            added += 1
            if n.get("email"):
                by_email[n["email"]] = n
            d = _domain(n.get("website", ""), "")
            if d:
                by_dom[(d, (n.get("brand") or "").lower())] = n
            continue
        changed = False
        for k in DB_FIELDS:
            if k in ("added_date", "relation", "source"):
                continue
            if not hit.get(k) and n.get(k):
                hit[k] = n[k]
                changed = True
        if rank.get(n["relation"], 0) > rank.get(hit.get("relation", ""), 0):
            hit["relation"] = n["relation"]
            changed = True
        if n["source"] not in (hit.get("source") or ""):
            hit["source"] = ((hit.get("source") or "") + ";" + n["source"]).strip(";")
            changed = True
        if changed:
            hit["updated_at"] = n["updated_at"]
            updated += 1
    return added, updated, skipped


def _sync_blacklist(rows):
    """Sync do_not_contact rows into blacklist.csv (the csv_ops pre-send check blocks them)."""
    path = os.path.join(DATA_DIR, "blacklist.csv")
    existing = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            existing = {(r.get("email") or "").lower() for r in csv.DictReader(f)}
    new = [r for r in rows if r.get("relation") == "do_not_contact" and r.get("email")
           and r["email"].lower() not in existing]
    if not new:
        return 0
    os.makedirs(DATA_DIR, exist_ok=True)
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "brand", "reason", "date"])
        if write_header:
            w.writeheader()
        for r in new:
            w.writerow({"email": r["email"], "brand": r.get("brand", ""),
                        "reason": "import:do_not_contact", "date": datetime.date.today().isoformat()})
    return len(new)


def cmd_fields(_args):
    print("Standard fields (customer_db.csv) and auto-recognised column names:")
    for f in DB_FIELDS:
        names = ALIASES.get(f)
        print(f"  {f:<18} " + (" / ".join(names[:8]) if names else "(system field)"))
    print("  first_name / last_name  → merged automatically into contact_person")
    print("Unrecognised columns: use --map original_column=standard_field; unwanted columns: --map original_column=ignore")


def cmd_inspect(args):
    headers, rows = read_table(args.file)
    mapping = build_mapping(headers, args.map)
    print(f"File: {args.file}  | rows: {len(rows)}  | columns: {len(headers)}")
    print("Field mapping (original column → standard field):")
    for h in headers:
        print(f"  {h:<28} → {mapping.get(h, '(unrecognised; ignored on import; use --map to assign)')}")
    missing = [f for f in ("brand", "email") if f not in mapping.values()]
    if missing:
        print(f"[!] Key fields not recognised: {', '.join(missing)}. Rows without an e-mail can only be used for de-dup, not for sending.")
    print("Preview of the first 3 rows (normalised by the mapping):")
    for r in rows[:3]:
        n = normalize(r, mapping, args.relation or "prospect", "preview")
        print("  " + json.dumps({k: v for k, v in n.items() if v and k not in ("added_date", "updated_at")},
                                ensure_ascii=False))
    print("Read-only preview; nothing written. Run import once the mapping looks right.")


def cmd_import(args):
    if args.relation not in RELATIONS:
        raise SystemExit(f"ERROR: --relation must be one of {RELATIONS}")
    headers, rows = read_table(args.file)
    mapping = build_mapping(headers, args.map)
    if not mapping:
        raise SystemExit("ERROR: no column was recognised. Run inspect to see the headers, then assign with --map.")
    new = [normalize(r, mapping, args.relation, args.source) for r in rows]
    db_path = os.path.join(DATA_DIR, DB_NAME)
    db = load_db(db_path)
    before = len(db)
    added, updated, skipped = merge(db, new)
    rel_count = {}
    for n in new:
        rel_count[n["relation"]] = rel_count.get(n["relation"], 0) + 1
    print(f"Read {len(rows)} rows → {added} added, {updated} existing rows completed, {skipped} empty rows skipped")
    print(f"Relation split in this import: {rel_count}")
    if args.dry_run:
        print(f"[DRY_RUN] nothing written. The DB would go from {before} to {len(db)} rows: {db_path}")
        return
    save_db(db_path, db)
    bl = _sync_blacklist(db)
    log = os.path.join(DATA_DIR, "import_log.csv")
    first = not os.path.exists(log)
    with open(log, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["time", "file", "source", "relation", "rows", "added", "updated"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), os.path.basename(args.file),
                    args.source, args.relation, len(rows), added, updated])
    print(f"Customer DB written: {db_path} ({len(db)} rows)" + (f"; {bl} do-not-contact e-mails synced into blacklist.csv" if bl else ""))
    print("Next: search_customers.py filter <results> --against " + db_path + " (search de-dup); "
          "replenish reads this table by default to count sendable accounts.")


def cmd_stats(_args):
    db_path = os.path.join(DATA_DIR, DB_NAME)
    db = load_db(db_path)
    if not db:
        print(f"Customer DB empty or missing: {db_path}. Import at install: data_import.py inspect / import.")
        return
    rel, src = {}, {}
    cold = 0
    for r in db:
        rel[r.get("relation", "")] = rel.get(r.get("relation", ""), 0) + 1
        for s in (r.get("source") or "unknown").split(";"):
            key = s.split(":")[0]
            src[key] = src.get(key, 0) + 1
        if (r.get("email") and r.get("relation") == "prospect"
                and (r.get("email_status") or "").lower() not in ("sent", "replied", "bounced")):
            cold += 1
    print(f"Customer DB: {db_path}  {len(db)} rows")
    print(f"  Relation split: {rel}")
    print(f"  Source split: {src}")
    print(f"  Cold-outreach capacity (prospect · has e-mail · never sent): {cold}")


def main():
    p = argparse.ArgumentParser(description="Own customer DB / SaaS exports / CRM exports → one unified customer DB (v3.1)")
    sub = p.add_subparsers(dest="cmd")
    pi = sub.add_parser("inspect", help="Read-only: detect headers and preview the mapping")
    pi.add_argument("file")
    pi.add_argument("--map", nargs="*", default=[])
    pi.add_argument("--relation", choices=RELATIONS)
    pi.set_defaults(func=cmd_inspect)
    pm = sub.add_parser("import", help="Merge into customer_db.csv")
    pm.add_argument("file")
    pm.add_argument("--relation", required=True, choices=RELATIONS)
    pm.add_argument("--source", required=True,
                    help="Source tag, e.g. own:excel / saas:<platform> / crm:<system> / customs:<platform>")
    pm.add_argument("--map", nargs="*", default=[])
    pm.add_argument("--dry-run", action="store_true")
    pm.set_defaults(func=cmd_import)
    ps = sub.add_parser("stats", help="Customer DB overview")
    ps.set_defaults(func=cmd_stats)
    pf = sub.add_parser("fields", help="Standard fields and recognised column names")
    pf.set_defaults(func=cmd_fields)
    args = p.parse_args()
    if not getattr(args, "cmd", None):
        p.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
