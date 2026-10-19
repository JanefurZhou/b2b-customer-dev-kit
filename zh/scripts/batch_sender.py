#!/usr/bin/env python3
"""SMTP 批量发信脚本（零外部依赖，仅用 Python 标准库）

用法:
    python3 scripts/batch_sender.py [最大发信数] [输入文件.json] [报告目录]

输入 JSON（数组）:
[
  {
    "brand": "Brand A",
    "contact_person": "Hannah Smith",
    "title": "Buyer",
    "email": "hannah.smith@branda.example",
    "region": "UK",
    "need_tag": "line_a",
    "solution_tag": "compliance",
    "website": "https://branda.example",
    "subject": "Your subject line",
    "body": "邮件正文（若不提供，用内置的通用极简模板）"
  }
]

发信通道（三选一，详见 references/mail_setup.md）:
    A1 单邮箱：SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS 环境变量（mail_setup.py env <服务商> 生成）
    A2 多邮箱托管：mail_setup.py add 登记 → 未设 SMTP_HOST 时自动按剩余额度轮换；
       MAILBOX=<id> 指定某个；按预热上限限量；一轮退信超阈值自动暂停该邮箱
    B  MCP / 连接器：DRY_RUN=1 出报告 → mail_setup.py mcp-export → 人工逐条批准后由连接器建草稿/发送

SMTP 凭证（全部通过环境变量注入，脚本内不硬编码任何密钥）:
    SMTP_HOST     SMTP 服务器（如 smtp.your-mail-provider.com）
    SMTP_PORT     端口（默认 465，SSL）
    SMTP_USER     登录用户名 / 发件邮箱
    SMTP_PASS     登录密码 / 授权码
    SENDER_NAME   发件人显示名
    SENDER_TITLE  发件人职位
    SENDER_WA     WhatsApp 号码
    SENDER_WEBSITE 公司网站
    SENDER_COMPANY 公司名
    SEND_INTERVAL 发信间隔秒数（默认 30）
    DAILY_LIMIT   每日上限（默认 200）
    DRY_RUN       设为 1 时仅预览不真正发送
    UNSUBSCRIBE_URL  选填：一键退订 HTTPS 地址（配了才加 List-Unsubscribe-Post 一键退订头）
    OPT_OUT_LINE  选填：覆盖正文末尾的退订提示句；档案 rules.opt_out_line 设 "off" 可关闭
    SEND_WINDOW   收件人当地发信窗口（默认取档案 rules.local_send_window，再默认 09:00-11:00,14:00-16:00）
    SEND_WINDOW_ENFORCE  设 0 关闭当地时间窗口拦截（默认开启；联系人带 region/tz 才生效）

发信铁律:
    - 单 session 执行，禁止多 agent 并行
    - 通用邮箱（info@/contact@ 等）自动拦截，不发
    - 30 秒间隔防风控，每日上限 200 封
    - 发送成功后回写 sent_history；SMTP 拒收则记录，建议 24-48h 后跑 imap_scanner 扫退信
"""
import json, sys, os, ssl, smtplib, time, subprocess, datetime
import send_window as _sw  # 收件人当地发信窗口
import mail_setup as _ms   # 发信通道：单邮箱 / 多邮箱托管预热 / MCP
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import config as _cfg
except ImportError:
    _cfg = None

# 通用邮箱前缀黑名单（退信率极高，绝不发冷邮件）
# 全行业通用/职能邮箱前缀统一维护在 config.GENERIC_MAILBOX_PREFIXES
GENERIC_PREFIXES = set(_cfg.GENERIC_MAILBOX_PREFIXES) if _cfg is not None else {
    "info", "contact", "hello", "sales", "support", "admin", "office", "service",
}

# 多语种问候语（按 region 匹配；未命中用英文）
GREETINGS = {
    "IT": "Buongiorno", "DE": "Guten Tag", "FR": "Bonjour", "ES": "Hola",
    "JP": "こんにちは", "NL": "Goedendag", "PT": "Olá", "BR": "Olá",
}


def is_generic(email):
    local = email.split("@")[0].lower().strip()
    return local in GENERIC_PREFIXES


def env(key, default=""):
    return os.environ.get(key, default)


def first_name(contact, region=""):
    """Greeting name: first name only (\"Hannah Smith\" -> \"Hannah\").

    Honorifics are dropped. For JP the full name is kept, because the local
    convention is surname-based and the draft should be localised by a human.
    """
    contact = (contact or "").strip()
    if not contact:
        return ""
    if (region or "").upper() == "JP":
        return contact
    parts = [t for t in contact.replace(",", " ").split()
             if t.lower().rstrip(".") not in {"mr", "mrs", "ms", "miss", "dr", "prof", "sir", "madam"}]
    return parts[0] if parts else contact


def build_body(item, sender, profile):
    """若未提供 body，用 company_profile 的产品定位/卖点生成通用极简正文。

    本脚本不含任何具体行业话术；所有产品事实均取自建档时用户填写的
    product.* 字段。若 draft 已带 body（人工/AI 审核过的本地化邮件），原样使用。
    """
    if item.get("body"):
        return item["body"]
    region = (item.get("region") or "").upper()
    greeting = GREETINGS.get(region, "Hello")
    contact = first_name(item.get("contact_person"), region) or "there"
    brand = item.get("brand") or "your brand"

    one_liner = (profile.get("product", {}).get("one_liner_en") or "").strip()
    diffs = profile.get("product", {}).get("differentiators") or []

    lines = [f"{greeting} {contact},", ""]
    if one_liner:
        # No "came across" / "may be a fit" — both are on the banned list in
        # references/email_templates.md. State the offer, then the proof.
        lines.append(f"A quick note for the {brand} team: we provide {one_liner.rstrip('.')}.")
        lines.append("")
    for d in diffs[:3]:
        d = str(d).strip()
        if d:
            lines.append(f"- {d}")
    facts = list(_cfg.offer_facts(profile))   # offer.key_facts，兼容旧 moq/打样字段
    if facts and sender.get("wa"):
        facts.append(f"WhatsApp: {sender['wa']}")
    if facts:
        lines.append("")
        lines.append(". ".join(facts) + ".")
    lines += ["", _cfg.cta_question(profile), "", "Best,",
              _signature_line(sender, profile)]
    return "\n".join(lines)


def _signature_line(sender, profile):
    parts = [sender.get("name") or profile.get("contact", {}).get("founder_name", "")]
    company = sender.get("company") or profile.get("company", {}).get("brand_display", "")
    if company:
        parts = [(parts[0] + f" | {company}") if parts[0] else company]
    tail = []
    site = sender.get("website") or profile.get("company", {}).get("website", "")
    if site:
        tail.append(site)
    wa = sender.get("wa") or profile.get("contact", {}).get("whatsapp", "")
    if wa:
        tail.append(f"WhatsApp: {wa}")
    if tail:
        parts.append(" | ".join(tail))
    return " | ".join([p for p in parts if p])


DEFAULT_OPT_OUT = "If this isn't relevant for you, just reply \"no\" and I won't write again."


def opt_out_line(profile):
    v = os.environ.get("OPT_OUT_LINE") or (profile.get("rules", {}) or {}).get("opt_out_line") or DEFAULT_OPT_OUT
    return "" if str(v).strip().lower() == "off" else str(v).strip()


def with_opt_out(body, profile):
    """正文末尾补一句退订提示（已有则不重复）。演练报告里看到的就是最终正文。"""
    line = opt_out_line(profile)
    if not line or line.lower() in body.lower():
        return body
    return body.rstrip() + "\n\n" + line


def compose(subject, body, sender_name, from_addr, to_addr):
    """纯文本邮件 + 退订头（mailto；配了 UNSUBSCRIBE_URL 再加一键退订）。"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(sender_name, "utf-8")), from_addr))
    msg["To"] = to_addr
    lu = [f"<mailto:{from_addr}?subject=unsubscribe>"] if from_addr else []
    url = os.environ.get("UNSUBSCRIBE_URL", "").strip()
    if url.startswith("https://"):
        lu.insert(0, f"<{url}>")
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    if lu:
        msg["List-Unsubscribe"] = ", ".join(lu)
    return msg


def csv_ops(args, data_dir):
    """调用同目录 csv_ops.py 回写数据。"""
    here = os.path.dirname(os.path.abspath(__file__))
    env2 = dict(os.environ)
    if data_dir:
        env2["B2B_DATA_DIR"] = data_dir
    try:
        subprocess.run([sys.executable, os.path.join(here, "csv_ops.py"), *args],
                       env=env2, check=False, capture_output=True)
    except Exception as e:
        print(f"  WARN: csv_ops 回写失败: {e}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)
    if len(sys.argv) > 1:
        try:
            max_send = int(sys.argv[1])
            if max_send <= 0:
                raise ValueError
        except ValueError:
            print(f"ERROR: 第 1 个参数应为最大发信数（正整数），收到的是「{sys.argv[1]}」。\n"
                  "用法: python3 scripts/batch_sender.py [最大发信数] [输入文件.json] [报告目录]\n"
                  "例如: DRY_RUN=1 python3 scripts/batch_sender.py 20 drafts.json reports")
            sys.exit(1)
    else:
        max_send = int(env("DAILY_LIMIT", "200"))
    infile = sys.argv[2] if len(sys.argv) > 2 else "candidates.json"
    report_dir = sys.argv[3] if len(sys.argv) > 3 else "reports"
    data_dir = env("B2B_DATA_DIR", "data")
    dry_run = env("DRY_RUN", "") in ("1", "true", "yes")

    # 首次配置门禁：未建档/未填齐 → 拒绝发送（DRY_RUN 也不允许，避免发出空模板）
    if _cfg is not None:
        try:
            profile = _cfg.load_profile(require_complete=True)
        except _cfg.ProfileNotConfigured as e:
            print("ERROR: 公司档案未就绪，禁止发送。\n" + str(e))
            sys.exit(2)
    else:
        print("ERROR: 找不到 config.py 配置门禁，拒绝发送。")
        sys.exit(2)

    _co = profile.get("company", {})
    _ct = profile.get("contact", {})
    profile_limit = profile.get("rules", {}).get("daily_limit")
    daily_limit = int(env("DAILY_LIMIT", str(profile_limit or 200)))
    max_send = min(max_send, daily_limit)
    interval = float(env("SEND_INTERVAL", "30"))

    # 环境变量优先；未设时回落到建档档案；仍为空才留空（不再用虚构占位）
    sender = {
        "name": env("SENDER_NAME") or _ct.get("founder_name", ""),
        "title": env("SENDER_TITLE") or _ct.get("founder_title", ""),
        "wa": env("SENDER_WA") or _ct.get("whatsapp", ""),
        "website": env("SENDER_WEBSITE") or _co.get("website", ""),
        "company": env("SENDER_COMPANY") or _co.get("brand_display", ""),
    }

    if not os.path.exists(infile):
        print(f"ERROR: 找不到输入文件「{infile}」。请传入草稿清单 JSON（数组，见脚本顶部说明）。")
        sys.exit(1)
    try:
        with open(infile, encoding="utf-8-sig") as f:
            items = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: 输入文件「{infile}」不是合法 JSON：{e}")
        sys.exit(1)
    if isinstance(items, dict):
        items = items.get("records", items.get("items", []))

    route = _ms.resolve_sender_route()
    host, port, user, password = route["host"], route["port"], route["user"], route["password"]
    mailbox_id = route["mailbox_id"]
    if route["cap"] is not None:
        max_send = min(max_send, route["cap"])
        print(f"托管邮箱 {mailbox_id}（{user}）：今日预热剩余 {route['cap']} 封 → 本轮上限 {max_send}")

    if not dry_run and (not host or not user or not password):
        print("ERROR: 缺少 SMTP 凭证（SMTP_HOST / SMTP_USER / SMTP_PASS，或托管邮箱的 "
              f"{route.get('pass_env') or '密钥环境变量'}）。请先 export，或设 DRY_RUN=1 预览。"
              "配置向导：python3 scripts/mail_setup.py providers")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)
    _win = _sw.window_spec(profile)
    report = {"sent": [], "skipped_generic": [], "failed": [], "started_at": datetime.datetime.now().isoformat()}

    server = None
    if not dry_run:
        # 合规：拒绝明文投递。仅允许 465(SSL) 或 587/其它端口 + 强制 STARTTLS。
        # 端口 25 常为明文，禁止用于带凭证的外发。
        if port == 25:
            print("ERROR: 端口 25 为明文 SMTP，禁止用于带凭证的外发。请用 465(SSL) 或 587(STARTTLS)。")
            sys.exit(1)
        ctx = ssl.create_default_context()  # 默认校验证书与主机名
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            if not server.has_extn("starttls"):
                print("ERROR: 服务器不支持 STARTTLS，拒绝明文发送凭证。请改用 465(SSL) 端口。")
                try:
                    server.quit()
                except Exception:
                    pass
                sys.exit(1)
            server.starttls(context=ctx)
            server.ehlo()
        server.login(user, password)

    count = 0
    seen_emails = set()
    report["skipped_duplicate"] = []
    try:
        for item in items:
            if count >= max_send:
                print(f"已达上限 {max_send} 封，停止。")
                break
            email = (item.get("email") or "").strip().lower()
            if not email or "@" not in email:
                report["failed"].append({"email": email, "reason": "invalid_email"})
                continue
            if is_generic(email):
                report["skipped_generic"].append(email)
                print(f"  跳过通用邮箱: {email}")
                continue
            if email in seen_emails:
                report["skipped_duplicate"].append(email)
                print(f"  跳过重复收件人（本批已出现过）: {email}")
                continue
            seen_emails.add(email)
            # 收件人当地发信窗口（rules.local_send_window；工作日）——窗口外本轮跳过，下轮再发
            _ok, _wi = _sw.in_window(item.get("region", ""), _win, item.get("tz", ""))
            if _ok is False and _sw.enforce_enabled():
                if dry_run:
                    item["_window_note"] = f"outside window ({_wi.get('local_time')} {_wi.get('tz')}) — real run would defer"
                else:
                    report.setdefault("deferred_window", []).append({"email": email, **_wi})
                    print(f"  延后（收件人当地 {_wi.get('local_time')} 不在窗口 {_win}）: {email}")
                    continue

            subject = item.get("subject") or f"Hello from {sender['company']}".strip()
            body = with_opt_out(build_body(item, sender, profile), profile)
            _ph = _cfg.find_placeholder_text(subject + "\n" + body)
            if _ph:
                report.setdefault("skipped_placeholder", []).append({"email": email, "placeholders": _ph})
                print(f"  拦截（正文/主题残留模板占位符 {', '.join(_ph)}）: {email}")
                continue
            from_addr = user or _ct.get("email") or ""
            msg = compose(subject, body, sender["name"], from_addr, email)

            if dry_run:
                print(f"[DRY_RUN] → {email} | {subject}")
                report["sent"].append({"email": email, "brand": item.get("brand", ""), "dry_run": True,
                                       "need_tag": item.get("need_tag", "open"),
                                       "subject": subject, "body": body,
                                       "window": item.get("_window_note", "ok")})
                count += 1
                continue

            try:
                server.sendmail(user, [email], msg.as_string())
                report["sent"].append({"email": email, "brand": item.get("brand", "")})
                csv_ops(["add_sent", email, item.get("brand", ""), subject,
                         item.get("need_tag", "open")], data_dir)
                print(f"  已发送 → {email}")
                count += 1
            except smtplib.SMTPRecipientsRefused:
                report["failed"].append({"email": email, "reason": "recipient_refused"})
                csv_ops(["mark_bounced", email], data_dir)
                print(f"  拒收(疑似退信) → {email}，已标记 bounced")
            except Exception as e:
                report["failed"].append({"email": email, "reason": str(e)})
                print(f"  发送失败 → {email}: {e}")

            time.sleep(interval)
    finally:
        if server:
            server.quit()

    if not dry_run and mailbox_id:
        _real = len([x for x in report["sent"] if not x.get("dry_run")])
        _bounced = len([x for x in report["failed"] if x.get("reason") == "recipient_refused"])
        _ms.record_usage(mailbox_id, _real, _bounced)
        if _ms.maybe_auto_pause(mailbox_id, _real, _bounced):
            print(f"[!] 托管邮箱 {mailbox_id} 本轮退信偏高，已自动暂停。排查名单质量后 mail_setup.py resume {mailbox_id}。")
        report["mailbox"] = mailbox_id

    report["finished_at"] = datetime.datetime.now().isoformat()
    report["summary"] = {
        "sent": len(report["sent"]),
        "skipped_generic": len(report["skipped_generic"]),
        "skipped_duplicate": len(report["skipped_duplicate"]),
        "failed": len(report["failed"]),
        "deferred_window": len(report.get("deferred_window", [])),
    }
    rpath = os.path.join(report_dir, f"batch_report_{datetime.date.today().isoformat()}.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    label = "演练（未真实发送）" if dry_run else "发送"
    print(f"\n完成：{label} {len(report['sent'])}，跳过通用邮箱 {len(report['skipped_generic'])}，"
          f"跳过重复 {len(report['skipped_duplicate'])}，失败 {len(report['failed'])}。报告 → {rpath}")
    if dry_run:
        print("演练报告里已附每封的主题与正文，请逐条核对后再去掉 DRY_RUN 真发。")
    print("建议 24-48 小时后运行 imap_scanner.py 扫描退信。")


if __name__ == "__main__":
    main()
