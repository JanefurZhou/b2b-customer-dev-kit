#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triggers.py — 数据触发口：扫描客户池与各数据表，生成「今天该做什么」的触发队列（技能版本 v3.1）

托管和自动化的核心是客户池：所有动作都由数据变化触发，而不是靠人记。
本脚本只读扫描 + 写一份队列；任何「发出去」的动作（邮件 / WhatsApp / 推 CRM）
在队列里一律标 needs_human=true，由人工拍板后再执行对应命令。
唯一允许自动执行的是保护性动作：--apply-safe 时，退信异常会暂停托管邮箱。

触发口（type）
--------------
  POOL_LOW         可发冷开发候选 < 红线，或只够 N 天        → search_customers.py replenish
  NEW_IMPORT_FILE  $B2B_DATA_DIR/inbox/ 出现新的 CSV/XLSX（SaaS/海关/CRM 导出）→ data_import.py inspect/import
  COOLDOWN_DUE     已过冷却期、可发下一封跟进的联系人        → 第六步 跟进管理（先 DRY_RUN）
  REPLY_RECEIVED   新回复（sent_history.status=replied）      → 人工回复 + 第六/七步
  BOUNCE_SPIKE     近 7 天退信率超阈值                         → 暂停托管邮箱 + 清洗名单（保护性，可自动）
  WA_SIGNAL        wa_contacts 里待处理的 WhatsApp 线索        → 第七步 WhatsApp 触发
  WARMUP_STEP      托管邮箱今天进入新的预热档位                 → 仅提示，发信脚本自动按新上限
  MAILBOX_PAUSED   有托管邮箱处于暂停                           → 排查后 mail_setup.py resume
  CRM_SYNC_DUE     客户库有更新且距上次 CRM 同步 ≥ N 天         → crm_sync.py export/pull
  WEEKLY_REVIEW    距上次周复盘 ≥ 7 天                          → 第零步 全渠道复盘 / 第八步 写回

用法
----
  python3 scripts/triggers.py scan [--floor 100] [--daily-target 100] [--ahead-days 30]
                                   [--bounce-rate 0.05] [--crm-days 7] [--apply-safe]
                                   [--out reports/trigger_queue.json]
  python3 scripts/triggers.py ack <触发 key> [...]     标记已处理（同一事件不再重复提醒）
  python3 scripts/triggers.py reviewed                 记录本周已复盘（重置 WEEKLY_REVIEW）
可挂到 cron / 任务计划 / 平台定时任务，每天跑一次 scan（见 references/automation_setup.md）。
零第三方依赖。
"""

import os
import sys
import csv
import json
import argparse
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mail_setup as _ms  # noqa: E402

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
STATE_FILE = os.path.join(DATA_DIR, "trigger_state.json")
COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}   # 与 csv_ops.py 一致（consistency_audit 校验）
MAX_GENERIC_FOLLOWUP = 3   # 第4封起停通用邮箱（与 csv_ops.py 一致）
MAX_TOTAL_FOLLOWUP = 4
NON_COLD = {"existing_customer", "do_not_contact", "competitor", "lost_do_not_contact"}


def _rows(name):
    p = os.path.join(DATA_DIR, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"acked": [], "last_review": "", "seen_inbox": []}


def _save_state(s):
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(s, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def _d(s):
    try:
        return datetime.date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def scan(a):
    today = datetime.date.today()
    st = _state()
    acked = set(st.get("acked", []))
    q = []

    def add(t, key, priority, count, detail, cmd, needs_human):
        if key in acked:
            return
        q.append({"type": t, "key": key, "priority": priority, "count": count,
                  "detail": detail, "next_command": cmd, "needs_human": needs_human})

    # 1 POOL_LOW
    db = _rows("customer_db.csv")
    sent = _rows("sent_history.csv")
    sent_emails = {(r.get("email") or "").lower() for r in sent}
    non_cold_emails = {(r.get("email") or "").lower() for r in db
                       if (r.get("relation") or "prospect") in NON_COLD}
    sendable = sum(1 for r in db if r.get("email") and (r.get("relation") or "prospect") not in NON_COLD
                   and r["email"].lower() not in sent_emails
                   and (r.get("email_status") or "").lower() not in ("sent", "replied", "bounced"))
    days = sendable // a.daily_target if a.daily_target else 0
    if not db:
        add("POOL_LOW", f"POOL_EMPTY:{today}", 1, 0,
            "客户库为空：安装时先导入自有客户库/SaaS 导出，或直接开始补池搜索",
            "python3 scripts/data_import.py inspect <文件>  或  python3 scripts/search_customers.py replenish --force --emit queries_today.txt",
            False)
    elif sendable < a.floor or days < a.ahead_days:
        add("POOL_LOW", f"POOL_LOW:{today}", 1, sendable,
            f"可发冷开发候选 {sendable}（红线 {a.floor}，约够 {days} 天 < 提前量 {a.ahead_days} 天）",
            "python3 scripts/search_customers.py replenish --emit queries_today.txt", False)

    # 2 NEW_IMPORT_FILE
    inbox = os.path.join(DATA_DIR, "inbox")
    logged = {r.get("file") for r in _rows("import_log.csv")}
    if os.path.isdir(inbox):
        new = [f for f in sorted(os.listdir(inbox))
               if f.lower().endswith((".csv", ".xlsx")) and f not in logged]
        for f in new:
            add("NEW_IMPORT_FILE", f"IMPORT:{f}", 2, 1,
                f"inbox 有新导出文件 {f}（来自 SaaS/海关/CRM）：先预览映射，人工确认关系与来源后导入",
                f"python3 scripts/data_import.py inspect {os.path.join(inbox, f)}", True)

    # 3 COOLDOWN_DUE / 4 REPLY_RECEIVED / 5 BOUNCE_SPIKE
    latest = {}
    for r in sent:
        e = (r.get("email") or "").lower()
        if e:
            latest[e] = r
    due, replies = [], []
    for e, r in latest.items():
        status = (r.get("status") or "").lower()
        if status == "replied":
            replies.append(e)
            continue
        if status not in ("sent", "") or e in non_cold_emails:   # 老客户/禁联不排冷邮件跟进
            continue
        try:
            fu = int(r.get("followup_count") or 0)
        except ValueError:
            fu = 0
        if fu >= MAX_GENERIC_FOLLOWUP:   # 第4封起不再自动排冷邮件跟进
            continue
        last = _d(r.get("last_followup_date") or r.get("send_date"))
        if last and (today - last).days >= COOLDOWN_RULES.get(fu, 999):
            due.append(e)
    if due:
        add("COOLDOWN_DUE", f"COOLDOWN:{today}", 2, len(due),
            f"{len(due)} 个联系人已过冷却期，可写下一封跟进（先 DRY_RUN 核对）",
            "python3 scripts/csv_ops.py cooldown <email>  → 写跟进草稿 → DRY_RUN=1 python3 scripts/batch_sender.py ...",
            True)
    for e in replies:
        add("REPLY_RECEIVED", f"REPLY:{e}", 1, 1, f"{e} 已回复：人工回复，判断转 WhatsApp / 报价 / 成单复盘",
            "references/SOP.md 第六步 跟进管理 / 第七步 WhatsApp 触发", True)
    week = [r for r in sent if (_d(r.get("send_date")) or datetime.date.min) >= today - datetime.timedelta(days=7)]
    bounced = [r for r in week if (r.get("status") or "").lower() == "bounced"]
    if len(week) >= 20 and len(bounced) / len(week) > a.bounce_rate:
        detail = f"近 7 天退信 {len(bounced)}/{len(week)} = {len(bounced) / len(week):.1%} > {a.bounce_rate:.0%}"
        paused = []
        if a.apply_safe:
            data = _ms.load_mailboxes()
            for m in data["mailboxes"]:
                if m.get("status", "active") == "active":
                    m["status"] = "paused"
                    m["paused_reason"] = "auto: " + detail
                    paused.append(m["id"])
            if paused:
                _ms.save_mailboxes(data)
        add("BOUNCE_SPIKE", f"BOUNCE:{today}", 1, len(bounced),
            detail + (f"；已自动暂停托管邮箱 {paused}" if paused else "；建议暂停发信并清洗名单"),
            "python3 scripts/imap_scanner.py → dns_validator.py 清洗 → 排查后 mail_setup.py resume <id>", False)

    # 6 WA_SIGNAL
    wa = [r for r in _rows("wa_contacts.csv") if (r.get("status") or "").lower() in ("new", "pending", "待处理", "")]
    if wa:
        add("WA_SIGNAL", f"WA:{today}", 2, len(wa), f"{len(wa)} 条 WhatsApp 线索待处理",
            "references/SOP.md 第七步 WhatsApp 触发（wa_bulk_sender.py preview → 人工核对 → send）", True)

    # 7 WARMUP_STEP / 8 MAILBOX_PAUSED
    for m in _ms.load_mailboxes()["mailboxes"]:
        cap, dn = _ms.warmup_cap(m)
        if any(dn == day for day, _ in (m.get("warmup_schedule") or _ms.DEFAULT_WARMUP)) and dn > 1:
            add("WARMUP_STEP", f"WARMUP:{m['id']}:{today}", 3, cap,
                f"托管邮箱 {m['id']} 今天进入预热第 {dn} 天档位，每日上限 {cap}",
                "python3 scripts/mail_setup.py list", False)
        if m.get("status") == "paused":
            add("MAILBOX_PAUSED", f"PAUSED:{m['id']}:{m.get('paused_at', '')}", 1, 1,
                f"托管邮箱 {m['id']} 暂停中：{m.get('paused_reason', '')}",
                f"排查退信/投诉原因后 python3 scripts/mail_setup.py resume {m['id']}", True)

    # 9 CRM_SYNC_DUE
    log = _rows("crm_sync_log.csv")
    last_sync = _d(log[-1]["time"]) if log else None
    db_updated = max((_d(r.get("updated_at")) or datetime.date.min for r in db), default=None)
    if db and (last_sync is None or ((today - last_sync).days >= a.crm_days
                                     and db_updated and db_updated > last_sync)):
        add("CRM_SYNC_DUE", f"CRM:{today}", 3, len(db),
            "客户库有更新，距上次 CRM 同步 ≥ %d 天（或从未同步）" % a.crm_days,
            "python3 scripts/crm_sync.py export --target <hubspot|salesforce|okki|fumeng|generic>", True)

    # 10 WEEKLY_REVIEW
    lr = _d(st.get("last_review"))
    if lr is None or (today - lr).days >= 7:
        add("WEEKLY_REVIEW", f"REVIEW:{today.isocalendar()[1]}", 3, 1,
            "距上次周复盘 ≥ 7 天：跑第零步 全渠道复盘，并把结论写回七件套",
            "python3 scripts/email_dashboard.py → references/soul_kit/周复盘写回.md → triggers.py reviewed", True)

    q.sort(key=lambda x: (x["priority"], x["type"]))
    out = a.out or os.path.join("reports", "trigger_queue.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump({"generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "queue": q},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"===== 数据触发口扫描 {today} =====")
    if not q:
        print("没有需要处理的触发。")
    for x in q:
        flag = "需人工拍板" if x["needs_human"] else "可直接执行"
        print(f"[P{x['priority']}] {x['type']:<16} {x['detail']}")
        print(f"      → {x['next_command']}   （{flag}）")
    print(f"队列已写入 {out}。处理完用 triggers.py ack <key> 消掉提醒。")


def cmd_ack(a):
    st = _state()
    st["acked"] = sorted(set(st.get("acked", [])) | set(a.keys))[-500:]
    _save_state(st)
    print(f"已标记处理 {len(a.keys)} 个触发。")


def cmd_reviewed(_a):
    st = _state()
    st["last_review"] = datetime.date.today().isoformat()
    _save_state(st)
    print("已记录本周复盘。")


def main():
    p = argparse.ArgumentParser(description="数据触发口：客户池驱动的每日触发队列（v3.1）")
    sub = p.add_subparsers(dest="cmd")
    ps = sub.add_parser("scan")
    ps.add_argument("--floor", type=int, default=100)
    ps.add_argument("--daily-target", dest="daily_target", type=int, default=100)
    ps.add_argument("--ahead-days", dest="ahead_days", type=int, default=30)
    ps.add_argument("--bounce-rate", dest="bounce_rate", type=float, default=0.05,
                    help="近 7 天退信率阈值（本技能可调默认值，不是服务商公布数字）")
    ps.add_argument("--crm-days", dest="crm_days", type=int, default=7)
    ps.add_argument("--apply-safe", dest="apply_safe", action="store_true",
                    help="允许执行保护性动作（退信异常时暂停托管邮箱）")
    ps.add_argument("--out")
    ps.set_defaults(func=scan)
    pa = sub.add_parser("ack")
    pa.add_argument("keys", nargs="+")
    pa.set_defaults(func=cmd_ack)
    pr = sub.add_parser("reviewed")
    pr.set_defaults(func=cmd_reviewed)
    a = p.parse_args()
    if not getattr(a, "cmd", None):
        p.print_help()
        sys.exit(0)
    a.func(a)


if __name__ == "__main__":
    main()
