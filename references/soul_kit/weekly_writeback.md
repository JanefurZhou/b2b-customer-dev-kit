# Weekly write-back: where the mistake is, that is the file you fix

> Source: the "review write-back" method from soul-seven-kit, wired into this skill's Step 0 Omni-channel Review and Step 8 Win Review + Kit Write-back.
> Trigger: once a week (ideally the same day as `csv_ops.py review_success` / `wa_review.py review`).

## Three steps

1. **Read the records**: this week's conversations, HEARTBEAT, sending reports (`batch_report_*.json` / `decision_maker_report_*.json`), bounce-scan results. Look for three kinds of problems only: what was answered wrong / what was skipped / where it overstepped.
2. **Attribute**: map every problem to **exactly one** file.
3. **Write back**: change the rule, not just the one answer; afterwards update HEARTBEAT's "Human intervention" and "Next improvement", then run `python3 scripts/onboarding.py kit-check`.

| Symptom (customer-development scenario) | Cause | Write back to |
|---|---|---|
| E-mail wording / tone inconsistent | way of speaking undefined | SOUL.md |
| Loses track of which customers it serves in a new conversation | identity unclear | IDENTITY.md |
| Skipped DB de-dup / research / the three checks | SOP has a gap | AGENTS.md |
| Sent / quoted before the boss confirmed | brake missing or unclear | AGENTS.md |
| Wrong script, wrong field, DRY_RUN not run first | tool usage not explained | TOOLS.md |
| Same pit twice (e.g. cold e-mail to a generic mailbox) | pit not recorded | TOOLS.md |
| Forgot pool status, asked for background again | state not updated | MEMORY.md |
| Wrong reporting format | boss preference not written | USER.md |
| Errors not logged, cannot trace | no log kept | HEARTBEAT.md |
| Scheduled replenish / review did not run | schedule not in the files | AGENTS.md or HEARTBEAT.md |

**Cannot tell which file to fix → the files are unclear; go back and rewrite that file.**

## Rhythm

| Frequency | Action |
|---|---|
| Daily | fix the file on the spot when an answer is wrong |
| Weekly | full three-step review, write back every attribution; update MEMORY "Conclusions of the last review" |
| Monthly | if the files get too thick, consolidate the stable parts and delete outdated content |

## Review report template for the user

> This week's review found N problems, attributed as follows:
> 1. <symptom> → <which file lacks what> → added to <file>
> 2. …
> Kit health check 7/7 passed, HEARTBEAT updated.
