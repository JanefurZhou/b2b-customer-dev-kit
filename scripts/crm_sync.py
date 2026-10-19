#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crm_sync.py — 客户库 ⇄ CRM 双向同步（技能版本 v3.1）

三条路径（按你手上有什么选）
----------------------------
  路径 1 · CSV 导入导出（任何 CRM 都能用，零门槛）
      export --target <crm>  把 customer_db + 发信/回复/退信状态 导出成该 CRM 导入向导好映射的列名
      pull <CRM导出.csv>     把 CRM 里人工更新过的阶段/负责人/关系 拉回本地客户库
  路径 2 · HubSpot 官方 API（有私有应用令牌时）
      push-hubspot           调 contacts 批量 upsert（以 email 为唯一键）；默认 DRY_RUN，
                             必须 CRM_PUSH=1 且有 HUBSPOT_TOKEN 才真推
  路径 3 · MCP（运行环境支持 MCP 时）
      mcp-payload            生成 reports/crm_mcp_payload.json，供 AI 通过 CRM 的 MCP 服务
                             （如 HubSpot 官方远程 MCP：https://mcp.hubspot.com）逐条创建/更新，
                             执行前由人工确认

target 可选：hubspot / salesforce / okki / fumeng / generic
  hubspot / salesforce 用其导入向导里常见的英文列名；okki / fumeng / generic 用通用中文列名，
  导入时在对方系统的导入向导里做一次字段映射即可（以各系统当前导入模板为准）。
密钥只走环境变量（HUBSPOT_TOKEN），不写进任何文件。零第三方依赖。
"""

import os
import sys
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
CN_COLS = [("邮箱", "email"), ("联系人", "contact_person"), ("公司名称", "brand"), ("职位", "title"),
           ("官网", "website"), ("国家/地区", "region"), ("电话", "phone"), ("WhatsApp", "whatsapp"),
           ("客户类型", "_relation_cn"), ("跟进阶段", "_lead_status_cn"), ("负责人", "owner"),
           ("最近联系", "last_contact_date"), ("来源", "_source"), ("备注", "_note")]
TARGETS = {"hubspot": EN_COLS, "salesforce": SF_COLS, "okki": CN_COLS, "fumeng": CN_COLS, "generic": CN_COLS}

REL_CN = {"existing_customer": "老客户", "prospect": "潜在客户", "lost": "流失客户",
          "do_not_contact": "禁止联系", "competitor": "同行"}
STATUS_CN = {"new": "未联系", "sent": "已发信", "replied": "已回复", "bounced": "退信",
             "wa": "转WhatsApp", "won": "成交"}
# HubSpot 默认 8 个 hs_lead_status：NEW/OPEN/IN_PROGRESS/OPEN_DEAL/UNQUALIFIED/ATTEMPTED_TO_CONTACT/CONNECTED/BAD_TIMING；
# 你的门户若自定义过选项，请按实际改（或导入时在向导里重映射）。
STATUS_HS = {"new": "NEW", "sent": "ATTEMPTED_TO_CONTACT", "replied": "CONNECTED",
             "bounced": "UNQUALIFIED", "wa": "IN_PROGRESS", "won": "OPEN_DEAL"}


def _status_index():
    """email → 最新外联状态（sent_history + success_cases + wa_contacts）。"""
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
    print(f"已导出 {len(rows)} 条 → {path}（目标：{a.target}）")
    print("导入时在 CRM 的导入向导里核对一次字段映射；以邮箱为唯一键去重。")
    _log("export", a.target, len(rows))


def cmd_pull(a):
    """CRM 导出 → 只更新本地已有记录的 阶段/负责人/关系/最近联系（不新增陌生人）。"""
    headers, rows = _di.read_table(a.file)
    mapping = _di.build_mapping(headers, a.map)
    if "email" not in mapping.values():
        raise SystemExit("ERROR: CRM 导出里没识别到邮箱列，无法对齐。用 --map 原列名=email 指定。")
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
        print(f"[DRY_RUN] 将更新 {changed} 条本地记录（只更新已存在的邮箱）。")
        return
    _di.save_db(db_path, db)
    _di._sync_blacklist(db)
    print(f"已从 CRM 拉回并更新 {changed} 条 → {db_path}")
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
    print(f"待推送 HubSpot 联系人 {len(inputs)} 条（以 email 为唯一键 upsert）")
    if not live:
        sample = json.dumps(inputs[:2], ensure_ascii=False, indent=2)
        print("[DRY_RUN] 未调用 API。前 2 条预览：\n" + sample)
        print("真推：export HUBSPOT_TOKEN=<私有应用令牌>  CRM_PUSH=1  后再运行。")
        return
    if not token:
        raise SystemExit("ERROR: 缺 HUBSPOT_TOKEN 环境变量。")
    import config as _cfg   # 真推属于对外写入：必须过安装门禁（READY + 内容指纹一致）
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
            print(f"  批次 {i // a.batch + 1} 失败：HTTP {e.code} {e.read().decode('utf-8', 'ignore')[:300]}")
    print(f"完成：成功 {ok}，失败 {fail}")
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
    print(f"已生成 CRM MCP 同步清单 {len(payload)} 条 → {path}")
    print("规则：AI 只处理 approved=true 的条目；先按 email 查重再创建/更新；完成后跑 export 或 pull 复核一致性。")
    print("HubSpot 官方远程 MCP：https://mcp.hubspot.com（OAuth 2.1 + PKCE；在 HubSpot 的 Development → MCP Auth Apps 创建应用）。")


def _log(action, target, n):
    p = os.path.join(DATA_DIR, "crm_sync_log.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    first = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
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
    p = argparse.ArgumentParser(description="客户库 ⇄ CRM 同步：CSV / HubSpot API / MCP（v3.1）")
    sub = p.add_subparsers(dest="cmd")
    pe = sub.add_parser("export")
    pe.add_argument("--target", required=True, choices=list(TARGETS))
    pe.add_argument("--since", help="只导出 updated_at ≥ 该日期（YYYY-MM-DD）的记录")
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
    ph.add_argument("--no-status", action="store_true", help="不写 hs_lead_status（门户自定义过选项时用）")
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
