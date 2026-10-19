#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_import.py — 自有客户库 / 外贸 SaaS 导出 / CRM 导出 → 统一客户库（技能版本 v3.1）

为什么要有它
------------
本技能本身不带任何客户数据库。安装时由用户自己导入：
  - 已有客户、往来记录（Excel/CSV，任何 CRM 或表格导出）
  - 外贸 SaaS（海关数据 / 找邮箱 / 获客平台）导出的线索表
导入后统一写进 $B2B_DATA_DIR/customer_db.csv，搜索去重（filter --against）、
保底补池（replenish --pool）、触发口（triggers.py）、CRM 同步（crm_sync.py）都读这一张表。

子命令
------
  inspect <文件>                         只读：识别表头 → 显示字段映射 + 前 3 行预览，不写任何文件
  import  <文件> --relation <关系> --source <来源>
          [--map 原列名=标准字段 ...] [--dry-run]
                                         合并进 customer_db.csv（按邮箱 → 域名去重，已有记录只补空字段）
  stats                                  客户库概览：总量 / 关系分布 / 来源分布 / 可冷开发量
  fields                                 列出标准字段及可识别的中英文列名

关系 --relation（决定能不能冷开发）
  existing_customer   老客户（下过单）→ 不进冷开发池，走复购/生命周期
  prospect            线索/潜客（含 SaaS 导出）→ 进冷开发池，仍需背调后再发
  lost                流失客户 → 进唤醒，不当陌生人发
  do_not_contact      明确拒绝/投诉/退订 → 永不再发
  competitor          同行 → 只做参照，不发

支持格式：.csv（UTF-8 / UTF-8-BOM / GB18030 自动识别）、.xlsx（标准库解析，取第一张表）。
零第三方依赖。只读写本地文件，不联网。
"""

import os
import re
import sys
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

# 标准字段 → 可识别的列名（小写比对；中英文常见 CRM / 海关 / 找邮箱工具导出写法）
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

# 关系列取值的常见写法 → 标准关系
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
    """返回 {原列名: 标准字段}；--map 覆盖优先。"""
    mapping, used = {}, set()
    ov = {}
    for item in overrides or []:
        if "=" not in item:
            raise SystemExit(f"ERROR: --map 写法应为 原列名=标准字段，收到「{item}」")
        k, v = item.split("=", 1)
        if v not in DB_FIELDS + ["first_name", "last_name", "ignore"]:
            raise SystemExit(f"ERROR: --map 目标字段「{v}」不在标准字段里（fields 子命令可查）")
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
    """读 CSV / XLSX → (headers, rows[dict])。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xlsx":
        return _read_xlsx(path)
    if ext in (".xls",):
        raise SystemExit("ERROR: 老格式 .xls 不支持；请在表格软件里另存为 .xlsx 或 .csv 再导入。")
    raw = open(path, "rb").read()
    text = None
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise SystemExit("ERROR: 无法识别文件编码；请另存为 UTF-8 CSV。")
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
            raise SystemExit("ERROR: xlsx 里没有工作表。")
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
    # 先判具体的（禁联/流失/同行/潜客），最后才判「客户」，避免「潜在客户」被误判成老客户
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
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DB_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in DB_FIELDS})


def merge(db_rows, new_rows):
    """按邮箱 → 域名+公司名 去重；已有记录只补空字段，关系「升级」规则：
    do_not_contact 永远保留；existing_customer 不会被 prospect 覆盖。"""
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
    """do_not_contact 同步进 blacklist.csv（csv_ops 的发前检查会拦截）。"""
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
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "brand", "reason", "date"])
        if write_header:
            w.writeheader()
        for r in new:
            w.writerow({"email": r["email"], "brand": r.get("brand", ""),
                        "reason": "import:do_not_contact", "date": datetime.date.today().isoformat()})
    return len(new)


def cmd_fields(_args):
    print("标准字段（customer_db.csv）及可自动识别的列名：")
    for f in DB_FIELDS:
        names = ALIASES.get(f)
        print(f"  {f:<18} " + (" / ".join(names[:8]) if names else "（系统字段）"))
    print("  first_name / last_name  → 自动合并成 contact_person")
    print("识别不到的列：用 --map 原列名=标准字段 指定；不想要的列 --map 原列名=ignore")


def cmd_inspect(args):
    headers, rows = read_table(args.file)
    mapping = build_mapping(headers, args.map)
    print(f"文件：{args.file}  ｜行数：{len(rows)}  ｜列数：{len(headers)}")
    print("字段映射（原列名 → 标准字段）：")
    for h in headers:
        print(f"  {h:<28} → {mapping.get(h, '（未识别，导入时忽略；可用 --map 指定）')}")
    missing = [f for f in ("brand", "email") if f not in mapping.values()]
    if missing:
        print(f"[!] 未识别到关键字段：{', '.join(missing)}。没有 email 的行只能用于去重，不能直接发信。")
    print("前 3 行预览（已按映射标准化）：")
    for r in rows[:3]:
        n = normalize(r, mapping, args.relation or "prospect", "preview")
        print("  " + json.dumps({k: v for k, v in n.items() if v and k not in ("added_date", "updated_at")},
                                ensure_ascii=False))
    print("只读预览，未写任何文件。确认无误后执行 import。")


def cmd_import(args):
    if args.relation not in RELATIONS:
        raise SystemExit(f"ERROR: --relation 只能是 {RELATIONS}")
    headers, rows = read_table(args.file)
    mapping = build_mapping(headers, args.map)
    if not mapping:
        raise SystemExit("ERROR: 一个列都没识别出来。先跑 inspect 看表头，再用 --map 指定。")
    new = [normalize(r, mapping, args.relation, args.source) for r in rows]
    db_path = os.path.join(DATA_DIR, DB_NAME)
    db = load_db(db_path)
    before = len(db)
    added, updated, skipped = merge(db, new)
    rel_count = {}
    for n in new:
        rel_count[n["relation"]] = rel_count.get(n["relation"], 0) + 1
    print(f"读取 {len(rows)} 行 → 新增 {added}，补全已有 {updated}，跳过空行 {skipped}")
    print(f"本次关系分布：{rel_count}")
    if args.dry_run:
        print(f"[DRY_RUN] 未写入。客户库将从 {before} 条变为 {len(db)} 条：{db_path}")
        return
    save_db(db_path, db)
    bl = _sync_blacklist(db)
    log = os.path.join(DATA_DIR, "import_log.csv")
    first = not os.path.exists(log)
    with open(log, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["time", "file", "source", "relation", "rows", "added", "updated"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), os.path.basename(args.file),
                    args.source, args.relation, len(rows), added, updated])
    print(f"已写入客户库：{db_path}（共 {len(db)} 条）" + (f"；同步禁联 {bl} 个邮箱进 blacklist.csv" if bl else ""))
    print("下一步：search_customers.py filter <结果> --against " + db_path + "（搜索去重）；"
          "replenish 默认读取这张表数可发量。")


def cmd_stats(_args):
    db_path = os.path.join(DATA_DIR, DB_NAME)
    db = load_db(db_path)
    if not db:
        print(f"客户库为空或不存在：{db_path}。安装时先导入：data_import.py inspect / import。")
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
    print(f"客户库：{db_path}  共 {len(db)} 条")
    print(f"  关系分布：{rel}")
    print(f"  来源分布：{src}")
    print(f"  可冷开发（prospect·有邮箱·未发）：{cold}")


def main():
    p = argparse.ArgumentParser(description="自有客户库 / SaaS 导出 / CRM 导出 → 统一客户库（v3.1）")
    sub = p.add_subparsers(dest="cmd")
    pi = sub.add_parser("inspect", help="只读：识别表头并预览映射")
    pi.add_argument("file")
    pi.add_argument("--map", nargs="*", default=[])
    pi.add_argument("--relation", choices=RELATIONS)
    pi.set_defaults(func=cmd_inspect)
    pm = sub.add_parser("import", help="合并进 customer_db.csv")
    pm.add_argument("file")
    pm.add_argument("--relation", required=True, choices=RELATIONS)
    pm.add_argument("--source", required=True,
                    help="来源标记，如 own:excel / saas:<平台名> / crm:<系统名> / customs:<平台名>")
    pm.add_argument("--map", nargs="*", default=[])
    pm.add_argument("--dry-run", action="store_true")
    pm.set_defaults(func=cmd_import)
    ps = sub.add_parser("stats", help="客户库概览")
    ps.set_defaults(func=cmd_stats)
    pf = sub.add_parser("fields", help="标准字段与可识别列名")
    pf.set_defaults(func=cmd_fields)
    args = p.parse_args()
    if not getattr(args, "cmd", None):
        p.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
