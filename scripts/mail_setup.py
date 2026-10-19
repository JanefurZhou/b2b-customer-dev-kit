#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mail_setup.py — sending-route takeover: enterprise mailbox keys / hosted multi-mailbox / warm-up ramp / MCP sending route (skill v3.1)

Two sending paths (choose one, or run both)
--------------------------------
Path A · Enterprise mailbox + key (most common for Chinese providers; works for any SMTP provider)
    Tencent Exmail / Alibaba Mail / NetEase Enterprise Mail / Gmail·Workspace / Microsoft 365 / custom SMTP.
    "Key" = the client-specific password / third-party client password / client authorisation code / app password
    generated in the mailbox admin UI — not the web login password. Keys live only in environment variables; this script and every config file never store them in clear text.
Path B · MCP / platform connectors
    When the runtime already has a Gmail / Outlook mail connector or a mail MCP:
    DRY_RUN produces a dry-run report → human checks each item → mcp-export builds the outbox → the AI calls the connector to draft/send
    → mcp-writeback updates sent_history. The script itself calls no MCP and never bypasses human confirmation.

Sub-commands
------
  providers                         List built-in provider presets (servers / ports / what the key is called / where to generate it)
  env <provider> --user <mailbox>    Print the environment variables to export (the key line is left blank for you to fill)
  add <id> --provider <p> --user <mailbox> [--pass-env VAR] [--daily-cap N] [--start YYYY-MM-DD]
                                    Register a hosted mailbox in config/mailboxes.json (stores variable names only, never keys)
  list                              Each hosted mailbox: status / today's warm-up cap / used today / remaining
  pick                              Pick today's mailbox by remaining quota (rotation) and print the export lines
  test [--mailbox id]               Log in to SMTP (+IMAP) only, to verify the key; sends nothing
  auth-check <domain> [--selector s] Look up the sending domain's SPF / DMARC / DKIM DNS TXT records (read-only)
  pause <id> --reason <text> / resume <id>
  mcp-export <dry_run_report.json> [--out reports/mcp_outbox.json]
  mcp-writeback <mcp_outbox.json>   Write outbox items with status=sent back into sent_history

Warm-up ramp and auto-pause
------------------
  Each hosted mailbox has a warmup_schedule (from day N → daily cap). The built-in default is a set of "conservative starting values": an adjustable default of this skill, not a number published by any provider. If your provider
  gives your account an explicit quota, the provider wins.
  In MAILBOX mode batch_sender / decision_maker_sender use min(profile daily_limit, warm-up cap − used today);
  when bounces in one round exceed bounce_pause_rate (default 0.05, editable) the mailbox is set to paused automatically.
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
import ssl
import socket
import struct
import smtplib
import imaplib
import argparse
import datetime
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_HERE)
MAILBOX_FILE = os.environ.get("B2B_MAILBOXES") or os.path.join(_SKILL_ROOT, "config", "mailboxes.json")
DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
USAGE_FILE = "mailbox_usage.csv"

# Provider presets: all values come from the providers' official help pages (see the source column in references/mail_setup.md)
PROVIDERS = {
    "tencent_exmail": {
        "name": "Tencent Exmail",
        "smtp_host": "smtp.exmail.qq.com", "smtp_port": 465,
        "imap_host": "imap.exmail.qq.com", "imap_port": 993,
        "overseas": "overseas nodes hwsmtp.exmail.qq.com / hwimap.exmail.qq.com",
        "secret": "client-specific password (required once secure login is enabled)",
        "where": "Webmail → Settings → Mailbox binding → Client-specific password; also enable IMAP/SMTP under send/receive settings",
    },
    "aliyun_qiye": {
        "name": "Alibaba Mail (qiye.aliyun.com)",
        "smtp_host": "smtp.qiye.aliyun.com", "smtp_port": 465,
        "imap_host": "imap.qiye.aliyun.com", "imap_port": 993,
        "overseas": "Hong Kong nodes smtphk.qiye.aliyun.com / imaphk.qiye.aliyun.com",
        "secret": "third-party client security password",
        "where": "Webmail → Settings → Account & security → Account security → Third-party client security password",
    },
    "netease_qiye": {
        "name": "NetEase Enterprise Mail (qiye.163.com)",
        "smtp_host": "smtphz.qiye.163.com", "smtp_port": 465,
        "imap_host": "imaphz.qiye.163.com", "imap_port": 993,
        "overseas": "",
        "secret": "client authorisation code (shown once only; save it immediately)",
        "where": "Webmail → Settings → Account & security → Client settings → Generate authorisation code; the admin must have enabled client protocols",
    },
    "gmail": {
        "name": "Gmail / Google Workspace",
        "smtp_host": "smtp.gmail.com", "smtp_port": 465,
        "imap_host": "imap.gmail.com", "imap_port": 993,
        "overseas": "587 + STARTTLS also works",
        "secret": "app password (2-step verification required; revoked when the account password changes)",
        "where": "Google Account → Security → 2-Step Verification → App passwords; Google prefers OAuth / connectors (path B)",
    },
    "microsoft365": {
        "name": "Microsoft 365 / Exchange Online",
        "smtp_host": "smtp.office365.com", "smtp_port": 587,
        "imap_host": "", "imap_port": 993,
        "overseas": "IMAP inbound / bounce scanning should use OAuth or a connector (path B); this preset leaves IMAP empty",
        "secret": "SMTP AUTH basic authentication (account password) — Microsoft has published a phased retirement timeline; prefer OAuth / connectors (path B)",
        "where": "The admin must enable SMTP AUTH for the mailbox; from late December 2026 basic auth is disabled by default for existing tenants",
    },
    "custom": {
        "name": "Custom SMTP",
        "smtp_host": "", "smtp_port": 465, "imap_host": "", "imap_port": 993,
        "overseas": "", "secret": "SMTP password / authorisation code from your provider", "where": "see your mail provider's help pages",
    },
}

# Conservative starting values (adjustable default of this skill, not provider-published numbers): [from day N, daily cap]
DEFAULT_WARMUP = [[1, 20], [8, 40], [15, 80], [22, 150], [29, 200]]
DEFAULT_BOUNCE_PAUSE_RATE = 0.05


# ---------------- Hosted mailbox configuration ----------------
def load_mailboxes():
    if not os.path.exists(MAILBOX_FILE):
        return {"mailboxes": []}
    with open(MAILBOX_FILE, encoding="utf-8-sig") as f:
        data = json.load(f)
    data.setdefault("mailboxes", [])
    return data


def save_mailboxes(data):
    os.makedirs(os.path.dirname(MAILBOX_FILE), exist_ok=True)
    with open(MAILBOX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find(data, mid):
    for m in data["mailboxes"]:
        if m["id"] == mid:
            return m
    return None


def warmup_cap(mb, today=None):
    today = today or datetime.date.today()
    try:
        start = datetime.date.fromisoformat(mb.get("start_date") or today.isoformat())
    except ValueError:
        start = today
    day_n = (today - start).days + 1
    cap = 0
    for day, limit in mb.get("warmup_schedule") or DEFAULT_WARMUP:
        if day_n >= day:
            cap = limit
    if mb.get("daily_cap"):
        cap = min(cap, int(mb["daily_cap"])) if cap else int(mb["daily_cap"])
    return cap, day_n


def _usage_rows():
    p = os.path.join(DATA_DIR, USAGE_FILE)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def used_today(mid):
    today = datetime.date.today().isoformat()
    n = 0
    for r in _usage_rows():
        if r.get("date") == today and r.get("mailbox") == mid:
            n += int(r.get("sent") or 0)
    return n


def record_usage(mid, sent, bounced):
    p = os.path.join(DATA_DIR, USAGE_FILE)
    os.makedirs(DATA_DIR, exist_ok=True)
    first = not os.path.exists(p) or os.path.getsize(p) == 0
    with open(p, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "time", "mailbox", "sent", "bounced"])
        if first:
            w.writeheader()
        w.writerow({"date": datetime.date.today().isoformat(),
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "mailbox": mid, "sent": sent, "bounced": bounced})


def maybe_auto_pause(mid, sent, bounced):
    """Bounces in one round above the threshold → pause the mailbox automatically (protective action; resuming requires a manual resume)."""
    total = sent + bounced
    if total < 5:
        return False
    data = load_mailboxes()
    mb = _find(data, mid)
    if not mb:
        return False
    rate = float(mb.get("bounce_pause_rate", DEFAULT_BOUNCE_PAUSE_RATE))
    if bounced / total > rate:
        mb["status"] = "paused"
        mb["paused_reason"] = f"auto: bounces this round {bounced}/{total} > {rate:.0%}"
        mb["paused_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        save_mailboxes(data)
        return True
    return False


def remaining(mb):
    cap, _ = warmup_cap(mb)
    return max(0, cap - used_today(mb["id"]))


def pick_mailbox(data=None):
    data = data or load_mailboxes()
    active = [m for m in data["mailboxes"] if m.get("status", "active") == "active"]
    active.sort(key=lambda m: -remaining(m))
    for m in active:
        if remaining(m) > 0:
            return m
    return None


def resolve_sender_route():
    """Called by the sending scripts: returns dict(host, port, user, password, mailbox_id, cap).

    Priority: MAILBOX=<id> (explicit hosted mailbox) > config/mailboxes.json exists and SMTP_HOST unset (auto rotation)
            > plain SMTP_HOST/SMTP_USER/SMTP_PASS environment variables (cap=None = no extra cap).
    """
    want = os.environ.get("MAILBOX", "").strip()
    data = load_mailboxes()
    mb = None
    if want:
        mb = _find(data, want)
        if mb is None:
            raise SystemExit(f"ERROR: MAILBOX={want} is not in {MAILBOX_FILE}; register it with mail_setup.py add first.")
        if mb.get("status", "active") != "active":
            raise SystemExit(f"ERROR: mailbox {want} is paused ({mb.get('paused_reason','')}). Investigate, then mail_setup.py resume {want}.")
    elif data["mailboxes"] and not os.environ.get("SMTP_HOST"):
        mb = pick_mailbox(data)
        if mb is None:
            raise SystemExit("ERROR: every hosted mailbox is out of quota for today or paused. See mail_setup.py list.")
    if mb is None:
        return {"host": os.environ.get("SMTP_HOST", ""), "port": int(os.environ.get("SMTP_PORT", "465")),
                "user": os.environ.get("SMTP_USER", ""), "password": os.environ.get("SMTP_PASS", ""),
                "mailbox_id": "", "cap": None}
    prov = PROVIDERS.get(mb.get("provider", "custom"), PROVIDERS["custom"])
    return {"host": mb.get("smtp_host") or prov["smtp_host"],
            "port": int(mb.get("smtp_port") or prov["smtp_port"]),
            "user": mb["user"], "password": os.environ.get(mb.get("pass_env", ""), ""),
            "mailbox_id": mb["id"], "cap": remaining(mb), "pass_env": mb.get("pass_env", "")}


# ---------------- Sub-commands ----------------
def cmd_providers(_a):
    for pid, p in PROVIDERS.items():
        print(f"[{pid}] {p['name']}")
        print(f"   SMTP {p['smtp_host'] or '<your server>'}:{p['smtp_port']}   IMAP {p['imap_host'] or '<your server>'}:{p['imap_port']}")
        if p["overseas"]:
            print(f"   {p['overseas']}")
        print(f"   Key: {p['secret']}")
        print(f"   Where to generate: {p['where']}")
    print("Sources and caveats: references/mail_setup.md")


def cmd_env(a):
    p = PROVIDERS.get(a.provider)
    if not p:
        raise SystemExit(f"ERROR: unknown provider {a.provider}; choose from {list(PROVIDERS)}")
    print(f"# {p['name']} — paste into your terminal (fill the key line yourself; never write it into a file or a chat)")
    print(f"export SMTP_HOST={p['smtp_host'] or '<your SMTP server>'}")
    print(f"export SMTP_PORT={p['smtp_port']}")
    print(f"export SMTP_USER={a.user}")
    print("export SMTP_PASS=  # ← paste your " + p["secret"].split(" (")[0])
    print(f"export IMAP_HOST={p['imap_host'] or '<your IMAP server>'}")
    print(f"export IMAP_PORT={p['imap_port']}")
    print("# then:  python3 scripts/mail_setup.py test   (login only, no sending)")


def cmd_add(a):
    if a.provider not in PROVIDERS:
        raise SystemExit(f"ERROR: unknown provider {a.provider}; choose from {list(PROVIDERS)}")
    data = load_mailboxes()
    if _find(data, a.id):
        raise SystemExit(f"ERROR: mailbox id {a.id} already exists.")
    pass_env = a.pass_env or ("MAILBOX_PASS_" + a.id.upper().replace("-", "_"))
    mb = {"id": a.id, "provider": a.provider, "user": a.user, "pass_env": pass_env,
          "start_date": a.start or datetime.date.today().isoformat(),
          "warmup_schedule": DEFAULT_WARMUP, "status": "active",
          "bounce_pause_rate": DEFAULT_BOUNCE_PAUSE_RATE}
    if a.daily_cap:
        mb["daily_cap"] = a.daily_cap
    if a.provider == "custom":
        if not a.smtp_host:
            raise SystemExit("ERROR: the custom provider requires --smtp-host")
        mb["smtp_host"] = a.smtp_host
        mb["smtp_port"] = a.smtp_port or 465
    data["mailboxes"].append(mb)
    data["_note"] = "Stores only the mailbox and the environment-variable name of the key, never the key itself; warmup_schedule is a conservative default of this skill and can be edited."
    save_mailboxes(data)
    print(f"Registered hosted mailbox {a.id} ({PROVIDERS[a.provider]['name']}, {a.user}) → {MAILBOX_FILE}")
    print(f"Put the key into the environment variable: export {pass_env}=<{PROVIDERS[a.provider]['secret'].split(' (')[0]}>")
    print(f"Verify: MAILBOX={a.id} python3 scripts/mail_setup.py test")


def cmd_list(_a):
    data = load_mailboxes()
    if not data["mailboxes"]:
        print("No hosted mailbox registered yet. A single mailbox can use the SMTP_* variables directly; register with add for multi-mailbox rotation.")
        return
    print(f"{'id':<12}{'status':<8}{'warm-up day':<12}{'cap today':<10}{'used':<6}{'left':<6}mailbox")
    for m in data["mailboxes"]:
        cap, dn = warmup_cap(m)
        used = used_today(m["id"])
        st = m.get("status", "active")
        print(f"{m['id']:<12}{st:<8}{dn:<10}{cap:<8}{used:<6}{max(0, cap - used):<6}{m['user']}"
              + (f"   [{m.get('paused_reason','')}]" if st != "active" else ""))
        if not os.environ.get(m.get("pass_env", "")):
            print(f"{'':<12}↳ environment variable {m.get('pass_env')} is not set (export it before a real send)")


def cmd_pick(_a):
    mb = pick_mailbox()
    if not mb:
        print("No hosted mailbox available today (quota used up or all paused).")
        sys.exit(1)
    print(f"Suggested for today: {mb['id']} ({mb['user']}, {remaining(mb)} left)")
    print(f"export MAILBOX={mb['id']}")


def cmd_test(a):
    if a.mailbox:
        os.environ["MAILBOX"] = a.mailbox
    r = resolve_sender_route()
    if not r["host"] or not r["user"] or not r["password"]:
        miss = r.get("pass_env") or "SMTP_HOST / SMTP_USER / SMTP_PASS"
        raise SystemExit(f"ERROR: credentials incomplete (missing {miss}). Run env <provider> or add, then export the key.")
    print(f"Testing SMTP login {r['host']}:{r['port']} as {r['user']} (no sending)…")
    ctx = ssl.create_default_context()
    try:
        if r["port"] == 465:
            s = smtplib.SMTP_SSL(r["host"], r["port"], context=ctx, timeout=20)
        else:
            s = smtplib.SMTP(r["host"], r["port"], timeout=20)
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
        s.login(r["user"], r["password"])
        s.quit()
        print("  SMTP login OK.")
    except smtplib.SMTPAuthenticationError as e:
        print(f"  SMTP authentication failed: {e.smtp_code} {e.smtp_error!r}")
        print("  Common causes: web login password used instead of the client key; IMAP/SMTP not enabled; admin has not enabled client protocols.")
        sys.exit(1)
    except Exception as e:
        print(f"  SMTP connection failed: {e}")
        sys.exit(1)
    ih = os.environ.get("IMAP_HOST")
    if not ih and r.get("mailbox_id"):
        ih = PROVIDERS.get(_find(load_mailboxes(), r["mailbox_id"]).get("provider"), {}).get("imap_host")
    if ih:
        try:
            m = imaplib.IMAP4_SSL(ih, int(os.environ.get("IMAP_PORT", "993")), ssl_context=ctx)
            m.login(os.environ.get("IMAP_USER") or r["user"], os.environ.get("IMAP_PASS") or r["password"])
            m.logout()
            print(f"  IMAP login OK ({ih}) — bounce scanning available.")
        except Exception as e:
            print(f"  IMAP login failed ({ih}): {e} — bounce scanning needs separate IMAP_* settings.")


def _query_txt(name, server):
    sys.path.insert(0, _HERE)
    import dns_validator as _dv
    tid, packet = _dv._build_query(name, qtype=16)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(_dv.TIMEOUT)
    try:
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    _, flags, qd, an, _, _ = struct.unpack(">HHHHHH", data[:12])
    off = 12
    for _ in range(qd):
        _, off = _dv._parse_name(data, off)
        off += 4
    out = []
    for _ in range(an):
        _, off = _dv._parse_name(data, off)
        rtype, _, _, rdlen = struct.unpack(">HHIH", data[off:off + 10])
        off += 10
        if rtype == 16:
            chunk, i, parts = data[off:off + rdlen], 0, []
            while i < len(chunk):
                ln = chunk[i]
                parts.append(chunk[i + 1:i + 1 + ln].decode("utf-8", "ignore"))
                i += 1 + ln
            out.append("".join(parts))
        off += rdlen
    return out


def _txt_doh(name):
    """DNS-over-HTTPS fallback (when UDP 53 is blocked): try the Cloudflare and Google JSON resolvers in turn."""
    import urllib.request
    import urllib.parse
    q = urllib.parse.urlencode({"name": name, "type": "TXT"})
    last = None
    for base in ("https://cloudflare-dns.com/dns-query?", "https://dns.google/resolve?"):
        try:
            req = urllib.request.Request(base + q, headers={"accept": "application/dns-json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
            return [a.get("data", "").replace('" "', "").strip('"')
                    for a in data.get("Answer", []) if a.get("type") == 16]
        except Exception as e:
            last = e
    raise last


def _txt(name):
    sys.path.insert(0, _HERE)
    import dns_validator as _dv
    for srv in _dv.DNS_SERVERS:
        try:
            res = _query_txt(name, srv.strip())
            if res:
                return res
        except Exception:
            continue
    try:
        return _txt_doh(name)
    except Exception:
        return None


def cmd_auth_check(a):
    d = a.domain.lower().strip()
    if os.environ.get("DRY_RUN") in ("1", "true", "yes"):
        print(f"[DRY_RUN] would query TXT: {d} (SPF), _dmarc.{d} (DMARC)"
              + (f", {a.selector}._domainkey.{d} (DKIM)" if a.selector else ""))
        return
    raw_spf, raw_dmarc = _txt(d), _txt("_dmarc." + d)
    if raw_spf is None and raw_dmarc is None:
        print(f"Sending domain: {d}\n  DNS lookup failed (both UDP 53 and DNS-over-HTTPS unreachable). Try another network, or read the TXT records in your DNS provider's console.")
        sys.exit(1)
    spf = [t for t in (raw_spf or []) if t.lower().startswith("v=spf1")]
    dmarc = [t for t in (raw_dmarc or []) if t.lower().startswith("v=dmarc1")]
    print(f"Sending domain: {d}")
    print(f"  SPF   : {'found → ' + spf[0] if spf else 'no v=spf1 record found'}")
    print(f"  DMARC : {'found → ' + dmarc[0] if dmarc else 'no _dmarc record found'}")
    if a.selector:
        dk = [t for t in (_txt(f"{a.selector}._domainkey.{d}") or []) if "p=" in t]
        print(f"  DKIM  : {'found (selector=' + a.selector + ')' if dk else 'no ' + a.selector + '._domainkey record found'}")
    else:
        print("  DKIM  : needs a selector (visible on your mailbox DKIM settings page); add --selector <name>")
    print("Gmail sender requirements: every sender needs at least SPF or DKIM; bulk senders (about 5,000+ messages a day to Gmail) need SPF + DKIM + DMARC. "
          "See references/mail_setup.md.")


def cmd_pause(a):
    data = load_mailboxes()
    mb = _find(data, a.id)
    if not mb:
        raise SystemExit(f"ERROR: no mailbox {a.id}")
    mb["status"] = "paused"
    mb["paused_reason"] = a.reason
    mb["paused_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save_mailboxes(data)
    print(f"Paused {a.id}: {a.reason}")


def cmd_resume(a):
    data = load_mailboxes()
    mb = _find(data, a.id)
    if not mb:
        raise SystemExit(f"ERROR: no mailbox {a.id}")
    mb["status"] = "active"
    mb.pop("paused_reason", None)
    save_mailboxes(data)
    print(f"Resumed {a.id} (make sure the bounce cause has been investigated)")


def cmd_mcp_export(a):
    r = json.load(open(a.report, encoding="utf-8-sig"))
    items = [x for x in r.get("sent", []) if x.get("dry_run") and x.get("email")]
    if not items:
        raise SystemExit("ERROR: the report contains no DRY_RUN items. Run batch_sender / decision_maker_sender with DRY_RUN=1 first.")
    out = [{"to": x["email"], "subject": x.get("subject", ""), "body": x.get("body", ""),
            "brand": x.get("brand", ""), "need_tag": x.get("need_tag", "open"),
            "approved": False, "status": "pending"} for x in items]
    path = a.out or os.path.join(os.path.dirname(a.report) or ".", "mcp_outbox.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Generated MCP sending list with {len(out)} items → {path}")
    print("Rules: the AI may only process items with approved=true (set by a human after checking each one); the connector creates drafts by default, "
          "and sends only with the user's explicit authorisation; after each item set status to drafted / sent, then run mcp-writeback.")


def cmd_mcp_writeback(a):
    items = json.load(open(a.outbox, encoding="utf-8-sig"))
    n = 0
    for x in items:
        if x.get("status") == "sent" and x.get("approved") and not x.get("written_back"):
            subprocess.run([sys.executable, os.path.join(_HERE, "csv_ops.py"), "add_sent", x["to"],
                            x.get("brand", ""), x.get("subject", ""), x.get("need_tag", "open"), "via:mcp"],
                           check=False, capture_output=True)
            x["written_back"] = True
            n += 1
    json.dump(items, open(a.outbox, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if n:
        record_usage("mcp", n, 0)
    print(f"Wrote {n} items back to sent_history (only approved=true and status=sent).")


def main():
    p = argparse.ArgumentParser(description="Sending-route takeover: enterprise mailbox keys / hosted multi-mailbox warm-up / MCP sending (v3.1)")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("providers").set_defaults(func=cmd_providers)
    pe = sub.add_parser("env")
    pe.add_argument("provider")
    pe.add_argument("--user", required=True)
    pe.set_defaults(func=cmd_env)
    pa = sub.add_parser("add")
    pa.add_argument("id")
    pa.add_argument("--provider", required=True)
    pa.add_argument("--user", required=True)
    pa.add_argument("--pass-env", dest="pass_env")
    pa.add_argument("--daily-cap", dest="daily_cap", type=int)
    pa.add_argument("--start")
    pa.add_argument("--smtp-host", dest="smtp_host")
    pa.add_argument("--smtp-port", dest="smtp_port", type=int)
    pa.set_defaults(func=cmd_add)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("pick").set_defaults(func=cmd_pick)
    pt = sub.add_parser("test")
    pt.add_argument("--mailbox")
    pt.set_defaults(func=cmd_test)
    pc = sub.add_parser("auth-check")
    pc.add_argument("domain")
    pc.add_argument("--selector")
    pc.set_defaults(func=cmd_auth_check)
    pp = sub.add_parser("pause")
    pp.add_argument("id")
    pp.add_argument("--reason", required=True)
    pp.set_defaults(func=cmd_pause)
    pr = sub.add_parser("resume")
    pr.add_argument("id")
    pr.set_defaults(func=cmd_resume)
    pm = sub.add_parser("mcp-export")
    pm.add_argument("report")
    pm.add_argument("--out")
    pm.set_defaults(func=cmd_mcp_export)
    pw = sub.add_parser("mcp-writeback")
    pw.add_argument("outbox")
    pw.set_defaults(func=cmd_mcp_writeback)
    a = p.parse_args()
    if not getattr(a, "cmd", None):
        p.print_help()
        sys.exit(0)
    a.func(a)


if __name__ == "__main__":
    main()
