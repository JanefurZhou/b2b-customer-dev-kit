#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mail_setup.py — 发信通道接管：企业邮箱密钥 / 多邮箱托管 / 预热爬坡 / MCP 发信通道（技能版本 v3.1）

两条发信路径（二选一，也可并存）
--------------------------------
路径 A · 企业邮箱 + 密钥（国内最常见）
    腾讯企业邮 / 阿里企业邮 / 网易企业邮 / Gmail·Workspace / Microsoft 365 / 自定义 SMTP。
    「密钥」= 邮箱后台生成的 客户端专用密码 / 三方客户端安全密码 / 客户端授权码 / 应用专用密码，
    不是网页登录密码。密钥只放环境变量，本脚本和任何配置文件都不保存明文。
路径 B · MCP / 平台连接器
    运行环境已接入 Gmail / Outlook 等邮件连接器或邮件 MCP 时：
    DRY_RUN 出演练报告 → 人工逐条核对 → mcp-export 生成 outbox → 由 AI 调连接器建草稿/发送
    → mcp-writeback 回写 sent_history。脚本本身不调用任何 MCP，也不绕过人工确认。

子命令
------
  providers                         列出内置服务商预设（服务器/端口/密钥叫法/在哪生成）
  env <provider> --user <邮箱>       打印要 export 的环境变量（密钥一行留空，你自己填）
  add <id> --provider <p> --user <邮箱> [--pass-env 变量名] [--daily-cap N] [--start YYYY-MM-DD]
                                    登记一个托管邮箱到 config/mailboxes.json（只存变量名，不存密钥）
  list                              每个托管邮箱：状态 / 今日预热上限 / 今日已用 / 剩余
  pick                              按剩余额度挑今天该用的邮箱（轮换），打印 export 行
  test [--mailbox id]               只登录 SMTP（+IMAP）验证密钥，不发任何邮件
  auth-check <域名> [--selector s]  查发件域 SPF / DMARC / DKIM 的 DNS TXT 记录（只读）
  pause <id> --reason <原因> / resume <id>
  mcp-export <演练报告.json> [--out reports/mcp_outbox.json]
  mcp-writeback <mcp_outbox.json>   把 outbox 里 status=sent 的条目回写 sent_history

预热爬坡与自动暂停
------------------
  每个托管邮箱有 warmup_schedule（从第几天起 → 每日上限）。内置默认是一组「保守起步值」，
  属于本技能的可调默认，不是任何服务商公布的数字；服务商若对你的账户有明确额度，以服务商为准。
  batch_sender / decision_maker_sender 在 MAILBOX 模式下会取 min(档案 daily_limit, 预热上限 − 今日已用)，
  一轮内退信占比超过 bounce_pause_rate（默认 0.05，可改）即自动把该邮箱置为 paused。
零第三方依赖。
"""

import os
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
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

# 服务商预设：数值均来自服务商官方帮助文档（见 references/mail_setup.md 的出处列）
PROVIDERS = {
    "tencent_exmail": {
        "name": "腾讯企业邮箱",
        "smtp_host": "smtp.exmail.qq.com", "smtp_port": 465,
        "imap_host": "imap.exmail.qq.com", "imap_port": 993,
        "overseas": "海外节点 hwsmtp.exmail.qq.com / hwimap.exmail.qq.com",
        "secret": "客户端专用密码（开启安全登录后必须用）",
        "where": "网页版邮箱 → 设置 → 邮箱绑定 → 客户端专用密码；并在 收发信设置 开启 IMAP/SMTP 服务",
    },
    "aliyun_qiye": {
        "name": "阿里企业邮箱",
        "smtp_host": "smtp.qiye.aliyun.com", "smtp_port": 465,
        "imap_host": "imap.qiye.aliyun.com", "imap_port": 993,
        "overseas": "香港节点 smtphk.qiye.aliyun.com / imaphk.qiye.aliyun.com",
        "secret": "三方客户端安全密码",
        "where": "网页版邮箱 → 设置 → 账户与安全 → 账户安全 → 三方客户端安全密码",
    },
    "netease_qiye": {
        "name": "网易企业邮箱",
        "smtp_host": "smtphz.qiye.163.com", "smtp_port": 465,
        "imap_host": "imaphz.qiye.163.com", "imap_port": 993,
        "overseas": "",
        "secret": "客户端授权码（只显示一次，务必当场保存）",
        "where": "网页版邮箱 → 设置 → 账户与安全 → 客户端设置 → 生成授权码；管理员需已开放客户端协议",
    },
    "gmail": {
        "name": "Gmail / Google Workspace",
        "smtp_host": "smtp.gmail.com", "smtp_port": 465,
        "imap_host": "imap.gmail.com", "imap_port": 993,
        "overseas": "也可用 587 + STARTTLS",
        "secret": "应用专用密码（需先开两步验证；改账户密码后会被吊销）",
        "where": "Google 账户 → 安全 → 两步验证 → 应用专用密码；Google 更推荐 OAuth / 连接器（路径 B）",
    },
    "microsoft365": {
        "name": "Microsoft 365 / Exchange Online",
        "smtp_host": "smtp.office365.com", "smtp_port": 587,
        "imap_host": "", "imap_port": 993,
        "overseas": "IMAP 收信/退信扫描建议走 OAuth 或连接器（路径 B）；本预设不填 IMAP",
        "secret": "SMTP AUTH 基本认证（账户密码）——微软已公布逐步停用时间表，建议走 OAuth / 连接器（路径 B）",
        "where": "管理员需为该邮箱开启 SMTP AUTH；2026 年 12 月底起现有租户默认关闭基本认证",
    },
    "custom": {
        "name": "自定义 SMTP",
        "smtp_host": "", "smtp_port": 465, "imap_host": "", "imap_port": 993,
        "overseas": "", "secret": "服务商给的 SMTP 密码 / 授权码", "where": "看你的邮件服务商帮助文档",
    },
}

# 保守起步值（本技能可调默认，非服务商公布数字）：[从第 N 天起, 每日上限]
DEFAULT_WARMUP = [[1, 20], [8, 40], [15, 80], [22, 150], [29, 200]]
DEFAULT_BOUNCE_PAUSE_RATE = 0.05


# ---------------- 托管邮箱配置 ----------------
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
    """一轮内退信占比超阈值 → 自动暂停该邮箱（保护性动作，恢复需人工 resume）。"""
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
        mb["paused_reason"] = f"auto: 本轮退信 {bounced}/{total} > {rate:.0%}"
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
    """供发信脚本调用：返回 dict(host, port, user, password, mailbox_id, cap)。

    优先级：MAILBOX=<id>（指定托管邮箱）> 有 config/mailboxes.json 且未设 SMTP_HOST（自动轮换）
            > 直接用 SMTP_HOST/SMTP_USER/SMTP_PASS 环境变量（cap=None 表示不额外限额）。
    """
    want = os.environ.get("MAILBOX", "").strip()
    data = load_mailboxes()
    mb = None
    if want:
        mb = _find(data, want)
        if mb is None:
            raise SystemExit(f"ERROR: MAILBOX={want} 不在 {MAILBOX_FILE}；先 mail_setup.py add 登记。")
        if mb.get("status", "active") != "active":
            raise SystemExit(f"ERROR: 邮箱 {want} 已暂停（{mb.get('paused_reason','')}）。人工排查后 mail_setup.py resume {want}。")
    elif data["mailboxes"] and not os.environ.get("SMTP_HOST"):
        mb = pick_mailbox(data)
        if mb is None:
            raise SystemExit("ERROR: 所有托管邮箱今日额度已用完或已暂停。mail_setup.py list 查看。")
    if mb is None:
        return {"host": os.environ.get("SMTP_HOST", ""), "port": int(os.environ.get("SMTP_PORT", "465")),
                "user": os.environ.get("SMTP_USER", ""), "password": os.environ.get("SMTP_PASS", ""),
                "mailbox_id": "", "cap": None}
    prov = PROVIDERS.get(mb.get("provider", "custom"), PROVIDERS["custom"])
    return {"host": mb.get("smtp_host") or prov["smtp_host"],
            "port": int(mb.get("smtp_port") or prov["smtp_port"]),
            "user": mb["user"], "password": os.environ.get(mb.get("pass_env", ""), ""),
            "mailbox_id": mb["id"], "cap": remaining(mb), "pass_env": mb.get("pass_env", "")}


# ---------------- 子命令 ----------------
def cmd_providers(_a):
    for pid, p in PROVIDERS.items():
        print(f"[{pid}] {p['name']}")
        print(f"   SMTP {p['smtp_host'] or '<你的服务器>'}:{p['smtp_port']}   IMAP {p['imap_host'] or '<你的服务器>'}:{p['imap_port']}")
        if p["overseas"]:
            print(f"   {p['overseas']}")
        print(f"   密钥：{p['secret']}")
        print(f"   在哪生成：{p['where']}")
    print("出处与注意事项：references/mail_setup.md")


def cmd_env(a):
    p = PROVIDERS.get(a.provider)
    if not p:
        raise SystemExit(f"ERROR: 未知服务商 {a.provider}，可选 {list(PROVIDERS)}")
    print(f"# {p['name']} —— 复制到终端执行（密钥那行自己填，不要写进任何文件或聊天记录）")
    print(f"export SMTP_HOST={p['smtp_host'] or '<你的SMTP服务器>'}")
    print(f"export SMTP_PORT={p['smtp_port']}")
    print(f"export SMTP_USER={a.user}")
    print("export SMTP_PASS=  # ← 粘贴" + p["secret"].split("（")[0])
    print(f"export IMAP_HOST={p['imap_host'] or '<你的IMAP服务器>'}")
    print(f"export IMAP_PORT={p['imap_port']}")
    print("# 然后：python3 scripts/mail_setup.py test   （只登录验证，不发信）")


def cmd_add(a):
    if a.provider not in PROVIDERS:
        raise SystemExit(f"ERROR: 未知服务商 {a.provider}，可选 {list(PROVIDERS)}")
    data = load_mailboxes()
    if _find(data, a.id):
        raise SystemExit(f"ERROR: 邮箱 id {a.id} 已存在。")
    pass_env = a.pass_env or ("MAILBOX_PASS_" + a.id.upper().replace("-", "_"))
    mb = {"id": a.id, "provider": a.provider, "user": a.user, "pass_env": pass_env,
          "start_date": a.start or datetime.date.today().isoformat(),
          "warmup_schedule": DEFAULT_WARMUP, "status": "active",
          "bounce_pause_rate": DEFAULT_BOUNCE_PAUSE_RATE}
    if a.daily_cap:
        mb["daily_cap"] = a.daily_cap
    if a.provider == "custom":
        if not a.smtp_host:
            raise SystemExit("ERROR: custom 服务商需要 --smtp-host")
        mb["smtp_host"] = a.smtp_host
        mb["smtp_port"] = a.smtp_port or 465
    data["mailboxes"].append(mb)
    data["_note"] = "只存邮箱与密钥的环境变量名，不存密钥本身；warmup_schedule 为本技能保守默认值，可改。"
    save_mailboxes(data)
    print(f"已登记托管邮箱 {a.id}（{PROVIDERS[a.provider]['name']}，{a.user}）→ {MAILBOX_FILE}")
    print(f"把密钥放进环境变量：export {pass_env}=<{PROVIDERS[a.provider]['secret'].split('（')[0]}>")
    print(f"验证：MAILBOX={a.id} python3 scripts/mail_setup.py test")


def cmd_list(_a):
    data = load_mailboxes()
    if not data["mailboxes"]:
        print("尚未登记托管邮箱。单邮箱可直接用 SMTP_* 环境变量；多邮箱轮换用 add 登记。")
        return
    print(f"{'id':<12}{'状态':<8}{'预热第N天':<10}{'今日上限':<8}{'已用':<6}{'剩余':<6}邮箱")
    for m in data["mailboxes"]:
        cap, dn = warmup_cap(m)
        used = used_today(m["id"])
        st = m.get("status", "active")
        print(f"{m['id']:<12}{st:<8}{dn:<10}{cap:<8}{used:<6}{max(0, cap - used):<6}{m['user']}"
              + (f"   [{m.get('paused_reason','')}]" if st != "active" else ""))
        if not os.environ.get(m.get("pass_env", "")):
            print(f"{'':<12}↳ 环境变量 {m.get('pass_env')} 未设置（真发前需 export）")


def cmd_pick(_a):
    mb = pick_mailbox()
    if not mb:
        print("今天没有可用托管邮箱（额度用完或全部暂停）。")
        sys.exit(1)
    print(f"今日建议使用：{mb['id']}（{mb['user']}，剩余 {remaining(mb)} 封）")
    print(f"export MAILBOX={mb['id']}")


def cmd_test(a):
    if a.mailbox:
        os.environ["MAILBOX"] = a.mailbox
    r = resolve_sender_route()
    if not r["host"] or not r["user"] or not r["password"]:
        miss = r.get("pass_env") or "SMTP_HOST / SMTP_USER / SMTP_PASS"
        raise SystemExit(f"ERROR: 凭证不全（缺 {miss}）。先 env <provider> 或 add 登记后 export 密钥。")
    print(f"测试登录 SMTP {r['host']}:{r['port']} as {r['user']}（不发信）…")
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
        print("  SMTP 登录成功。")
    except smtplib.SMTPAuthenticationError as e:
        print(f"  SMTP 认证失败：{e.smtp_code} {e.smtp_error!r}")
        print("  常见原因：用了网页登录密码而不是客户端密钥；未开启 IMAP/SMTP 服务；管理员未开放客户端协议。")
        sys.exit(1)
    except Exception as e:
        print(f"  SMTP 连接失败：{e}")
        sys.exit(1)
    ih = os.environ.get("IMAP_HOST")
    if not ih and r.get("mailbox_id"):
        ih = PROVIDERS.get(_find(load_mailboxes(), r["mailbox_id"]).get("provider"), {}).get("imap_host")
    if ih:
        try:
            m = imaplib.IMAP4_SSL(ih, int(os.environ.get("IMAP_PORT", "993")), ssl_context=ctx)
            m.login(os.environ.get("IMAP_USER") or r["user"], os.environ.get("IMAP_PASS") or r["password"])
            m.logout()
            print(f"  IMAP 登录成功（{ih}）——退信扫描可用。")
        except Exception as e:
            print(f"  IMAP 登录失败（{ih}）：{e}——退信扫描需另配 IMAP_*。")


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
    """DNS-over-HTTPS 兜底（网络屏蔽 UDP 53 时）：依次试 Cloudflare / Google 的 JSON 解析接口。"""
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
        print(f"[DRY_RUN] 将查询 TXT：{d}（SPF）、_dmarc.{d}（DMARC）"
              + (f"、{a.selector}._domainkey.{d}（DKIM）" if a.selector else ""))
        return
    raw_spf, raw_dmarc = _txt(d), _txt("_dmarc." + d)
    if raw_spf is None and raw_dmarc is None:
        print(f"发件域：{d}\n  DNS 查询失败（UDP 53 与 DNS-over-HTTPS 都不通）。换个网络再试，或在域名服务商后台直接看 TXT 记录。")
        sys.exit(1)
    spf = [t for t in (raw_spf or []) if t.lower().startswith("v=spf1")]
    dmarc = [t for t in (raw_dmarc or []) if t.lower().startswith("v=dmarc1")]
    print(f"发件域：{d}")
    print(f"  SPF   : {'有 → ' + spf[0] if spf else '未找到 v=spf1 记录'}")
    print(f"  DMARC : {'有 → ' + dmarc[0] if dmarc else '未找到 _dmarc 记录'}")
    if a.selector:
        dk = [t for t in (_txt(f"{a.selector}._domainkey.{d}") or []) if "p=" in t]
        print(f"  DKIM  : {'有（selector=' + a.selector + '）' if dk else '未找到 ' + a.selector + '._domainkey 记录'}")
    else:
        print("  DKIM  : 需要 selector 才能查（在邮箱后台 DKIM 设置页能看到），加 --selector <名字>")
    print("Gmail 发件人要求：所有发件人至少 SPF 或 DKIM；每天给 Gmail 发约 5000 封以上的批量发件人需 SPF+DKIM+DMARC。"
          "详见 references/mail_setup.md。")


def cmd_pause(a):
    data = load_mailboxes()
    mb = _find(data, a.id)
    if not mb:
        raise SystemExit(f"ERROR: 无邮箱 {a.id}")
    mb["status"] = "paused"
    mb["paused_reason"] = a.reason
    mb["paused_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save_mailboxes(data)
    print(f"已暂停 {a.id}：{a.reason}")


def cmd_resume(a):
    data = load_mailboxes()
    mb = _find(data, a.id)
    if not mb:
        raise SystemExit(f"ERROR: 无邮箱 {a.id}")
    mb["status"] = "active"
    mb.pop("paused_reason", None)
    save_mailboxes(data)
    print(f"已恢复 {a.id}（请确认退信原因已排查）")


def cmd_mcp_export(a):
    r = json.load(open(a.report, encoding="utf-8-sig"))
    items = [x for x in r.get("sent", []) if x.get("dry_run") and x.get("email")]
    if not items:
        raise SystemExit("ERROR: 报告里没有 DRY_RUN 条目。先 DRY_RUN=1 跑 batch_sender / decision_maker_sender。")
    out = [{"to": x["email"], "subject": x.get("subject", ""), "body": x.get("body", ""),
            "brand": x.get("brand", ""), "need_tag": x.get("need_tag", "open"),
            "approved": False, "status": "pending"} for x in items]
    path = a.out or os.path.join(os.path.dirname(a.report) or ".", "mcp_outbox.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"已生成 MCP 发信清单 {len(out)} 条 → {path}")
    print("规则：AI 只能处理 approved=true 的条目（人工逐条核对后改）；默认用连接器「建草稿」，"
          "用户明确授权后才「发送」；每条处理后把 status 改为 drafted / sent，再跑 mcp-writeback。")


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
    print(f"已回写 sent_history {n} 条（只处理 approved=true 且 status=sent 的条目）。")


def main():
    p = argparse.ArgumentParser(description="发信通道接管：企业邮箱密钥 / 多邮箱托管预热 / MCP 发信（v3.1）")
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
