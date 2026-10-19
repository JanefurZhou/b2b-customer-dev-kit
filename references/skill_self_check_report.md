# Skill-Self-Check audit result (v3.1, English edition)

Tool: full run_full_audit of [xenos2025/Skill-Self-Check](https://github.com/xenos2025/Skill-Self-Check) (static audit; the audited skill is not executed).

| Check | v2.2 (before) | v3.1 (final) |
|---|---|---|
| hard-gates | fail (critical 1.7 description lacks a "Use when" trigger phrase; should_fix 2.5 negation density 12) | **pass** (critical 0; one should_fix left: 2.5 negation density 10 — the red-line section is deliberately written as prohibitions) |
| ship-safety | stop_ship (critical CMD.1 `../csv_ops.py` path missing ×2; critical EXT.1 bounce scan without dry run; should_fix EXT.1 DNS validation without dry run; should_fix EXT.3 PowerShell ×3) | **static_pass** (critical 0; only EXT.3 PowerShell ×3 remain, manually reviewed; the v3.1 `crm_sync.py` and `mail_setup.py` only carry info-level "has a dry-run switch, confirm default does not send", checked item by item in `ship_safety_review.md`) |
| role-contract | not_assessed (no role contract) | **pass** (`role-contract.json` single_context / single_role) |
| workflow-prompt | not_assessed | **not_applicable** (scripts call no model and have no multi-step prompt chain, declared in SKILL.md) |
| score basic_usable | 4/5 | **5/5** |
| score contract_clarity | 5/5 | **5/5** |
| score support_kit | 3/4 | **4/4** (record schema section added to SKILL.md) |

In-package self-check: `python3 scripts/consistency_audit.py` → FAIL 0 (dimensions A–O, incl. flowchart consistency, Data Access Layer and four-axis rotation).

Re-run:
```bash
git clone https://github.com/xenos2025/Skill-Self-Check
cd Skill-Self-Check/skills/skill-self-check/scripts
# run the run_full_audit script in that directory: <this skill directory> --out-dir <output directory> --pretty
```
The in-package self-check runs from this skill directory: `python3 scripts/consistency_audit.py`.
