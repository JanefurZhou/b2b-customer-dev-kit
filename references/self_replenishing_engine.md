# Self-replenishing customer engine (four-axis rotation · pool floor · data triggers)

> Goal: fresh, well-matched candidate customers every day; a customer pool that never runs dry; never burn through the easy markets in one go.
> Progress is measured and driven on four axes: **Height, Breadth, Depth, Reach**. Each run takes exactly one tier on each axis and advances step by step.

---

## 1. The four axes

| Axis | What it measures | Where the tiers come from | How the engine applies it |
|---|---|---|---|
| **Height** | Customer value tier: hit the most valuable tier first | order of `targeting.customer_levels` = high to low (high-value / large-account tiers first) | drops one tier after every region has had a full round |
| **Breadth** | How wide the search is: how many ways to find the same tier | `core` core combinations → `wide` + scenario / intent axis → `max` + every side axis (channel sites / sub-segments / certifications) | turns slowest; widens one tier only after a full Height round |
| **Depth** | How deep one market is mined: from companies to people to the existing pool | `d1_company` company-level discovery → `d2_decision` decision-maker penetration (procurement-chain titles) → `d3_stock` deep-mining the existing pool (look-alikes of won customers / reference brands, other roles at sent-but-unanswered accounts) | turns fastest: three consecutive runs on the same "region × tier" go from shallow to deep |
| **Reach** | Market radius and time span: near to far, never running out over the long run | order of `targeting.target_regions` = near to far (won / most familiar / closest time-zone markets first) | moves to the next region after a full Depth round |

**Advance order**: Depth (fastest) → Reach → Height → Breadth (slowest).
**One full coverage cycle** = regions × tiers × 3 (Depth) × 3 (Breadth) runs; `status` prints this number instead of hard-coding it.
Example: 6 regions × 4 tiers → 6 × 4 × 3 × 3 = 216 runs; once a day that is about 7 months per cycle, then it starts over on the latest data.

**Where d3 seeds come from** (all from your own data; with none it falls back to d2 and says so):
- won customer brands in `data/success_cases.csv` → search "companies like X / X competitors / X customers"
- `targeting.reference_brands` in the profile → same
- accounts in `data/sent_history.csv` with ≥2 e-mails sent and no reply → search other decision roles at that company (change the person, not the company)

---

## 2. The three mechanisms

### Mechanism 1: pool floor (never dry)
- Customer pool = `$B2B_DATA_DIR/customer_db.csv` (built by `data_import.py`: own customer DB + SaaS / customs / CRM exports + search results).
- **Sendable cold-outreach candidates** = has an e-mail + not in `sent_history` + relation is not existing customer / do-not-contact / competitor. Existing customers go through the repeat-order track, never cold outreach.
- **Two-criteria replenish trigger** (whichever breaks first):
  - hard red line: sendable count < `--floor` (default 100).
  - reserve line: sendable days < `--ahead-days` (default 30 days). Sendable days = sendable count ÷ `--daily-target` (default 100).
- All three numbers are adjustable defaults of this skill; set them to your sending capacity.

### Mechanism 2: four-axis state machine
- State lives in `search_state.json`: `depth_idx / region_idx / level_idx / breadth_idx / run_count / history`.
- v3.0 state files (without `depth_idx`) are upgraded automatically; history is kept.

### Mechanism 3: Data Triggers + scheduling
- `triggers.py scan`: scans the customer pool and data tables once a day and writes `reports/trigger_queue.json` (pool low, new import file, follow-up due, new reply, bounce spike, WhatsApp lead, warm-up step, CRM sync due, weekly review). See `references/data_access_and_triggers.md`.
- `search_customers.py schedule`: resident process that runs "check pool → replenish if low → emit the four-axis queries" at a fixed time every day.
- Hosting options (platform scheduled task / cron / resident process): `references/automation_setup.md`.

---

## 3. Command reference

```bash
export B2B_DATA_DIR=data          # directory of the customer DB and data tables

# 1) is the pool high enough + which cell is next today (no data changed)
python3 scripts/search_customers.py replenish

# 2) custom red line and reserve, write today's queries and the warning
python3 scripts/search_customers.py replenish --floor 100 --daily-target 100 --ahead-days 60 \
    --emit queries_today.txt --warn-file pool_warning.txt

# 3) advance one cell even when the pool is sufficient
python3 scripts/search_customers.py replenish --force --emit queries_today.txt

# 4) four-axis progress: next cell, tier ladders, last 8 runs, runs needed for full coverage
python3 scripts/search_customers.py status

# 5) resident scheduler: runs at 09:00 every day (Ctrl+C to stop)
python3 scripts/search_customers.py schedule --at 09:00 --floor 100 --ahead-days 30
```

**Next step in the loop**: `queries_today.txt` → check each public result with search / browser tools → `filter results.json --against $B2B_DATA_DIR/customer_db.csv` to de-dup and grade → research sets need_tag + solution_tag → into the pipeline → send (DRY_RUN check first) → sending consumes the sendable pool → `triggers.py scan` decides the next day whether to replenish.

---

## 4. Recommended rhythm

| Frequency | Action | Command |
|---|---|---|
| Daily (automatic) | trigger scan + pool check + four-axis replenish | `triggers.py scan`, `replenish --emit` |
| Daily (human) | handle triggers that need sign-off; verify today's queries one by one → de-dup → research → DRY_RUN → send | `filter` + the senders |
| Weekly | four-axis progress, pool health, bounce rate; weekly write-back into the kit | `status`, `email_dashboard.py`, `triggers.py reviewed` |
| Monthly | adjust region order (Reach) and tier order (Height); tune floor / ahead-days | edit `company_profile.json`, then re-confirm |

---

## 5. Data iron rule

The engine only reads the customer DB and only produces "today's queries" and the trigger queue; it never changes customer data or sends anything on its own.
Adding to the DB, changing tags, sending e-mail / WhatsApp, pushing to a CRM all require research and human confirmation (see the iron rules in SKILL.md).
