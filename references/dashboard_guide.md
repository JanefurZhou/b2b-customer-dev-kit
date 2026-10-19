# E-mail tracking dashboard guide

> Generates a visual HTML dashboard tracking the customer pool, sending progress, bounces, replies, success cases, need tags and follow-up stages, and compiles the WhatsApp contact list.

## Generate the dashboard

```bash
python3 scripts/email_dashboard.py <data.json> [output.html] [title]
```

Besides the HTML dashboard, the run also exports **`wa_targets.json`** (WhatsApp contact list) into the same directory for the WhatsApp outreach flow.

## Dashboard modules

1. **Customer pool overview bar** — unique pool size, reached / coverage, reserve pool, moved to WA, blacklist, with a progress bar
2. **Success case card wall** (always on top) — ✅ confirmed / ⏳ pain points awaiting confirmation; click to expand the full customer record; cards of existing customers with a WA number carry a clickable "📱 WhatsApp" badge and, when expanded, a green "Open WhatsApp follow-up (repeat-order message pre-filled)" button that calls wa.me directly
3. **Review summary** — number of success cases, confirmed / pending pain points, total deal amount, region / hook split, keywords, Top 5 cases
4. **Sending funnel** — sent → delivered → opened → replied
5. **Need tag distribution** (need_tag) — the core asset of research-first outreach, horizontal bars
6. **Follow-up stage distribution** — 5-level cooldown (1st / 2nd / 3rd e-mail → stopped → moved to WhatsApp)
7. **WhatsApp contact list** — customers with a WA number, split into "📩 WA pending / ✅ moved to WA", filterable, one-click copy of pending numbers; the number itself is a clickable wa.me link, and the rightmost "one-click" column shows "📩 Send outreach" (first-contact message pre-filled, first) for pending customers and "💬 Follow up" (repeat-order message pre-filled, repeat) for converted ones

> **Consistent WhatsApp behaviour**: the card wall and the contact list share the single `wa_link(num, contact, brand, stage)` function at the top of the script to build wa.me links and pre-filled text. `stage="first"` first contact, `stage="repeat"` existing-customer repeat / follow-up; identical behaviour across the dashboard.
8. **Sending trend** — bar chart of sends / bounces by date
9. **Region distribution** — horizontal bars by region
10. **Generic mailbox vs named decision-maker mailbox delivery comparison**

## Input JSON format

```json
{
  "pool": {
    "total_unique": 11148,
    "pipeline_reserve": 320,
    "blacklist": 45,
    "wa_contacts": 12
  },
  "records": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "title": "Buyer",
      "region": "Europe",
      "status": "sent",
      "email_type": "named",
      "sent_date": "2026-06-15",
      "batch": "Batch 1",
      "need_tag": "line_a",
      "hook_type": "compliance",
      "subject": "Email subject",
      "whatsapp": "+46 70 123 4567"
    }
  ],
  "followups": [
    {"stage": 1},
    {"stage": 2},
    {"stage": 5}
  ],
  "milestones": [
    {"date": "6/15", "event": "First batch sent", "result": "90 delivered / 10 bounced", "color": "#3b82f6"}
  ],
  "success_cases": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "title": "Buyer",
      "region": "Europe",
      "order_amount": 15000,
      "success_points": "1. personalised hook 2. named decision-maker e-mail",
      "hook_type": "personalized_hook",
      "need_tag": "line_b",
      "language": "EN",
      "confirmed": true,
      "ai_analysis": "Possible pain point: current supplier's delivery times are unstable",
      "first_sent_date": "2026-06-15",
      "reply_date": "2026-06-18",
      "order_date": "2026-07-01",
      "whatsapp": "+39 300 000 0001"
    }
  ]
}
```

## Field reference

### records (one per e-mail sent)
- `status` values: `sent` / `bounced` / `opened` / `replied` / `wa_only` moved to the WA channel
- `email_type`: `named` decision maker / `generic` generic mailbox (if empty, derived from the mailbox prefix)
- `need_tag`: the product / service lines you define in `positioning.need_tags` (e.g. `line_a` / `line_b`), plus the reserved values `multi` / `unknown` / `review`; shown as is
- `hook_type` (= solution_tag): one of the 11 generic decision drivers, shown with a label — `compliance` compliance first / `sustainability` sustainability first / `quality_upgrade` quality upgrade / `cost` cost first / `speed` speed first / `low_commitment` low-commitment trial / `innovation` new product / new approach / `exclusive_custom` custom / exclusive / `one_stop` one-stop / `dedicated_service` dedicated service / `strategic_scale` scale / strategic
- `whatsapp`: **only records with a WA number enter the WhatsApp contact list**. Spaces / brackets in the number are cleaned automatically

### followups (follow-up stage distribution)
- `stage`: `1` first follow-up / `2` second / `3` third / `4` stopped / `5` moved to WhatsApp

### success_cases (the script uses this new field set)
- `confirmed`: `true` = pain point confirmed by the user, `false` = preliminary AI analysis awaiting confirmation
- `ai_analysis`: preliminary AI pain-point analysis (shown when confirmed=false)
- `success_points`: success points after user confirmation
- `order_amount`: deal amount (number)
- `first_sent_date` / `reply_date` / `order_date`: timeline
- `whatsapp`: WA numbers of won customers also enter the contact list (marked "already in contact" by default)

## WhatsApp loop (e-mail → WA)

The dashboard compiles every customer with a `whatsapp` number into two groups:

- **WA pending**: has a WA number, but the e-mail status is not `wa_only` and `wa_status:"sent"` is not set — i.e. not yet contacted on WhatsApp. **These are the targets for a WhatsApp outreach message.**
- **Moved to WA (done)**: status=`wa_only` or already marked as sent on WA.

Structure of the exported `wa_targets.json`:
```json
{
  "pending": [ {"whatsapp": "...", "brand": "...", "contact": "...", "region": "...", "need_tag": "...", "email": "..."} ],
  "done": [ ... ],
  "all": [ ... ]
}
```

**Next**: feed the `pending` list of `wa_targets.json` to the WhatsApp outreach flow, match the hook by `need_tag`, and send one by one. After sending, write back with `csv_ops.py mark_wa_only <email> <wa> <brand> <name>`; the next dashboard run moves that customer to "moved to WA" automatically, avoiding repeat contact.

## Daily reporting flow
1. Collect the day's sending data + pool / blacklist counts → build the JSON
2. Run `email_dashboard.py` → HTML dashboard + `wa_targets.json`
3. Distil 3–5 key points for the user:
   - today's outreach / sending count, remaining pool coverage
   - bounce rate / reply rate
   - reserve pool remaining
   - number of WA-pending customers (WhatsApp outreach can be scheduled)
   - success-case progress, anomalies or items needing attention
