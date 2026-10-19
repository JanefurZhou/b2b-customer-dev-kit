# Automation Setup

The skill ships the "pool never runs dry" test and the replenish scheduling logic, but to **run unattended every day**
in a real environment a host (AI platform schedule / cron / resident process) must wake it up. This page explains
what is built in, where the boundaries are, and the three hosting options.

## 1. Automation logic already built in (nothing to write)

`scripts/search_customers.py` contains the self-replenishing engine:

- **Pool floor**: when the grade-A sendable candidate pool drops below the red line (`--floor`, default 100) → the pool is judged about to bottom out,
  a replenish rotation is triggered automatically and a warning is written.
- **Replenish rotation**: every replenish rotates the search combination on four axes (Height / Breadth / Depth / Reach) — customer tier × product terms ×
  5 orthogonal axes × region — so the same batch is not mined every day.
- **State memory**: rotation history and last run time are persisted; after an interruption it continues where it stopped, without repeats.
- **Related commands**:
  - `replenish`: checks the pool once; below the line it produces today's queries.
  - `status` / rotation view: pool level, sendable days, which channel tier it has reached.
  - `schedule`: resident-process mode; runs "check pool → replenish if low → rotate" at a fixed time every day.

Sending time: `batch_sender.py` / `decision_maker_sender.py` judge contacts with `region`/`tz` by the recipient-local
`rules.local_send_window` (`scripts/send_window.py`, daylight saving included, no weekends); outside the window the contact is deferred —
a scheduled task may run several times a day and each run sends only to people currently inside their local window.

The data pipeline (`filter` / `dns_validator` / `email_guesser` / `batch_sender` /
`imap_scanner` / `email_dashboard`) handles de-dup, e-mail validation, sending, bounce write-back and the dashboard,
and can be chained into a loop by a scheduled task.

## 2. Capability boundaries that must be stated

The scripts are **deterministic tools**; the following actions are not done by the scripts themselves and need an AI agent (or browser / search tools)
when woken up:

1. **Real web search and page reading**: the scripts produce boolean queries; running the search, opening websites / LinkedIn and
   extracting real contact e-mails is done by the AI with search / browser tools. Scripts must never invent e-mails.
2. **Per-account research and personalised copy**: whether each account fits, its need positioning and e-mail personalisation are done by the AI
   following research_guide, not by a script mass-filling templates.
3. **Human confirmation before sending**: per the brake nodes in AGENTS.md, outbound e-mail needs the boss's confirmation
   (the platform schedule may produce "drafts for review"; sending happens after approval).

So "fully automatic" precisely means: **scheduled pool checks, automatic query generation, automatic candidate and dashboard preparation, automatic reminders**;
the stretch "find e-mail — research — finalise — send" stays AI-executed with human confirmation at key nodes, for quality and compliance.

## 3. Three hosting options (pick one)

### Option A: AI platform schedule / workflow (recommended, no ops)

Create a daily scheduled task on the AI platform (e.g. every weekday morning) that:

1. First confirms `onboarding.py check` is READY (if the profile is not finished, only remind about the profile that day; no business run).
2. Runs `python3 scripts/triggers.py scan --apply-safe` and handles `reports/trigger_queue.json` by priority
   (pool low / new import file / follow-up due / new reply / bounce spike / WhatsApp lead / CRM sync due / weekly review;
   see `references/data_access_and_triggers.md`).
3. Runs `python3 scripts/search_customers.py replenish` (reads `$B2B_DATA_DIR/customer_db.csv` by default).
4. If the output says "below the red line": hands today's queries to the AI to run with search / browser tools,
   finds real e-mails per the process → `filter` into the DB → `dns_validator` validation.
5. Produces the day's draft list (DRY_RUN) and submits it to the boss; after confirmation `batch_sender` sends
   (single mailbox key / hosted multi-mailbox under warm-up caps / MCP connector — see `references/mail_setup.md`).
6. `imap_scanner` writes back bounces and replies; `email_dashboard` summarises, HEARTBEAT reports health;
   `crm_sync.py export/pull` aligns with the CRM once a week.

Time zones are converted per `rules.local_send_window` and the target market so sending happens in the customer's local working hours.

### Option B: system cron (when a machine is always on)

```cron
# every weekday: 08:20 scan the data triggers, 08:30 check the pool and replenish (adjust paths / interpreter)
20 8 * * 1-5  cd /path/to/skill && B2B_DATA_DIR=/path/to/data \
    /usr/bin/python3 scripts/triggers.py scan --apply-safe >> data/triggers.log 2>&1
30 8 * * 1-5  cd /path/to/skill && B2B_DATA_DIR=/path/to/data \
    /usr/bin/python3 scripts/search_customers.py replenish --emit queries_today.txt \
    >> data/replenish.log 2>&1
```

SMTP/IMAP keys are provided through environment variables; never write them into the cron file or the profile. Research and sending after
candidates are found still go to the AI / human confirmation stage.

### Option C: built-in resident scheduler (single machine, always on)

```bash
# needs an always-on environment; with apscheduler installed it uses cron precision, otherwise a built-in sleep loop
python3 scripts/search_customers.py schedule --at 09:00   # reads $B2B_DATA_DIR/customer_db.csv by default
```

Suited to a local server / container; mind process restarts, logs and key injection.

## 4. Recommended daily loop (arrange the timer like this)

1. Health check (HEARTBEAT): pool level, yesterday's send count, bounce rate, customer replies awaiting follow-up.
2. Pool below the red line → automatic replenish rotation across channels (see the `channels` sub-command:
   general web / social / Maps / customs / RFQ / trade media / trade shows / competitor reverse-lookup / independent stores).
3. Candidate filter and de-dup → DNS validation → per-account research → personalised drafts.
4. Drafts for review → boss confirms → send in local working hours → bounce write-back.
5. Customer replies: remind the boss through two channels per the rules; never stay silent.
