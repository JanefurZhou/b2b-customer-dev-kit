#!/usr/bin/env python3
"""IMAP 自动退信扫描脚本（零外部依赖，仅用 Python 标准库）

用法:
    python3 scripts/imap_scanner.py [最大扫描数]

功能:
    - 登录企业邮箱（IMAP），扫描收件箱中的退信通知
      （Mailer-Daemon / postmaster / delivery failure 等）
    - 从退信正文提取被退回的目标邮箱（Final-Recipient / Original-Recipient / 正文匹配）
    - 对每个退信邮箱调用 csv_ops.py mark_bounced：
        · 加入 blacklist.csv
        · sent_history.csv 对应记录标记 bounced
    - 建议发信后 24-48 小时执行一次

IMAP 凭证（全部走环境变量，脚本内不硬编码）:
    IMAP_HOST   IMAP 服务器（如 imap.your-mail-provider.com）
    IMAP_PORT   端口（默认 993，SSL）
    IMAP_USER   登录用户名 / 邮箱（未设则回退用 SMTP_USER）
    IMAP_PASS   登录密码 / 授权码（未设则回退用 SMTP_PASS）
    IMAP_FOLDER 扫描文件夹（默认 INBOX）
    IMAP_SINCE_DAYS 只扫描最近 N 天（默认 7）
    DRY_RUN     设为 1 时只列出识别到的退信邮箱，不调用 mark_bounced、不改任何数据

安全：邮箱以只读方式打开（EXAMINE / readonly=True），脚本不删除、不移动、不标记任何邮件。
"""
import imaplib, email, sys, os, re, subprocess, datetime, ssl
from email.header import decode_header
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BOUNCE_SENDERS = ("mailer-daemon", "postmaster", "mail delivery", "delivery status",
                  "delivery failure", "returned mail", "undelivered")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def env(key, default=""):
    return os.environ.get(key, default)


def _decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            out += text.decode(enc or "utf-8", "ignore")
        else:
            out += text
    return out


def _body_text(msg):
    """提取邮件纯文本正文。"""
    if msg.is_multipart():
        chunks = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "message/delivery-status", "message/rfc822", "text/rfc822-headers"):
                payload = part.get_payload(decode=True)
                if payload:
                    chunks.append(payload.decode("utf-8", "ignore"))
        return "\n".join(chunks)
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", "ignore") if payload else ""


def extract_bounced_emails(msg, own_address):
    """从退信邮件中提取被退回的目标邮箱。"""
    body = _body_text(msg)
    found = set()

    # 优先从标准字段提取
    for line in body.splitlines():
        low = line.lower()
        if low.startswith("final-recipient") or low.startswith("original-recipient"):
            m = EMAIL_RE.search(line)
            if m:
                found.add(m.group(0).lower())

    # 回退：正文中所有邮箱（排除自己的地址与常见系统地址）
    if not found:
        for m in EMAIL_RE.findall(body):
            addr = m.lower()
            if addr == own_address.lower():
                continue
            if any(k in addr for k in ("mailer-daemon", "postmaster", "noreply", "no-reply")):
                continue
            found.add(addr)
    return found


def csv_ops(args, data_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    env2 = dict(os.environ)
    if data_dir:
        env2["B2B_DATA_DIR"] = data_dir
    subprocess.run([sys.executable, os.path.join(here, "csv_ops.py"), *args],
                   env=env2, check=False, capture_output=True)


DRY_RUN = os.environ.get("DRY_RUN", "") in ("1", "true", "yes")


def main():
    max_scan = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    data_dir = env("B2B_DATA_DIR", "data")

    host = env("IMAP_HOST")
    port = int(env("IMAP_PORT", "993"))
    user = env("IMAP_USER") or env("SMTP_USER")
    password = env("IMAP_PASS") or env("SMTP_PASS")
    folder = env("IMAP_FOLDER", "INBOX")
    since_days = int(env("IMAP_SINCE_DAYS", "7"))

    if not host or not user or not password:
        print("ERROR: 缺少 IMAP 凭证环境变量（IMAP_HOST / IMAP_USER / IMAP_PASS，"
              "或回退用 SMTP_USER / SMTP_PASS）。")
        sys.exit(1)

    # 合规：显式传入默认 SSL context（校验证书与主机名），仅用加密 IMAPS。
    ssl_ctx = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl_ctx)
    conn.login(user, password)
    conn.select(folder, readonly=True)  # 只读：不改邮件的已读/删除状态

    since = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = conn.search(None, f'(SINCE {since})')
    ids = data[0].split() if data and data[0] else []
    ids = ids[-max_scan:]  # 只取最近 max_scan 封

    bounced_all = set()
    scanned = 0
    for msg_id in ids:
        typ, msg_data = conn.fetch(msg_id, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        scanned += 1
        sender = _decode(msg.get("From", "")).lower()
        subject = _decode(msg.get("Subject", "")).lower()
        is_bounce = (any(k in sender for k in BOUNCE_SENDERS)
                     or any(k in subject for k in ("undeliver", "delivery has failed",
                            "returned to sender", "failure notice", "delivery status")))
        if not is_bounce:
            continue
        for addr in extract_bounced_emails(msg, user):
            bounced_all.add(addr)

    conn.close()
    conn.logout()

    for addr in sorted(bounced_all):
        if DRY_RUN:
            print(f"  [DRY_RUN] 识别到退信，未写入: {addr}")
            continue
        csv_ops(["mark_bounced", addr], data_dir)
        print(f"  退信 → {addr}，已加入黑名单 + 标记 bounced")

    if DRY_RUN:
        print(f"\n演练完成：扫描 {scanned} 封邮件，识别退信邮箱 {len(bounced_all)} 个（未写入；去掉 DRY_RUN 才会同步黑名单）。")
    else:
        print(f"\n完成：扫描 {scanned} 封邮件，识别退信邮箱 {len(bounced_all)} 个，已同步黑名单与已发名单。")


if __name__ == "__main__":
    main()
