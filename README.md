# B2B Customer Development Kit (industry-generic, de-identified)

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.1-blue.svg)](CHANGELOG.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#install)
[![Self-Check](https://img.shields.io/badge/Skill--Self--Check-pass-brightgreen.svg)](references/skill_self_check_report.md)

**English edition at the repository root · 中文版在 [`zh/`](zh/) 目录（[中文说明](zh/README.md)）.**

An industry-agnostic, de-identified Agent Skill for B2B customer development: **Install Gate → Data Access Layer → Step 0 review → seven steps → WhatsApp trigger → Win Review and write-back**. Every stage has an exit and a return path; every outbound action needs a human decision.

The package contains no company, contact or customer data. Customer DB, mailboxes and CRM are connected by the user at install.

![SOP closed-loop flowchart v3.1](references/assets/sop_flowchart.png)

## What it does

| Stage | How | Entry point |
|---|---|---|
| Install Gate | Company profile required → Soul Seven Kit content check → user attestation with content fingerprint; until all three pass, search / send scripts refuse to run | `scripts/onboarding.py start` |
| Data Access Layer | Own customer DB and SaaS / customs / CRM exports imported into one table; three sending routes (business-mailbox keys, hosted multi-mailbox warm-up, MCP connector); CRM sync; daily Data Triggers | `data_import.py` · `mail_setup.py` · `crm_sync.py` · `triggers.py` |
| Self-replenishing engine | Four-axis rotation: Depth (companies → decision makers → deep-dive) · Reach (near → far) · Height (high → low) · Breadth (core → wide → max) | `search_customers.py replenish` |
| Step 1 Search | 15 discovery channels + public search queries for 10 social platforms + 30 procurement-chain titles; anything that needs a login is manual | `search_customers.py queries / channels / social` |
| Step 2 Research | Evidence tiers S1/S2/S3; ≥1 S1 or 2 independent S2 before tagging; the brand name does not decide the need | `references/research_guide.md` |
| Step 3 Positioning | Dual tags (need tag + solution tag) with rule-conflict blocking | `search_customers.py conflict-check` |
| Step 4 Writing | Recipient's native language, ≤120 words, plain text, S1/S2 facts only | `references/email_templates.md` |
| Step 5 Sending | Dry run → human approval → named decision makers only → local window → daily cap → automatic opt-out header | `decision_maker_sender.py` · `batch_sender.py` |
| Step 6 Follow-up | Cooldown 3/3/10 days, 4 e-mails at most; social 1-3-7-21; bounces blacklisted for good | `imap_scanner.py` · `csv_ops.py cooldown` |
| Step 7 WhatsApp | Triggered; validate → test number → one by one → hard stop at 200 → screenshot audit | `wa_bulk_sender.py` |
| Step 8 Review | Win attribution, omni-channel review, weekly kit write-back | `review_success` · `wa_review` |

## Install

```bash
git clone https://github.com/JanefurZhou/b2b-customer-dev-kit.git
cd b2b-customer-dev-kit
python3 scripts/onboarding.py start        # new-install checklist
python3 scripts/onboarding.py init         # blank company profile
# fill config/company_profile.json and soul_seven_kit/, then:
python3 scripts/onboarding.py kit-check
python3 scripts/onboarding.py check        # → READY
python3 scripts/data_import.py inspect <your_customers.xlsx>
python3 scripts/mail_setup.py providers    # business-mailbox setup paths
python3 scripts/consistency_audit.py       # in-package consistency check
```

Python 3.10+ standard library only. SMTP / IMAP / CRM keys live in environment variables and never in files.

## Layout

```
SKILL.md                 skill entry point and contract
CHANGELOG.md             version history
scripts/                 all scripts (standard library, no third-party dependencies)
references/              SOP, search workflow, e-mail templates, social playbooks, mailbox setup, SaaS integration, triggers, flowchart
examples/                blank profile and data templates, three fictional industry profiles
docs/training/           training material: full script, 20-minute version, conversational talk, slide outline
zh/                      Chinese edition (same version, same structure, Chinese docs and training material)
```

## Training material

`docs/training/` holds four teaching documents that go with the flowchart, for explaining the logic to a team or a new hire. The Chinese versions are in `zh/docs/training/`.

## Quality

- In-package consistency check `scripts/consistency_audit.py`: 15 dimensions A–O, comparing script constants with documentation term by term.
- External audit with [Skill-Self-Check](https://github.com/xenos2025/Skill-Self-Check): hard gates pass, ship-safety static scan pass; results in `references/skill_self_check_report.md`, per-file safety review in `references/ship_safety_review.md`.

## Boundaries

- Public search and no-registration paths only; platform logins, connection requests, DMs and group joins are done manually by the user.
- Ships no customer database; guarantees no win rate; every numeric rule comes from the SOP inside the package, and warm-up tiers and similar values are adjustable defaults.
- Third-party service parameters quoted in the docs carry their official source; see `references/mail_setup.md` and `references/saas_integration_guide.md`.

## License

[CC BY-NC 4.0](LICENSE): use, modify and share non-commercially with attribution; contact the author before commercial use.

## Encoding

All files are UTF-8. Scripts force UTF-8 output on start and write CSV with a BOM, so files open cleanly in Excel on Chinese Windows and redirected output is not garbled. The root edition is fully in English; `data_import.py`, `crm_sync.py` and `wa_bulk_sender.py` still recognise Chinese column headers on purpose so Chinese-language spreadsheets import without renaming.
