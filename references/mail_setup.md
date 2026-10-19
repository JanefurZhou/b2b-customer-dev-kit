# Sending-route setup (business mailbox keys / hosted multi-mailbox warm-up / MCP)

> Walk through this page once after installing and you will know which route to use, where to generate the key, how to verify it and how to hand it to the scripts.
> Every server address, port and key name carries its source; numbers set by this skill (warm-up tiers, bounce pause threshold) are marked "adjustable default".

---

## 1. Pick a route first

| Your situation | Choose | In one sentence |
|---|---|---|
| Chinese business mailbox (Tencent / Alibaba / NetEase) or Gmail, a single sender mailbox | **A1 single mailbox key** | generate a client key in the admin UI → `export` environment variables → the scripts send directly |
| 2 or more sender mailboxes, want to spread volume and ramp up with warm-up | **A2 hosted multi-mailbox** | register with `mail_setup.py add` → the senders pick the mailbox with the most quota left |
| The runtime already has a Gmail / Outlook connector or a mail MCP and you do not want to give scripts a key | **B MCP / connector** | the script only produces a dry-run report → human approves each item → the AI drafts/sends through the connector → results written back |

All three routes share one step: `DRY_RUN=1` first, check every recipient and body, then send for real.

---

## 2. A1 single mailbox key

```bash
python3 scripts/mail_setup.py providers                       # servers, ports, key names, where to generate
python3 scripts/mail_setup.py env tencent_exmail --user sales@your-domain   # prints the lines to export
export SMTP_PASS=<client key generated in the admin UI>        # type it in the terminal only, never in a file
python3 scripts/mail_setup.py test                            # logs in to SMTP/IMAP only, sends nothing
```

### Provider presets (sources in the right column)

| Provider | SMTP | IMAP | Key name and where to generate | Source |
|---|---|---|---|---|
| Tencent Exmail `tencent_exmail` | `smtp.exmail.qq.com` 465 SSL | `imap.exmail.qq.com` 993 SSL | once secure login is enabled a "client-specific password" is required; webmail Settings → Mailbox binding; IMAP/SMTP must be enabled under send/receive settings. Overseas nodes `hwsmtp/hwimap.exmail.qq.com` | [WeCom help centre](https://open.work.weixin.qq.com/help2/pc/19886), [Tencent Cloud docs](https://main.qcloudimg.com/raw/document/product/pdf/613_46019_cn.pdf) |
| Alibaba Mail `aliyun_qiye` | `smtp.qiye.aliyun.com` 465 SSL | `imap.qiye.aliyun.com` 993 SSL | "third-party client security password"; Settings → Account & security → Account security. Hong Kong nodes `smtphk/imaphk.qiye.aliyun.com` | [Alibaba Cloud help 36576](https://help.aliyun.com/zh/document_detail/36576.html), [Alibaba Cloud help 36687](https://help.aliyun.com/zh/document_detail/36687.html) |
| NetEase Enterprise Mail `netease_qiye` | `smtphz.qiye.163.com` 465 SSL | `imaphz.qiye.163.com` 993 SSL | third-party clients need a "client authorisation code"; Settings → Account & security → Client settings, shown once only; the admin may need to enable client protocols first | [NetEase enterprise mail help 1](https://office.163.com/helpCenter/mail/d/2057123645218729986.html), [NetEase enterprise mail help 2](https://office.163.com/helpCenter/mail/d/1892504337403437057.html) |
| Gmail / Workspace `gmail` | `smtp.gmail.com` 465 SSL (or 587 TLS) | `imap.gmail.com` 993 SSL | "app password" requires 2-step verification; revoked when the account password changes; Google prefers OAuth (route B) | [Gmail help](https://support.google.com/mail/answer/185833?hl=en), [Workspace admin help](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app), [Gmail developer docs](https://developers.google.com/workspace/gmail/imap/imap-smtp) |
| Microsoft 365 `microsoft365` | `smtp.office365.com` 587 STARTTLS (TLS 1.2+) | not preset (inbound / bounce scanning should use OAuth or a connector) | the mailbox needs Authenticated SMTP enabled; SMTP AUTH basic authentication stays until the end of December 2026, then is disabled by default for existing tenants (admins can re-enable), tenants created after December 2026 must use OAuth; the final removal date will be announced in the second half of 2027. Route B recommended | [Microsoft Learn](https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365), [Microsoft Exchange team blog](https://techcommunity.microsoft.com/blog/exchange/updated-exchange-online-smtp-auth-basic-authentication-deprecation-timeline/4489835) |
| Other `custom` | address from your provider | same | SMTP password / authorisation code from your provider | your provider's help pages |

**Common failures**: the web login password was used instead of the client key; IMAP/SMTP not enabled; the admin has not enabled client protocols; the company network blocks ports 465/587. `test` prints the cause of an authentication failure.

---

## 3. A2 hosted multi-mailbox + warm-up ramp

```bash
python3 scripts/mail_setup.py add mb1 --provider aliyun_qiye --user a@your-domain
python3 scripts/mail_setup.py add mb2 --provider tencent_exmail --user b@your-domain --daily-cap 60
export MAILBOX_PASS_MB1=<client key of mb1>
export MAILBOX_PASS_MB2=<client key of mb2>
python3 scripts/mail_setup.py list          # each mailbox: status / warm-up day / cap today / used / left
python3 scripts/mail_setup.py test --mailbox mb1
```

- **Hosting file** `config/mailboxes.json`: stores only the mailbox address, provider and the **environment-variable name** of the key, never the key itself. `config/` is excluded entirely when packaging.
- **Automatic rotation**: when `SMTP_HOST` is unset, `batch_sender.py` / `decision_maker_sender.py` pick the mailbox with the most quota left today; `MAILBOX=mb2` pins one.
- **Warm-up ramp**: every mailbox has a `warmup_schedule` (from day N → daily cap). Built-in default `day 1: 20 → day 8: 40 → day 15: 80 → day 22: 150 → day 29: 200`.
  This is a **conservative adjustable default of this skill, not a number published by any provider**; if your provider gives your account an explicit quota, the provider wins.
  The senders use `min(profile rules.daily_limit, warm-up cap − used today)`.
- **Automatic pause**: when bounces (recipient rejected) in one real round exceed `bounce_pause_rate` (default 0.05, editable) → the mailbox is set to `paused` and the senders refuse to use it; after checking the list, `mail_setup.py resume mb1`. `triggers.py scan --apply-safe` also pauses all hosted mailboxes when the 7-day bounce rate is abnormal.
- **Usage log** `data/mailbox_usage.csv`: date, mailbox, sent, bounced; read by the dashboard and the triggers.
- **Third-party warm-up services** (optional): dedicated mailbox warm-up / hosting services exist and can be used alongside this skill; the skill does not bundle or recommend a specific vendor — check their terms and data handling before connecting.

---

## 4. B MCP / connector sending

For: not wanting to hand mailbox keys to scripts, or Microsoft 365 / Google allowing OAuth only.

```bash
DRY_RUN=1 python3 scripts/decision_maker_sender.py queue.json reports/     # 1 dry-run report (with final bodies)
python3 scripts/mail_setup.py mcp-export reports/decision_maker_report_<date>.json   # 2 build the outbox
# 3 a human checks reports/mcp_outbox.json item by item and sets "approved": true on the ones to send
# 4 the AI uses the runtime's Gmail / Outlook connector (or mail MCP) to create drafts for approved items;
#   it sends only with the user's explicit authorisation; after each item set status to drafted / sent
python3 scripts/mail_setup.py mcp-writeback reports/mcp_outbox.json        # 5 write back to sent_history (marked via:mcp)
```

Rules: the script itself calls no MCP; the AI processes only `approved=true` items; drafts by default, never sends by default.

---

## 5. Sending-domain authentication and unsubscribe (hard requirements for inbox placement)

```bash
python3 scripts/mail_setup.py auth-check your-domain --selector <DKIM selector>
```
Looks up the SPF, DMARC and DKIM DNS TXT records (falls back to DNS-over-HTTPS when UDP 53 is blocked).

Gmail sender requirements ([Google sender guidelines](https://support.google.com/mail/answer/81126?hl=en), [Google sender guidelines FAQ](https://support.google.com/mail/answer/14229414?hl=en)):
- All senders: set up at least SPF or DKIM; the sending IP has a valid reverse DNS (PTR) record; keep the spam rate in Postmaster Tools below 0.3%.
- Bulk senders (about 5,000+ messages a day to personal Gmail accounts): SPF + DKIM + DMARC all required (DMARC may be `p=none`), From domain aligned with SPF/DKIM; marketing mail must support one-click unsubscribe (`List-Unsubscribe` + `List-Unsubscribe-Post` headers) with a visible unsubscribe link in the body; spam rate ideally below 0.1%.

How this skill implements it:
- The senders send **plain-text** e-mail, each with a `List-Unsubscribe: <mailto:sender?subject=unsubscribe>` header; with `UNSUBSCRIBE_URL=https://...` set, an HTTPS one-click header and `List-Unsubscribe-Post` are added.
- An opt-out sentence is appended to the body (default English "If this isn't relevant for you, just reply \"no\" and I won't write again."; the profile's `rules.opt_out_line` can change it to the local language; `off` disables it, not recommended). What you see in the dry-run report is the final body.
- A reply saying "no / unsubscribe" → `csv_ops.py add_blacklist`, or set the relation to `do_not_contact` in the customer DB and run `data_import` again; never contacted again.
