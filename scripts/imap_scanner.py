#!/usr/bin/env python3
"""IMAP automatic bounce scanner (zero external dependencies, Python standard library only)

Usage:
    python3 scripts/imap_scanner.py [max_scan]

What it does:
    - logs in to the business mailbox (IMAP) and scans the inbox for bounce notifications
      (Mailer-Daemon / postmaster / delivery failure etc.)
    - extracts the bounced recipient from the bounce body (Final-Recipient / Original-Recipient / body match)
    - calls csv_ops.py mark_bounced for each bounced address:
        · added to blacklist.csv
        · matching sent_history.csv records marked bounced
    - recommended 24-48 hours after sending

IMAP credentials (all via environment variables; nothing hard-coded):
    IMAP_HOST   IMAP server (e.g. imap.your-mail-provider.com)
    IMAP_PORT   port (default 993, SSL)
    IMAP_USER   login user / mailbox (falls back to SMTP_USER)
    IMAP_PASS   login password / authorisation code (falls back to SMTP_PASS)
    IMAP_FOLDER folder to scan (default INBOX)
    IMAP_SINCE_DAYS only scan the last N days (default 7)
    DRY_RUN     set to 1 to only list detected bounced addresses; mark_bounced is not called and no data changes

Safety: the mailbox is opened read-only (EXAMINE / readonly=True); the script never deletes, moves or flags any message.
"""
import imaplib, email, sys, os, re, subprocess, datetime, ssl
from email.header import decode_header
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
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
    """Extract the plain-text body of a message."""
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
    """Extract the bounced recipient address from a bounce message."""
    body = _body_text(msg)
    found = set()

    # Prefer the standard fields
    for line in body.splitlines():
        low = line.lower()
        if low.startswith("final-recipient") or low.startswith("original-recipient"):
            m = EMAIL_RE.search(line)
            if m:
                found.add(m.group(0).lower())

    # Fallback: every address in the body (excluding our own address and common system addresses)
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
        print("ERROR: IMAP credential variables missing (IMAP_HOST / IMAP_USER / IMAP_PASS, "
              "or the SMTP_USER / SMTP_PASS fallback).")
        sys.exit(1)

    # Compliance: pass the default SSL context explicitly (verifies certificate and host name); encrypted IMAPS only.
    ssl_ctx = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl_ctx)
    conn.login(user, password)
    conn.select(folder, readonly=True)  # read-only: never changes read/deleted flags

    since = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = conn.search(None, f'(SINCE {since})')
    ids = data[0].split() if data and data[0] else []
    ids = ids[-max_scan:]  # only the most recent max_scan messages

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
            print(f"  [DRY_RUN] bounce detected, not written: {addr}")
            continue
        csv_ops(["mark_bounced", addr], data_dir)
        print(f"  Bounce → {addr}, added to blacklist + marked bounced")

    if DRY_RUN:
        print(f"\nDry run done: scanned {scanned} messages, detected {len(bounced_all)} bounced addresses (not written; remove DRY_RUN to sync the blacklist).")
    else:
        print(f"\nDone: scanned {scanned} messages, detected {len(bounced_all)} bounced addresses; blacklist and send history synced.")


if __name__ == "__main__":
    main()
