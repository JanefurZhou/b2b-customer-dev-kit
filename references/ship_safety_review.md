# Manual review of sending paths (Skill-Self-Check · EXT.3)

> The ship-safety static scan of Skill-Self-Check flags PowerShell automation as should_fix "sending path needs manual review". Below is the per-file conclusion (reviewed for v3.0; v3.1 did not change these three files); any change to them requires a new review.

| File | Sends messages? | To whom | Guards |
|---|---|---|---|
| `scripts/wa_bulk/wa_harness.ps1` | yes (clipboard paste + Enter) | **only to the required parameter `-TestPhone`** (your own test number), never to customers in the list | `-TestPhone` / `-MessageFile` both required; exits when the message file is missing; sends only the first 3 by default (`-Count`); screenshot per message |
| `scripts/wa_bulk/wa_audit.ps1` | no (no send keystroke) | — | opens chats and screenshots only, for post-send review |
| `scripts/wa_bulk/wa_phase1_batch3.ps1` | no (file header states no send) | — | opens chats + screenshots only; pre-check before running: leftover `<placeholders>`, numbers not 8–15 digits, duplicate numbers → refuses to run |

Real bulk sending goes only through `wa_bulk_sender.py send`: runs only with gate READY + matching content fingerprint; checks the daily counter before generating each message (`WA_DAILY_LIMIT`, default 200, returns STOP at the limit); `harness` refuses files that fail `validate`.

## Dry-run switches of the other external actions

| Script | External action | Dry run |
|---|---|---|
| `batch_sender.py` / `decision_maker_sender.py` | SMTP sending | `DRY_RUN=1`: prints subject, body and local-window status per e-mail, sends nothing |
| `imap_scanner.py` | reads the mailbox (read-only open) | `DRY_RUN=1`: lists detected bounces only, writes no blacklist |
| `dns_validator.py` | DNS queries (read-only) | `DRY_RUN=1`: lists the domains to query, no network requests |
| `search_customers.py` | none (generates query text only) | — |
| `crm_sync.py push-hubspot` | HubSpot batch upsert API | **dry run by default**: without `CRM_PUSH=1` it only prints the items to push; a real push also needs `HUBSPOT_TOKEN` and the Install Gate (READY + matching fingerprint); do-not-contact / peers are never pushed |
| `crm_sync.py export / pull / mcp-payload` | none (local CSV / JSON only) | — |
| `mail_setup.py test` | logs into SMTP / IMAP to verify keys | **login only, no sending**; passwords read from environment variables, never written to disk |
| `mail_setup.py auth-check` | DNS queries for SPF / DMARC (UDP, public DoH fallback) | read-only queries |
| `mail_setup.py mcp-export` | none (generates the to-send list JSON only) | every item `approved=false`; you flip them to true one by one before handing over to the connector |
| `triggers.py scan --apply-safe` | local: pauses hosted mailboxes with bounce anomalies | the only automatic action, and it only "stops", never "sends"; resuming is manual via `mail_setup.py resume` |
| `data_import.py` | none (writes the local customer DB only) | `inspect` / `--dry-run` read-only preview |
