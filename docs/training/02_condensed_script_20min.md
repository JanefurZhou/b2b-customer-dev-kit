# B2B Customer Development SOP v3.1 · 20-minute condensed script

> For: explaining the logic to management or colleagues from other departments, without command details. Use with flowchart v3.1.
> Pacing: opening 2 min → four blocks of 4 min each → closing 2 min. Each block covers one problem, one mechanism, one takeaway.

---

## Opening (2 min)

This chart is a loop, not a line. The gate is at the top, the seven steps in the middle, and the review at the bottom writes its conclusions back to the top before the next round.

It solves three problems:
- Three months after an e-mail went out, can we trace "why we sent it to this person"?
- Can a new hire follow the experience of the senior salesperson?
- Once the AI does part of the work, is there a brake?

Four blocks follow: before starting, finding customers, sending, getting results back.

---

## Block one: before starting — the gate and data access (4 min)

**Problem**: why can't we just install and use it?

**Mechanism**:
- Three-check gate: company profile complete, the seven files for the AI pass a content health check, the user confirms. After confirmation a content fingerprint is recorded; any later edit makes the scripts stop and ask for re-confirmation.
- Data access: the tool ships no customer database; at install you declare where your customer DB comes from. On import, existing customers, do-not-contact and peers never enter the cold pool. Sending channel, one of three: business mailbox key, hosted multi-mailbox warm-up, or an MCP connector that creates drafts. CRM push is a dry run by default.
- Data Triggers once a day: pool too small, new files, follow-ups due, new replies, bounce anomalies — into a to-do queue. They only remind and stop; they never send for you.

**One line**: say clearly who we are, what we sell, whom we look for and what we send with, before any automation starts.

---

## Block two: finding customers — four-axis rotation, search, research, positioning (4 min)

**Problem**: how do we keep the pool from drying up without using it up in one go?

**Mechanism**:
- Four-axis replenishment: Depth rotates fastest (companies → decision makers → deep-dive the stock), Reach from near to far, Height from high to low, Breadth slowest (core terms → broad terms). Queries differ every day; a market counts as covered only after a full cycle.
- Search uses public paths only; anything that needs a login is manual. Three Iron Rules of Search: check the DB first; watch the funnel and change direction when duplicates exceed 40% or the named rate drops below 20%; wide entry, strict sending.
- Research is the core and cannot be skipped. Evidence tiers: S1 the company's own statements, S2 third parties, S3 guesses. At least one S1 or two independent S2 before tagging; S3 only goes to a human. The brand name does not decide the need; research does.
- Need positioning produces dual tags: which product line to push, which hook to use.

**One line**: search quality is not how many you found, but how many are truly new and how many have reliable evidence.

---

## Block three: sending — writing and sending (4 min)

**Problem**: how do we make sure every e-mail is right and safe?

**Mechanism**:
- Writing: recipient's native language, 120 words or fewer, plain text, S1 and S2 facts only, follow-ups must change angle and bring news.
- Three pre-send checks: named mailbox, de-duplicated, notes complete. Any failure goes back.
- Sending: dry run first, read every e-mail, send for real only after confirming. Named decision makers only; the recipient's local weekday window; no more than 200 a day; 30 seconds apart. Hosted mailboxes have caps per warm-up tier and pause automatically when the bounce rate is exceeded. Every e-mail carries an opt-out automatically.

**One line**: sending is the only truly outbound action; dry run, window, cap and opt-out are all mandatory.

---

## Block four: getting results back — follow-up, WhatsApp, review (4 min)

**Problem**: how do we manage after sending, and how does this round's experience become next round's rules?

**Mechanism**:
- Follow-up: e-mail cooldowns of 3, 3, 10 days, four e-mails at most; social 1, 3, 7, 21 days; one customer, one channel per day. Bounce = blacklist and permanent stop; reply = to a human; no reply after the fourth e-mail = stop generic mailboxes and switch channel.
- WhatsApp is triggered: three e-mails without reply, high value, or the customer gave their number — one of the three starts it. Validate the list, send to the test number first, then one by one, 8 to 15 seconds apart, hard stop at 200.
- Review once a week: wins go into the case library with human-confirmed pain points; win attribution by region, tag, hook and channel; what went wrong this week is written back into the matching file as a rule change. Re-run the health check, then the next round.

**One line**: the output of a review is not a report; it is a change to the files.

---

## Closing (2 min)

Back to the three opening questions:

- Traceable: every e-mail maps to one customer, one tag, one piece of evidence, one send record.
- Transferable: the gate tells the new hire what to fill in; the flowchart tells them what to run at each step.
- Brakes: gate, fingerprint, dry run, window, cap, human sign-off — six of them.

Three iron rules: scripts read customer data and never edit it on their own; pain points, tags, sending, CRM pushes and quotes are human decisions; keys live in environment variables only.

This SOP does not guarantee a win rate. It guarantees that every failure tells you where it went wrong and where to fix it.

---

## What to cut when short on time

1. First cut the "Three Iron Rules of Search" details in block two; keep only "check the DB first, watch the funnel".
2. Then cut the WhatsApp paragraph in block four; say only "WhatsApp is triggered and stricter than e-mail".
3. Last, cut the three sending routes in block one; say only "keys never go into files".
Never cut the three opening questions or the closing callback.
