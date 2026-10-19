#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triggers.py — Data Triggers: scan the customer pool and data tables and build a "what to do today" trigger queue (skill v3.1)

The core of hosting and automation is the customer pool: every action is triggered by data changes, not by someone remembering.
This script only scans read-only and writes one queue; any outbound action (e-mail / WhatsApp / CRM push)
is marked needs_human=true in the queue and is executed only after a human signs off.
The only action allowed to run automatically is protective: with --apply-safe, a bounce anomaly pauses the hosted mailbox.

Trigger types (type)
--------------
  POOL_LOW         sendable cold-outreach candidates < red line, or only enough for N days   → search_customers.py replenish
  NEW_IMPORT_FILE  new CSV/XLSX in $B2B_DATA_DIR/inbox/ (SaaS / customs / CRM export)           → data_import.py inspect/import
  COOLDOWN_DUE     contacts past their cooldown and eligible for the next follow-up            → Step 6 Follow-up Management (DRY_RUN first)
  REPLY_RECEIVED   new reply (sent_history.status=replied)                                     → human reply + Step 6/7
  BOUNCE_SPIKE     bounce rate over the last 7 days above threshold                            → pause hosted mailbox + clean the list (protective, may run automatically)
  WA_SIGNAL        pending WhatsApp leads in wa_contacts                                        → Step 7 WhatsApp Trigger
  WARMUP_STEP      a hosted mailbox enters a new warm-up tier today                            → notice only; senders apply the new cap automatically
  MAILBOX_PAUSED   a hosted mailbox is paused                                                   → investigate, then mail_setup.py resume
  CRM_SYNC_DUE     customer DB changed and last CRM sync ≥ N days ago                           → crm_sync.py export/pull
  WEEKLY_REVIEW    last weekly review ≥ 7 days ago                                             → Step 0 Omni-channel Review / Step 8 write-back

Usage
----
  python3 scripts/triggers.py scan [--floor 100] [--daily-target 100] [--ahead-days 30]
                                   [--bounce-rate 0.05] [--crm-days 7] [--apply-safe]
                                   [--out reports/trigger_queue.json]
  python3 scripts/triggers.py ack <trigger key> [...]  mark as handled (the same event is not raised again)
  python3 scripts/triggers.py reviewed                 record this week's review (resets WEEKLY_REVIEW)
Can be attached to cron / Task Scheduler / a platform scheduled task; run scan once a day (see references/automation_setup.md).
Zero third-party dependencies.
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

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mail_setup as _ms  # noqa: E402

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
STATE_FILE = os.path.join(DATA_DIR, "trigger_state.json")
COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}   # same as csv_ops.py (checked by consistency_audit)
MAX_GENERIC_FOLLOWUP = 3   # from the 4th e-mail stop generic mailboxes (same as csv_ops.py)
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
            return json.load(open(STATE_FILE, encoding="utf-8-sig"))
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
            "Customer DB is empty: import your own customer DB / SaaS export at install, or start a replenish search directly",
            "python3 scripts/data_import.py inspect <file>  or  python3 scripts/search_customers.py replenish --force --emit queries_today.txt",
            False)
    elif sendable < a.floor or days < a.ahead_days:
        add("POOL_LOW", f"POOL_LOW:{today}", 1, sendable,
            f"Sendable cold-outreach candidates {sendable} (red line {a.floor}, about {days} days < lead time {a.ahead_days} days)",
            "python3 scripts/search_customers.py replenish --emit queries_today.txt", False)

    # 2 NEW_IMPORT_FILE
    inbox = os.path.join(DATA_DIR, "inbox")
    logged = {r.get("file") for r in _rows("import_log.csv")}
    if os.path.isdir(inbox):
        new = [f for f in sorted(os.listdir(inbox))
               if f.lower().endswith((".csv", ".xlsx")) and f not in logged]
        for f in new:
            add("NEW_IMPORT_FILE", f"IMPORT:{f}", 2, 1,
                f"New export file in inbox: {f} (from SaaS / customs / CRM): preview the mapping, confirm relation and source, then import",
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
        if status not in ("sent", "") or e in non_cold_emails:   # existing customers / do-not-contact never get cold follow-ups
            continue
        try:
            fu = int(r.get("followup_count") or 0)
        except ValueError:
            fu = 0
        if fu >= MAX_GENERIC_FOLLOWUP:   # from the 4th e-mail no automatic cold follow-up
            continue
        last = _d(r.get("last_followup_date") or r.get("send_date"))
        if last and (today - last).days >= COOLDOWN_RULES.get(fu, 999):
            due.append(e)
    if due:
        add("COOLDOWN_DUE", f"COOLDOWN:{today}", 2, len(due),
            f"{len(due)} contacts are past their cooldown; write the next follow-up (DRY_RUN check first)",
            "python3 scripts/csv_ops.py cooldown <email>  → write follow-up draft → DRY_RUN=1 python3 scripts/batch_sender.py ...",
            True)
    for e in replies:
        add("REPLY_RECEIVED", f"REPLY:{e}", 1, 1, f"{e} replied: reply personally; decide WhatsApp handover / quote / win review",
            "references/SOP.md Step 6 Follow-up Management / Step 7 WhatsApp Trigger", True)
    week = [r for r in sent if (_d(r.get("send_date")) or datetime.date.min) >= today - datetime.timedelta(days=7)]
    bounced = [r for r in week if (r.get("status") or "").lower() == "bounced"]
    if len(week) >= 20 and len(bounced) / len(week) > a.bounce_rate:
        detail = f"Bounces in the last 7 days {len(bounced)}/{len(week)} = {len(bounced) / len(week):.1%} > {a.bounce_rate:.0%}"
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
            detail + (f"; hosted mailbox {paused} paused automatically" if paused else "; pause sending and clean the list"),
            "python3 scripts/imap_scanner.py → dns_validator.py clean → investigate, then mail_setup.py resume <id>", False)

    # 6 WA_SIGNAL
    wa = [r for r in _rows("wa_contacts.csv") if (r.get("status") or "").lower() in ("new", "pending", "待处理", "")]  # "待处理" = legacy Chinese alias for pending
    if wa:
        add("WA_SIGNAL", f"WA:{today}", 2, len(wa), f"{len(wa)} WhatsApp leads pending",
            "references/SOP.md Step 7 WhatsApp Trigger (wa_bulk_sender.py preview → human check → send)", True)

    # 7 WARMUP_STEP / 8 MAILBOX_PAUSED
    for m in _ms.load_mailboxes()["mailboxes"]:
        cap, dn = _ms.warmup_cap(m)
        if any(dn == day for day, _ in (m.get("warmup_schedule") or _ms.DEFAULT_WARMUP)) and dn > 1:
            add("WARMUP_STEP", f"WARMUP:{m['id']}:{today}", 3, cap,
                f"Hosted mailbox {m['id']} enters warm-up day {dn} tier today, daily cap {cap}",
                "python3 scripts/mail_setup.py list", False)
        if m.get("status") == "paused":
            add("MAILBOX_PAUSED", f"PAUSED:{m['id']}:{m.get('paused_at', '')}", 1, 1,
                f"Hosted mailbox {m['id']} is paused: {m.get('paused_reason', '')}",
                f"Investigate bounce / complaint cause, then python3 scripts/mail_setup.py resume {m['id']}", True)

    # 9 CRM_SYNC_DUE
    log = _rows("crm_sync_log.csv")
    last_sync = _d(log[-1]["time"]) if log else None
    db_updated = max((_d(r.get("updated_at")) or datetime.date.min for r in db), default=None)
    if db and (last_sync is None or ((today - last_sync).days >= a.crm_days
                                     and db_updated and db_updated > last_sync)):
        add("CRM_SYNC_DUE", f"CRM:{today}", 3, len(db),
            "Customer DB changed and last CRM sync ≥ %d days ago (or never synced)" % a.crm_days,
            "python3 scripts/crm_sync.py export --target <hubspot|salesforce|okki|fumeng|generic>", True)

    # 10 WEEKLY_REVIEW
    lr = _d(st.get("last_review"))
    if lr is None or (today - lr).days >= 7:
        add("WEEKLY_REVIEW", f"REVIEW:{today.isocalendar()[1]}", 3, 1,
            "Last weekly review ≥ 7 days ago: run Step 0 Omni-channel Review and write the conclusions back into the Soul Seven Kit",
            "python3 scripts/email_dashboard.py → references/soul_kit/weekly_writeback.md → triggers.py reviewed", True)

    q.sort(key=lambda x: (x["priority"], x["type"]))
    out = a.out or os.path.join("reports", "trigger_queue.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump({"generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "queue": q},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"===== Data Triggers scan {today} =====")
    if not q:
        print("No triggers to handle.")
    for x in q:
        flag = "needs human sign-off" if x["needs_human"] else "may run directly"
        print(f"[P{x['priority']}] {x['type']:<16} {x['detail']}")
        print(f"      → {x['next_command']}   ({flag})")
    print(f"Queue written to {out}. After handling, run triggers.py ack <key> to clear the notice.")


def cmd_ack(a):
    st = _state()
    st["acked"] = sorted(set(st.get("acked", [])) | set(a.keys))[-500:]
    _save_state(st)
    print(f"Marked {len(a.keys)} triggers as handled.")


def cmd_reviewed(_a):
    st = _state()
    st["last_review"] = datetime.date.today().isoformat()
    _save_state(st)
    print("This week's review recorded.")


def main():
    p = argparse.ArgumentParser(description="Data Triggers: customer-pool-driven daily trigger queue (v3.1)")
    sub = p.add_subparsers(dest="cmd")
    ps = sub.add_parser("scan")
    ps.add_argument("--floor", type=int, default=100)
    ps.add_argument("--daily-target", dest="daily_target", type=int, default=100)
    ps.add_argument("--ahead-days", dest="ahead_days", type=int, default=30)
    ps.add_argument("--bounce-rate", dest="bounce_rate", type=float, default=0.05,
                    help="bounce-rate threshold over the last 7 days (adjustable default of this skill, not a provider-published number)")
    ps.add_argument("--crm-days", dest="crm_days", type=int, default=7)
    ps.add_argument("--apply-safe", dest="apply_safe", action="store_true",
                    help="allow protective actions (pause a hosted mailbox on a bounce anomaly)")
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
