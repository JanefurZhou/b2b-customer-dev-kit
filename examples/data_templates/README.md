# Data table templates (headers only)

These 5 CSV files contain headers only and no real data; the headers are **identical** to the fields `scripts/csv_ops.py` actually writes
(`scripts/consistency_audit.py` section I checks this automatically):

| File | csv_ops field constant | Purpose |
|---|---|---|
| `sent_history.csv` | `SENT_FIELDS` | sending ledger (cooldown, follow-up count, status) |
| `blacklist.csv` | `BL_FIELDS` | blacklist / bounces / blocks |
| `wa_contacts.csv` | `WA_FIELDS` | WhatsApp contact records |
| `success_cases.csv` | `SUCCESS_FIELDS` | success cases (written only after user confirmation) |
| `pipeline.csv` | `PIPELINE_FIELDS` | reserve customer pool |

## Where they live at runtime

The scripts read and write `data/` under the working directory by default; the environment variable `B2B_DATA_DIR` overrides it:

```bash
export B2B_DATA_DIR=/path/to/your/data
python3 scripts/csv_ops.py stats
```

First use: copy the headers from this directory into your `B2B_DATA_DIR` (the scripts also create the tables automatically when a file is missing).
These templates stay inside `examples/` and are never written to at runtime; **real customer data lives only in your own
private data directory and must never be committed back into the skill package**. Field definitions: `references/csv_guide.md`.
