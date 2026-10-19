# WhatsApp bulk-send execution guide (the last link of the e-mail → WA loop)

> This guide expands the WhatsApp bulk-send section of SKILL.md.
> Upstream: `wa_targets.json` (pending list) exported by the dashboard `email_dashboard.py`.
> Engine: `scripts/wa_bulk/wa_bulk_sender.py` + 3 PowerShell scripts.
> Environment: **Windows desktop + WhatsApp Desktop (Store edition) + one logged-in local device (device name set by you at first install / run, referred to as <local-device>)**.

---

## 1. How the whole loop fits together

```
① e-mail development (six steps) → customer did not reply / explicitly asked for WA
② csv_ops.py mark_wa_only <email> <wa> <brand> <name>  → writes back the "moved to WA" status
③ email_dashboard.py builds the dashboard → exports wa_targets.json automatically (pending / done / all)
④ wa_bulk_sender.py convert wa_targets.json → bulk-send input (Format B template + variables, see below)
⑤ wa_bulk_sender.py validate → preview (read-only) → harness (send to your own test number)
⑥ confirmed → real bulk send (per message: open chat → popup detection → screenshot verification → send → checkpoint)
⑦ audit re-checks screenshots → write back wa_status="sent" → the dashboard files it under "moved to WA" next time
```

**Key**: the dashboard's pending list and the bulk engine are natural upstream / downstream. `whatsapp` + `brand` + `contact` in the list map directly to the template variables `phone` / `brand` / `intro`.

---

## 2. Two-number system (generic configuration)

| Role | Number | Use |
|------|------|------|
| **Small number (outreach number)** | `<wa-outreach-number>` (E.164, confirmed and filled in by you before use) | logged in on WA Desktop, sends messages. A ban only costs the outreach number |
| **Main number (customer-facing)** | profile `contact.whatsapp`, i.e. `WhatsApp: +<country-code-number>` | the number customers are invited to add in e-mail / WA signatures; long-term conversations, never bulk-sends |

**Iron rule**: bulk sends only from the small number; the harness test number is also the small number sending to itself. Never bulk-send from the main number. The outreach number is never filled in or invented without the user's confirmation.

---

## 3. Store-edition WA specifics (must read, or the scripts fail)

| Property | Store edition | Impact |
|------|---------|------|
| process name | `WhatsApp.Root.exe` | `Get-Process` must use `WhatsApp.Root`, not `WhatsApp` |
| window title | **always "WhatsApp"** | the title cannot identify the current chat |
| registration check | popup white-screen detection | 9 sample points in a 3×3 grid at the screen centre, ≥6 white → unregistered |
| protocol registration | declared in AppxManifest.xml | a broken HKCU key overrides the correct registration and must be removed |

## 4. Repairing the whatsapp:// protocol

The Store edition may leave a broken registry key `HKCU:\SOFTWARE\Classes\whatsapp` (protocol name only, no `shell\open\command`), so `whatsapp://send?phone=xxx` does nothing.

```powershell
# 1. back up
reg export "HKCU\SOFTWARE\Classes\whatsapp" "<your-local-folder>\whatsapp_reg_backup.reg" /y
# 2. delete the broken key (the system falls back to the correct AppxManifest registration)
Remove-Item -Path 'HKCU:\SOFTWARE\Classes\whatsapp' -Recurse -Force
# 3. verify
Start-Process 'whatsapp://send?phone=<phone-E164>'
```

## 5. Local folder structure

```
<your-local-folder>\  (e.g. %TEMP% or your own WA working folder; configurable with WA_WORK_DIR / WA_SCREENSHOT_DIR / WA_MESSAGE_DIR / WA_LOG_DIR / WA_PROGRESS_FILE)
├── scripts\       ← PowerShell scripts (.ps1)
├── screenshots\   ← WA verification screenshots (generated)
├── messages\      ← message temp files + contact JSON
└── logs\          ← progress wa_progress.json
```

Screenshots are saved to `$env:TEMP` first → `Copy-Item` to the target path (GDI+ has limits with non-ASCII paths).

---

## 6. Pre-send checklist (all required)

- [ ] WhatsApp Desktop (Store edition) open and logged in (small number)
- [ ] local device <local-device> online
- [ ] `whatsapp://` protocol works (repair the registry first if not)
- [ ] contact data ready (CSV/Excel converted to JSON, or JSON directly)
- [ ] `validate` shows ✅ All passed (no format errors, no duplicate numbers)
- [ ] template reviewed with `preview` (read-only, never sends)
- [ ] today's count < 200 (`progress`)

Any unticked item → do not start.

---

## 7. Step 0 — data preparation (CSV/Excel → JSON)

Skip when you already have JSON.

```bash
python wa_bulk_sender.py convert customers.csv contacts_wa.json   # zero dependencies
python wa_bulk_sender.py convert customers.xlsx                   # needs openpyxl; otherwise save as CSV first
python wa_bulk_sender.py convert wa_targets.json                  # the pending list exported by the dashboard
```

Header recognition (case-insensitive):

| Recognised headers | Field | Required |
|------------|------|------|
| phone / whatsapp / wa / wa_number / mobile | `phone` | ✅ |
| brand / company / name / customer | `brand` | optional |
| intro | `intro` | optional (Format B {intro}) |
| message / msg | `message` | optional |

The equivalent Chinese-language headers are also recognised for imports from legacy sheets.

Numbers are cleaned automatically (`+`, spaces, hyphens removed).

**Format A – flat list**:
```json
[
  {"brand": "Acme Corp", "phone": "12125551234", "message": "Hi Acme team!\n\n..."},
  {"brand": "Musterfirma GmbH", "phone": "4915100000001", "message": "Hallo Musterfirma GmbH!\n\n..."}
]
```

**Format B – template + variables (recommended; maps naturally to the dashboard's pending list)**:
```json
{
  "template": "Hi {brand} team!\n\n{intro}\n\nWe're {company} — {product}. {fact}. More: {website}\n\nWorth a quick chat?",
  "company": "<your-brand>", "product": "<your one_liner_en>",
  "fact": "<one item from offer.key_facts>", "website": "<your-domain>",
  "contacts": [
    {"brand": "<example-customer>", "phone": "<phone-E164>", "intro": "Congrats on the new <project/office/launch>!"},
    {"brand": "<example-customer-2>", "phone": "<phone-E164>", "intro": "Read your post on <topic> — spot on."}
  ]
}
```
> `intro` (a different opener per person) is the anti-ban core — generate it from the dashboard's `need_tag` / research notes; never one message for everyone.


## 7.2 WhatsApp outreach template bank (WA versions of the 7 hooks) ⭐

> WhatsApp outreach cannot copy e-mail. E-mail may be long and formal; WhatsApp must be **short, conversational, like a real person chatting**,
> and every message needs a **differentiated opener `{intro}`** (anti-ban core + higher reply rate). The 7 templates below match the 7 e-mail hooks,
> compressed to 3–5 lines, no formal salutation, with a light interactive closing. Put them into the Format B `template` field;
> `{intro}` is generated per account from `need_tag` / `solution_tag` / research, never the same sentence twice.

**WhatsApp outreach skeleton (unlike e-mail):**

```
[differentiated opener {intro}] → [one line: who we are + how we help] → [one specific hook] → [light closing question]
```

- Talk about **them** first (recent news / pain point / achievement), not about yourself — differentiation + anti-ban.
- At most 5 lines; close with a low-threshold question (send a catalogue? quick chat?), no hard sell.
- Research first: their business and current solution level (relation to your `differentiators`) + `need_tag` / `solution_tag`, then pick the hook — the wrong direction = a wasted message.

### WhatsApp templates for the 7 hooks (`{intro}` differs per person)

> The table is a **structural skeleton**, cross-industry; the facts in the body (positioning, entry offer, key facts, certifications, custom capability) must be replaced with
> real values from `config/company_profile.json` (`product.*` / `offer.*`); delete the line for any capability you do not have.

| Hook | solution_tag scenario | WhatsApp template skeleton (placeholders must become real facts) |
|------|----------------|-------------------------------------------|
| ① solution upgrade | `quality_upgrade`: using a lower-tier solution | `Hi {brand} team! {intro} We're <your-brand> — <your verifiable differentiator>. Want to compare side by side?` |
| ② low-commitment start | `low_commitment` / `cost`: small team, first attempt | `Hi {brand}! {intro} Easy way to test us: <offer.entry_offer>. <offer.key_facts[0]>. Shall I set it up?` |
| ③ speed / deadline | `speed`: a clear date / go-live / schedule | `Hi {brand} team! {intro} <offer.delivery_time> for <your-core-term> — ready before <their deadline>. What's your timeline?` |
| ④ custom / dedicated | `exclusive_custom` / `dedicated_service` | `Hi {brand}! {intro} We build <your-core-term> to your spec — <custom capability fact>. Want to see how?` |
| ⑤ compliance / sustainability | `compliance` / `sustainability` (real credentials only) | `Hi {brand} team! {intro} <your-core-term> with <exact certification name>. Want the documentation?` |
| ⑥ one-stop | `one_stop`: scattered suppliers / tools | `Hi {brand}! {intro} We cover <scope A> and <scope B> from one team. Would that simplify things?` |
| ⑦ new direction | `innovation`: new product line / market / funding | `Hi {brand} team! {intro} For your <new initiative>: <your one_liner_en>. Worth a quick chat?` |

> **Generating {intro}**: take one sentence from research / `need_tag` / `solution_tag` that is true only for this account. E.g. just won a new project → intro=`Congrats on winning the <project>`;
> hiring a relevant role → intro=`Saw you're hiring a <role> — sounds like <topic> is a priority`. **Never reuse the same sentence**.
>
> **Weak signal**: when the business / need is unclear, flag `need_review` and let the user decide; no automatic conclusions, no hard push.

### Difference from e-mail outreach (one sentence)

- E-mail: may be long, formal, with attachments and signature; WhatsApp: **short, conversational, praise them first, one hook, one light question**.
- E-mail hooks with the subject line; WhatsApp hooks with the **differentiated first line** + anti-ban.
- Both share the same 7 hooks + `need_tag` / `solution_tag` mapping; only the **medium and tone differ**.

---

## 7.3 WhatsApp trigger (clear direction: when, to whom, how to start) ⭐

> "When is WhatsApp outreach triggered?" — not whenever you happen to think of it, but **as soon as the dashboard shows one of the 4 signals below, the account enters the WA list**. WA stops being a hunch and becomes the natural extension of the e-mail chain.

### (1) Four trigger signals (any hit → WA list)

| Signal | Basis (dashboard / data) | Why switch to WA |
|---------|------------------|------------|
| **① several e-mail rounds, no reply** | `followup_count >= 2` and `status != replied` (3+ e-mails, no reply) | the mailbox may be unread / in spam; WA reaches the person directly, higher reply rate |
| **② bounce / invalid mailbox** | `status == bounced` or only a generic mailbox, no personal one | the e-mail route is dead; WA is the only direct channel left |
| **③ high-value target + public WA** | large account / strong positioning, WhatsApp number on the website or LinkedIn | a big deal justifies the heavier direct channel |
| **④ trade show / number given voluntarily** | the customer gave their WA (show, inquiry, correspondence) | the customer has signalled WA is welcome; highest priority |

> ①② are **fed automatically by the e-mail chain** (pending / no-reply list of `email_dashboard.py`); ③④ come from research / manual discovery and are added by hand.

### (2) Trigger chain (five steps, joined to the e-mail loop)

```
① dashboard lists pending / no reply      ② export WA targets          ③ apply templates
   email_dashboard.py filter        ==→   → wa_targets.json       ==→   7.2 template bank + {intro} per account
   (signals ①②③④ hit)                     (Format B structure)          (need_tag / solution_tag picks the hook)
                                                                        ↓
⑥ review results                 ⑤ write back dashboard / list       ④ bulk engine sends one by one + screenshot verification
   wa_review.py review     ←==   mark_wa_only / wa_status      ←==   wa_bulk_sender.py send
   (funnel + hooks + won channel)  (avoid duplicate contact)           (anti-ban rules, screenshot per message)
        ↓
   review results feed ① the next list (self-loop): which region / hook / need wins most on WA gets more weight next round
```

### (3) Commands per step

```bash
# ① export the "several rounds no reply + bounced" WA list from the dashboard (if supported; otherwise filter manually)
python3 scripts/email_dashboard.py --export-wa-targets wa_targets.json   # without this flag, export manually by status / followup_count

# ②③ apply the 7.2 templates to wa_targets ({intro} per account) → Format B contacts.json (template filled manually / semi-automatically)

# ③ validate + preview
python3 scripts/wa_bulk/wa_bulk_sender.py validate contacts.json
python3 scripts/wa_bulk/wa_bulk_sender.py preview contacts.json

# ④ bulk send (screenshot verification per message, anti-ban rules)
python3 scripts/wa_bulk/wa_bulk_sender.py send contacts.json

# ⑤ write back the dashboard / list (avoid duplicate contact)
python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>
# customer replied → set that row's status in wa_contacts.csv to replied (the reply rate in the review depends on it)

# ⑥ review (read-only: WA funnel + which hook / region wins)
python3 scripts/wa_review.py review --html wa_review.html --compare-email
python3 scripts/wa_review.py funnel
# at close, add_success must carry --won_channel wa for a correct review
```

### (4) Join points with the e-mail chain (one system, not two)

- The e-mail chain does "broadcast reach", the WA chain "closes the hard accounts that never replied to e-mail" — **both share one customer table** (see the "no e-mail reply → moved to WA" state in the `stage` column).
- `won_channel` tells e-mail wins from WA wins at close; `wa_review --compare-email` then shows **which channel deserves more budget**.
- **Meta-need 2 (you decide)**: a signal hit is only a "suggestion to list"; whether, how many and who first is your call; weak signals get `need_review`.

## 8. Step 1 — validation and dry run

```bash
python wa_bulk_sender.py validate contacts.json
python wa_bulk_sender.py preview contacts.json      # read-only preview, never sends
```

**Number format** (no `+`, no spaces, no hyphens):

| Country | Format | Example |
|------|------|------|
| US / Canada | `1` + 10 digits | `12125551234` |
| UK | `44` + 10–11 digits | `447911123456` |
| France | `33` + 9 digits | `33612345678` |
| Germany | `49` + 10–11 digits | `4915100000001` |
| Italy | `39` + 10 digits | `393331234567` |
| Spain | `34` + 9 digits | `34612345678` |
| Australia | `61` + 9 digits | `61412345678` |
| Japan | `81` + 9–10 digits | `819012345678` |
| China | `86` + 11 digits | `86<11-digit-mobile>` (format example, not a real number) |

---

## 9. Step 2 — send loop (every contact in order, no skipped steps)

### 2-A open the chat
```powershell
Start-Process "whatsapp://send?phone={phone}"
```
Wait 5 seconds.

### 2-B popup white-screen detection ⚠ never skip
The Store edition's title never changes; the popup is how registration is detected:
```
sample 9 pixels in a 3×3 grid at the screen centre
≥6 white (R>240,G>240,B>240) → popup → number unregistered → SKIP
<6 white → no popup → chat open → continue
```

### 2-C screenshot verification
```bash
python wa_bulk_sender.py screenshot   # → $env:TEMP\wa_verify.png
```
**Matching rule — strip non-digits, compare the last 8 digits**:
```
✅ match → go to 2-D
❌ no match → retry 2-A+2-B+2-C (max 2) → still no match → SKIP and record the reason
screenshot failed → SKIP and record the reason
```

### 2-D send the message
**Inline method (verified, simplest, recommended for small batches)**:
```powershell
Start-Process "whatsapp://send?phone={phone}"
Start-Sleep -Seconds 5
Add-Type -AssemblyName System.Windows.Forms
Set-Clipboard -Value "{message_text}"
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
```
**Temp-file method (messages with special characters)**:
```bash
python wa_bulk_sender.py send "{message_text}"   # prints SENT or ERROR:WhatsApp_NOT_FOCUSED
```
On `ERROR:WhatsApp_NOT_FOCUSED`: retry once; on a second failure → skip and record.

### 2-E checkpoint and pacing
1. update `wa_progress.json`
2. increment `wa_daily_count.json` (`send` adds 1 per generated message; `progress` shows today's count)
3. daily count = limit (default 200; lower it with `WA_DAILY_LIMIT`, never raise it) → `send` returns `STOP` with exit code 3, stops and reports
4. random pause of **8–15 seconds** between contacts
5. every 5 contacts: random **30–60 second** cooldown
   (4 and 5 are enforced by `send`: when not enough time has passed since the last message it waits first; recorded in `wa_pacing.json`)

---

## 10. Anti-ban iron rules (non-negotiable)

- at most **200 messages per day** (enforced by the counter)
- at least **8 seconds** between messages (random 8–15 s)
- **30–60 s** cooldown after every 5 messages
- a **different opener per person** (`{intro}` variable)
- **no wa.me links** (in bulk sends — see the "wa.me context" below)
- **never** the same message to several people

### ⚠️ wa.me context (no contradiction with the dashboard)
- **No wa.me in bulk sends**: never put `wa.me` links into bulk message bodies and never open chats in bulk through `wa.me` — it is judged as marketing and banned outright. Bulk sends always open chats one by one through the `whatsapp://send?phone=` protocol.
- **wa.me in the dashboard's one-click links is fine**: the wa.me links in the dashboard's contact list / success-case cards are an operations tool for **you to open one customer chat manually** (one at a time, by hand), not bulk, not in a message body, therefore safe.
- In one sentence: **wa.me must not be used "in bulk / automatically / inside messages"; it may be used "to open one chat manually"**.

---

## 11. Common shortcuts and the truth

| Shortcut | Truth |
|---|---|
| "2-B popup detection is slow, skip it" | the Store edition's title never changes; the popup is the only way to detect an unregistered number |
| "the number looks right, skip the screenshot" | WA may still show the previous chat during a switch delay; the screenshot is the only evidence |
| "200/day is too conservative, raise it" | WhatsApp bans bulk senders; 200 is the safe ceiling |
| "dry-run was fine, skip validate" | validate catches empty messages, wrong numbers, wrong digit counts and **duplicate numbers**; dry-run does not |
| "skipped customers can be done later" | the skip records in the progress file are your to-do list; export them now |
| "same message to everyone" | identical messages = strong spam signal; always vary the opener |
| "inline without screenshots, to be fast" | without verification the message will land in the wrong window |

## 12. Danger signals (any of them → stop immediately)

- 2-B (popup detection) or 2-C (screenshot verification) skipped
- several contacts received identical text
- interval < 8 seconds
- daily count > 200 without a date reset
- `wa_progress.json` not updated after sending
- unreplaced `{variables}` in the message
- `Get-Process -Name 'WhatsApp'` used (must be `WhatsApp.Root`)
- trying to identify the chat by window title (never changes in the Store edition)

---

## 13. Post-send audit

```bash
python wa_bulk_sender.py audit
# generates wa_audit.ps1 → run on <local-device> → opens and screenshots every sent chat → the AI reads the images to verify number + content
```
| Parameter | Default | Description |
|------|------|------|
| `-ProgressFile` | `$env:TEMP\wa_progress.json` (or `WA_PROGRESS_FILE`) | progress file path |
| `-MessageFile` | `""` | message JSON (brand cross-reference) |
| `-StartFrom` | `1` | start at entry N |

## 14. Pre-send sandbox test harness

```bash
python wa_bulk_sender.py harness contacts.json   # validates the file first; refuses on problems
# generates wa_harness.ps1 -TestPhone <country-code><your-own-test-phone> -MessageFile contacts.json -Count 3
```
Sends the first 3 messages to **your own test number (small number)** to verify format / content / line breaks before deciding on the real bulk send.

| Parameter | Required | Description |
|------|------|------|
| `-TestPhone` | ✅ | your own WhatsApp number (small number) |
| `-MessageFile` | ✅ | message JSON path |
| `-Count` | ❌ | test count, default 3 |

---

## 15. Post-send write-back + review (closing the loop)

**Step 1: write back (avoid duplicate contact)** — after a successful bulk send, mark the sent customers as "moved to WA"; the dashboard files them under "✅ moved to WA" next time:
```bash
python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>
```
or set `wa_status="sent"` on the record in the dashboard data. **Customer replied → set that row's status in wa_contacts.csv to `replied`** (the reply rate depends on it).

**Step 2: tag the winning channel** — when a WA conversation closes, the success case must carry `--won_channel wa`:
```bash
python3 scripts/csv_ops.py add_success <email> <brand> <contact> <order_amount> "<success_points>" --won_channel wa --region ... --need_tag ... --hook_type ...
```

**Step 3: dedicated WA review** (read-only, 14 iron rules) — check regularly how the WA channel performs; it becomes the basis of the next list (self-loop):
```bash
python3 scripts/wa_review.py review --html wa_review.html --compare-email   # WA funnel + hook / region / need distribution + e-mail vs WA
python3 scripts/wa_review.py funnel                                        # reach → reply → won funnel only
```
> The review **feeds the trigger**: which region / hook / `need_tag` wins most on WA gets more weight in the next 7.3 list — the loop **trigger → send → write back → review → trigger again**. Conclusions are advisory; scaling up or down is your decision (meta-need 2).

---

## 16. Script execution methods

| Method | Reliability | Notes |
|------|--------|------|
| `-File xxx.ps1` | ✅ best | recommended |
| `-EncodedCommand Base64` | ⚠️ non-ASCII corruption | non-ASCII comments break |
| `-Command "inline"` | ❌ `$_` swallowed | forbidden |
| direct inline (Set-Clipboard + SendKeys) | ✅ verified | simplest for small batches |

## 17. Key constraints

1. **Operate WhatsApp only** — never touch other programs
2. **Screenshot-verify every message** — no verification, no sending
3. PowerShell scripts: **ASCII-only comments**
4. Screenshots: `$env:TEMP` first → `Copy-Item` to the target
5. Messages go through temp files, never concatenated into PowerShell strings
6. Command execution needs the user's confirmation card
7. Avoid `'"` quotes in messages

## 18. Script list (scripts/wa_bulk/)

| File | Purpose |
|------|------|
| `wa_bulk_sender.py` | controller: validate/preview/send/screenshot/progress/template/audit/harness (send/screenshot/harness/audit require a completed profile; validate blocks duplicate numbers) |
| `wa_audit.ps1` | opens and screenshots every sent chat after sending, for AI verification |
| `wa_harness.ps1` | sends the first N messages to your own test number before sending |
| `wa_phase1_batch3.ps1` | batch sample: open chat + screenshot only, no sending (phase 1 verifies registration status); self-checks before running and refuses on placeholders / format errors / duplicate numbers |
