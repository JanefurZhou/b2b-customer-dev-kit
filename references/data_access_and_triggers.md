# Data Access Layer and Data Triggers

> The core of hosting and automation is the **customer pool**. This skill ships no customer database: at install you declare and import your own data;
> from then on every action is triggered by data changes (pool low, new file, follow-up due, new reply, bounce spike …), not by someone remembering.

---

## 1. Data access items you must declare at install

| Profile field | Required | Values | Tool |
|---|---|---|---|
| `data_sources.customer_db` | **required** (checked by the gate) | `imported` already imported / `crm_sync` exported from the CRM and imported / `none` nothing yet, starting from zero | `data_import.py` |
| `data_sources.mail_route` | recommended | `smtp_env` single mailbox key / `mailboxes` hosted multi-mailbox / `mcp` connector / `not_yet` | `mail_setup.py`, see `references/mail_setup.md` |
| `data_sources.mail_provider` | recommended | `tencent_exmail` / `aliyun_qiye` / `netease_qiye` / `gmail` / `microsoft365` / `custom` | `mail_setup.py providers` |
| `data_sources.crm` / `crm_route` | optional | `hubspot` / `salesforce` / `okki` / `fumeng` / `other` / `none`; `csv` / `api` / `mcp` | `crm_sync.py` |
| `data_sources.saas_sources` | optional | names of the trade SaaS / customs platforms in use | see `references/saas_integration_guide.md` |

`python3 scripts/onboarding.py start` shows the status and next command for each item; `ask` asks you item by item.

---

## 2. Customer DB `customer_db.csv`

```bash
python3 scripts/data_import.py fields                     # standard fields + recognised English/Chinese column names
python3 scripts/data_import.py inspect customers.xlsx      # read-only mapping preview
python3 scripts/data_import.py import customers.xlsx --relation existing_customer --source own:excel
python3 scripts/data_import.py import leads.csv --relation prospect --source saas:<platform>
python3 scripts/data_import.py stats
```

- Supports `.csv` (UTF-8 / UTF-8-BOM / GB18030 auto-detected) and `.xlsx`; save legacy `.xls` as `.xlsx` first.
- De-dup: first by e-mail, then by "domain + company name"; existing rows only get empty fields filled, never overwritten.
- Relation priority: `do_not_contact` > `existing_customer` > `lost` / `competitor` > `prospect`. If the sheet has a relation / customer-type column, it is read row by row (existing customer / prospect / lost / unsubscribed / complaint / competitor etc.).
- `do_not_contact` e-mails are synced into `blacklist.csv` automatically; the pre-send check blocks them.
- Existing customers, do-not-contact and competitors never enter the cold-outreach sendable pool; existing customers go through repeat-order and lifecycle tracks.
- Every import writes `import_log.csv` (time, file, source, relation, rows, added, completed).

---

## 3. CRM sync `crm_sync.py`

| Path | Command | Notes |
|---|---|---|
| CSV (any CRM) | `export --target hubspot\|salesforce\|okki\|fumeng\|generic` | column names the target's import wizard maps easily; Chinese-language CRMs (OKKI / Fumeng) get Chinese columns, `generic` gets English; check the mapping once in the wizard |
| CSV pull-back | `pull crm_export.csv [--map original_column=standard_field]` | updates only stage / owner / relation / last contact of e-mails already in the local DB; never adds strangers |
| HubSpot API | `push-hubspot` | calls `POST /crm/v3/objects/contacts/batch/upsert` with email as the unique key ([HubSpot docs](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/guide)); DRY_RUN by default, real push only with `HUBSPOT_TOKEN` + `CRM_PUSH=1`; do-not-contact and competitors are never pushed |
| MCP | `mcp-payload` | writes `reports/crm_mcp_payload.json`; the AI processes only `approved=true` items through the CRM's official MCP (e.g. HubSpot remote MCP `https://mcp.hubspot.com`) |

Every sync writes `crm_sync_log.csv`; the triggers use it to decide when a sync is due.

---

## 4. Data Triggers `triggers.py`

```bash
python3 scripts/triggers.py scan                # write reports/trigger_queue.json and print it
python3 scripts/triggers.py scan --apply-safe   # allow the protective action: pause a hosted mailbox on a bounce spike
python3 scripts/triggers.py ack <key> ...       # mark as handled
python3 scripts/triggers.py reviewed            # record this week's review
```

| Trigger | Data source | Condition | Next step | Human sign-off |
|---|---|---|---|---|
| `POOL_LOW` | customer_db + sent_history | sendable < red line, or enough for < lead-time days; customer DB empty | `replenish` four-axis replenish | no (only produces queries) |
| `NEW_IMPORT_FILE` | `data/inbox/` + import_log | an un-imported CSV/XLSX appears | `data_import inspect` → `import` | yes (confirm relation and source) |
| `COOLDOWN_DUE` | sent_history | cooldown passed (3 days after the 1st/2nd e-mail, 10 days after the 3rd; same as `csv_ops.py`), not an existing customer / do-not-contact | write follow-up → DRY_RUN | yes |
| `REPLY_RECEIVED` | sent_history (written by imap_scanner) | status replied | reply personally → Step 6/7 | yes |
| `BOUNCE_SPIKE` | sent_history | ≥ 20 sent in the last 7 days and bounce rate > threshold (default 5%, adjustable default) | pause hosted mailbox, clean the list | no (protective, may run automatically) |
| `WA_SIGNAL` | wa_contacts | new / pending leads | Step 7 WhatsApp | yes |
| `WARMUP_STEP` | mailboxes.json | a mailbox enters a new warm-up tier today | notice only | no |
| `MAILBOX_PAUSED` | mailboxes.json | a mailbox is paused | investigate, then `resume` | yes |
| `CRM_SYNC_DUE` | customer_db + crm_sync_log | never synced, or DB changed and ≥ N days since last sync | `crm_sync export / pull` | yes |
| `WEEKLY_REVIEW` | trigger_state | ≥ 7 days since the last weekly review | Step 0 review + kit write-back | yes |

**Iron rule**: triggers scan read-only and write a queue; any outbound action (e-mail, WhatsApp, CRM push) is marked `needs_human=true`. The only action allowed to run automatically is the protective pause.

---

## 5. Daily automation (set up once)

```bash
# cron example: scan triggers at 08:30, replenish and emit queries at 09:00
30 8 * * * cd /your/skill/dir && B2B_DATA_DIR=data python3 scripts/triggers.py scan --apply-safe >> reports/cron.log 2>&1
0 9 * * *  cd /your/skill/dir && B2B_DATA_DIR=data python3 scripts/search_customers.py replenish --emit queries_today.txt >> reports/cron.log 2>&1
```
Platform scheduled tasks and Windows Task Scheduler: `references/automation_setup.md`.
