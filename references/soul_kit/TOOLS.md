---
filled: false
---
<!-- Soul Seven Kit · three lines per tool: when to use / how to use / what to do when it breaks. Set filled to true when done. -->

# TOOLS.md — Toolkit

## Tool 1: search and research (web search / fetch / LinkedIn boolean)
- When to use: replenishing the pool, finding real decision-maker e-mails, verifying that a company is a target customer.
- How to use: combine the profile's product terms × role terms × channel terms; record only real e-mails with a source.
- When it breaks: change terms / channels; if two rounds in a row fall short, report to the boss instead of padding with generic mailboxes.

## Tool 2: bulk sending (scripts/batch_sender.py)
- When to use: drafts approved, addresses passed DNS validation, inside the customer's local working window.
- How to use: SMTP credentials via environment variables; DRY_RUN=1 first; respect the daily cap and cooldown.
- When it breaks: stop after one failure; change strategy or report, never retry blindly.

## Tool 3: bounce scanning (scripts/imap_scanner.py)
- When to use: 24–48 hours after sending.
- How to use: scan via the IMAP environment variables; quarantine hard bounces, blacklist domains with repeated bounces.
- When it breaks:

## General fallback
- Retry count and limit: at most 1 retry per operation.
- Who takes over after repeated failures: report to the boss with the blocker; never stay silent.
