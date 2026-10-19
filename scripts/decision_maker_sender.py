#!/usr/bin/env python3
"""决策人具名发信脚本（零外部依赖，仅用 Python 标准库）

用法:
    python3 scripts/decision_maker_sender.py <联系人清单.json> [报告目录]

输入 JSON（数组，需含决策人姓名与职位）:
[
  {
    "brand": "Brand A",
    "contact_person": "Hannah Smith",
    "title": "Head of Buying",
    "email": "hannah.smith@branda.example",
    "region": "UK",
    "need_tag": "line_a",
    "solution_tag": "compliance",
    "website": "https://branda.example"
  }
]

与 batch_sender 的区别:
    - 强制要求具名决策人（无 contact_person 直接跳过，不发通用邮箱）
    - 根据 solution_tag（决策驱动，见 config.DRIVER_TAGS；缺省回落 hook_type / need_tag）选择钩子开场白
    - 根据 region 生成整封母语本地化问候 + 结尾
    - 通用邮箱自动拦截（25+ 前缀黑名单，复用 batch_sender）

SMTP 凭证同 batch_sender，全部走环境变量（SMTP_HOST/PORT/USER/PASS 等），脚本内不硬编码。
设 DRY_RUN=1 可仅预览不发送。
联系人带 region（或 tz）时按收件人当地发信窗口发送（SEND_WINDOW / rules.local_send_window，
工作日 09:00-11:00,14:00-16:00 为默认），窗口外本轮延后；SEND_WINDOW_ENFORCE=0 可关闭。
"""
import json, sys, os, ssl, smtplib, time, subprocess, datetime, importlib.util
import send_window as _sw  # 收件人当地发信窗口
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("batch_sender", os.path.join(_here, "batch_sender.py"))
_bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bs)

def build_hook(tag, profile):
    """按「决策驱动」标签生成开场钩子（英文基线，本地化时翻译）。

    行业无关：只引用 company_profile 里的定位与卖点。tag 取 solution_tag / hook_type /
    need_tag 中的决策驱动值（见 config.DRIVER_TAGS），旧版 eco_only/traditional 等
    会自动映射。profile.positioning.hooks.<tag> 可覆盖任意一句（可用 {one}/{lead}/{second}）。
    """
    p = profile.get("product", {})
    one = (p.get("one_liner_en") or "").strip().rstrip(".")
    diffs = [str(d).strip().rstrip(".") for d in (p.get("differentiators") or []) if str(d).strip()]
    cap = lambda t: (t[0].upper() + t[1:]) if t else t
    lead = cap(diffs[0]) if diffs else one
    second = cap(diffs[1]) if len(diffs) > 1 else ""
    driver = _bs._cfg.normalize_driver(tag)
    custom = ((profile.get("positioning") or {}).get("hooks") or {}).get(driver)
    if custom:
        return custom.format(one=one, lead=lead, second=second)
    tail = f" {lead}." if lead and lead != one else ""
    entry = ((profile.get("offer") or {}).get("entry_offer") or "").strip().rstrip(".")
    both = f" {lead}; {second}." if second else tail
    table = {
        "compliance":        f"Compliance is clearly a priority for your team. We provide {one}, with documentation available up front.{tail}",
        "sustainability":    f"Your sustainability commitments stood out. We provide {one}, built to support them.{tail}",
        "quality_upgrade":   f"A step up for what you already offer: {one}.{both}",
        "cost":              f"A more efficient option for your team: {one}.{tail}",
        "speed":             f"If timing matters on your side: {one}.{tail}",
        "low_commitment":    (f"An easy way to test us without a big commitment: {entry}. We provide {one}."
                              if entry else f"An easy way to test us without a big commitment: {one}.{tail}"),
        "innovation":        f"For the new direction you're taking: {one}.{tail}",
        "exclusive_custom":  f"Built around your requirements, not off the shelf: {one}.{tail}",
        "one_stop":          f"One partner instead of several: {one}.{both}",
        "dedicated_service": f"A direct line to the people doing the work: {one}.{tail}",
        "strategic_scale":   f"Capacity and planning for teams your size: {one}.{both}",
        "open":              f"A quick note for your team: we provide {one}.{tail}",
        "unknown":           f"A quick note for your team: we provide {one}.{tail}",
    }
    return table.get(driver, table["unknown"])

# region → (问候, 结尾敬语)
LOCALE = {
    "IT": ("Buongiorno", "Cordiali saluti"),
    "DE": ("Guten Tag", "Mit freundlichen Grüßen"),
    "FR": ("Bonjour", "Cordialement"),
    "ES": ("Hola", "Un cordial saludo"),
    "JP": ("拝啓", "敬具"),
    "NL": ("Goedendag", "Met vriendelijke groet"),
    "PT": ("Olá", "Atenciosamente"),
    "BR": ("Olá", "Atenciosamente"),
}


def build_named_body(item, sender, profile):
    region = (item.get("region") or "").upper()
    greeting, signoff = LOCALE.get(region, ("Hello", "Best regards"))
    contact = _bs.first_name(item.get("contact_person", ""), region)
    salutation = f"{greeting} {contact}" if contact else greeting
    hook = build_hook(item.get("solution_tag") or item.get("hook_type") or item.get("need_tag", "unknown"),
                      profile)
    facts = list(_bs._cfg.offer_facts(profile))
    if sender.get("wa"):
        facts.append(f"WhatsApp: {sender['wa']}")
    fact_line = ". ".join(facts) + ("." if facts else "")
    # _signature_line already starts with the sender name; add the title once, after it.
    sig = _bs._signature_line(sender, profile)
    name = sender.get("name") or ""
    if sender.get("title") and name and sig.startswith(name):
        sig = f"{name}, {sender['title']}" + sig[len(name):]
    parts = [f"{salutation},", hook]
    if fact_line:
        parts.append(fact_line)
    if "?" not in hook:  # templates require a short, answerable question ending
        parts.append(_bs._cfg.cta_question(profile))
    parts.append(f"{signoff},\n{sig}")
    return "\n\n".join(parts)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 1)
    infile = sys.argv[1]
    if not os.path.exists(infile):
        print(f"ERROR: 找不到联系人清单「{infile}」。\n"
              "用法: python3 scripts/decision_maker_sender.py <联系人清单.json> [报告目录]")
        sys.exit(1)
    report_dir = sys.argv[2] if len(sys.argv) > 2 else "reports"
    data_dir = _bs.env("B2B_DATA_DIR", "data")
    dry_run = _bs.env("DRY_RUN", "") in ("1", "true", "yes")
    interval = float(_bs.env("SEND_INTERVAL", "30"))
    max_send = int(_bs.env("DAILY_LIMIT", "200"))

    # 首次配置门禁
    try:
        profile = _bs._cfg.load_profile(require_complete=True)
    except Exception as e:
        print("ERROR: 公司档案未就绪，禁止发送。\n" + str(e))
        sys.exit(2)
    _co = profile.get("company", {})
    _ct = profile.get("contact", {})
    # 每日上限与 batch_sender 一致：DAILY_LIMIT 环境变量 > 档案 rules.daily_limit > 200
    _pl = profile.get("rules", {}).get("daily_limit")
    max_send = int(_bs.env("DAILY_LIMIT", str(_pl or 200)))

    sender = {
        "name": _bs.env("SENDER_NAME") or _ct.get("founder_name", ""),
        "title": _bs.env("SENDER_TITLE") or _ct.get("founder_title", ""),
        "wa": _bs.env("SENDER_WA") or _ct.get("whatsapp", ""),
        "website": _bs.env("SENDER_WEBSITE") or _co.get("website", ""),
        "company": _bs.env("SENDER_COMPANY") or _co.get("brand_display", ""),
    }

    try:
        with open(infile, encoding="utf-8") as f:
            items = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: 「{infile}」不是合法 JSON：{e}")
        sys.exit(1)
    if isinstance(items, dict):
        items = items.get("records", items.get("items", []))

    route = _bs._ms.resolve_sender_route()
    host, port, user, password = route["host"], route["port"], route["user"], route["password"]
    mailbox_id = route["mailbox_id"]
    if route["cap"] is not None:
        max_send = min(max_send, route["cap"])
        print(f"托管邮箱 {mailbox_id}（{user}）：今日预热剩余 {route['cap']} 封 → 本轮上限 {max_send}")
    if not dry_run and (not host or not user or not password):
        print("ERROR: 缺少 SMTP 凭证（SMTP_HOST / SMTP_USER / SMTP_PASS，或托管邮箱密钥环境变量）。"
              "设 DRY_RUN=1 可预览；配置向导：python3 scripts/mail_setup.py providers")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)
    _win = _sw.window_spec(profile)
    report = {"sent": [], "skipped_no_name": [], "skipped_generic": [], "skipped_duplicate": [], "failed": []}

    server = None
    if not dry_run:
        # 合规：拒绝明文投递。仅 465(SSL) 或 587/其它端口 + 强制 STARTTLS；禁用 25。
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
    try:
        for item in items:
            if count >= max_send:
                break
            email = (item.get("email") or "").strip().lower()
            contact = item.get("contact_person", "").strip()
            if not contact:
                report["skipped_no_name"].append(email or item.get("brand", ""))
                print(f"  跳过(无决策人姓名): {item.get('brand','')}")
                continue
            if not email or "@" not in email:
                report["failed"].append({"email": email, "reason": "invalid_email"})
                continue
            if _bs.is_generic(email):
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

            subject = item.get("subject") or f"A note for {_bs.first_name(contact, item.get('region', ''))}"
            body = _bs.with_opt_out(build_named_body(item, sender, profile), profile)
            _ph = _bs._cfg.find_placeholder_text(subject + "\n" + body)
            if _ph:
                report.setdefault("skipped_placeholder", []).append({"email": email, "placeholders": _ph})
                print(f"  拦截（正文/主题残留模板占位符 {', '.join(_ph)}）: {email}")
                continue
            msg = _bs.compose(subject, body, sender["name"], user or _ct.get("email", ""), email)

            if dry_run:
                print(f"[DRY_RUN] → {contact} <{email}> | {subject}")
                report["sent"].append({"email": email, "contact": contact, "dry_run": True,
                                       "brand": item.get("brand", ""), "need_tag": item.get("need_tag", "open"),
                                       "subject": subject, "body": body,
                                       "window": item.get("_window_note", "ok")})
                count += 1
                continue

            try:
                server.sendmail(user, [email], msg.as_string())
                report["sent"].append({"email": email, "contact": contact, "brand": item.get("brand", "")})
                _bs.csv_ops(["add_sent", email, item.get("brand", ""), subject,
                             item.get("need_tag", "open")], data_dir)
                print(f"  已发送 → {contact} <{email}>")
                count += 1
            except smtplib.SMTPRecipientsRefused:
                report["failed"].append({"email": email, "reason": "recipient_refused"})
                _bs.csv_ops(["mark_bounced", email], data_dir)
                print(f"  拒收 → {email}，已标记 bounced")
            except Exception as e:
                report["failed"].append({"email": email, "reason": str(e)})
                print(f"  失败 → {email}: {e}")
            time.sleep(interval)
    finally:
        if server:
            server.quit()

    if not dry_run and mailbox_id:
        _real = len([x for x in report["sent"] if not x.get("dry_run")])
        _bounced = len([x for x in report["failed"] if x.get("reason") == "recipient_refused"])
        _bs._ms.record_usage(mailbox_id, _real, _bounced)
        if _bs._ms.maybe_auto_pause(mailbox_id, _real, _bounced):
            print(f"[!] 托管邮箱 {mailbox_id} 本轮退信偏高，已自动暂停。排查后 mail_setup.py resume {mailbox_id}。")
        report["mailbox"] = mailbox_id

    report["summary"] = {k: len(report.get(k, [])) for k in ("sent", "skipped_no_name", "skipped_generic", "skipped_duplicate", "failed", "deferred_window")}
    rpath = os.path.join(report_dir, f"decision_maker_report_{datetime.date.today().isoformat()}.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n完成：发送 {report['summary']['sent']}，无名跳过 {report['summary']['skipped_no_name']}，"
          f"通用邮箱跳过 {report['summary']['skipped_generic']}，重复跳过 {report['summary']['skipped_duplicate']}，失败 {report['summary']['failed']}。报告 → {rpath}")


if __name__ == "__main__":
    main()
