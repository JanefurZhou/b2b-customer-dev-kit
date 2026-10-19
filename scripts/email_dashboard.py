#!/usr/bin/env python3
"""B2B customer development — e-mail tracking dashboard generator (skill v3.1)
Usage: python3 scripts/email_dashboard.py <data.json> [output.html] [title]

Input JSON format:
{
  "records": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "title": "Buyer",
      "region": "US",
      "status": "sent",          # sent / bounced / opened / replied
      "email_type": "named",     # generic / named
      "sent_date": "2026-06-15",
      "batch": "Batch 1",
      "need_tag": "line_a",
      "hook_type": "compliance",
      "subject": "Email subject"
    }
  ],
  "milestones": [
    {"date": "6/15", "event": "first batch sent", "result": "90 delivered / 110 bounced", "color": "#3b82f6"}
  ],
  "success_cases": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "region": "US",
      "order_amount": 15000,
      "success_points": "1. personalised hook 2. named decision-maker send",
      "hook_type": "personalized_hook",
      "need_tag": "line_b",
      "language": "EN",
      "confirmed": true,           # true = confirmed by the user, false = preliminary AI analysis awaiting confirmation
      "ai_analysis": "possible pain point: current supplier delivers unreliably",  # preliminary AI analysis
      "first_sent_date": "2026-06-15",
      "reply_date": "2026-06-18",
      "order_date": "2026-07-01"
    }
  ]
}

Output: HTML file
"""

import json, sys, os, html as html_mod
from datetime import datetime
from collections import Counter
from urllib.parse import quote
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# The repeat-order follow-up one-liner comes from profile.offer.repeat_hook (generic; neutral sentence when empty)
def _load_repeat_hook():
    try:
        import os as _o, sys as _s
        _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
        import config as _c
        prof = _c.load_profile(require_complete=False) or {}
        return (_c.get(prof, "offer.repeat_hook", "") or "").strip()
    except Exception:
        return ""


_REPEAT_HOOK = _load_repeat_hook()

def wa_digits(num):
    """Extract the digits of a WhatsApp number (for wa.me links)."""
    return "".join(ch for ch in str(num or "") if ch.isdigit())

def wa_link(num, contact="", brand="", stage="first"):
    """Build the wa.me link (with pre-filled text) in one place.
    stage='first' first outreach message; stage='repeat' repeat-order follow-up with a won customer.
    The card wall and the outreach list share this function so the call logic stays consistent."""
    d = wa_digits(num)
    if not d:
        return ""
    # First name only, and none of the phrases banned in references/email_templates.md
    # (came across / could be a great fit / we'd love to). The text is only pre-filled:
    # WhatsApp opens it for the user to review and edit before pressing send.
    parts = str(contact or "").replace(",", " ").split()
    name = parts[0] if parts else "there"
    who = brand or "your team"
    if stage == "repeat":
        hook = (_REPEAT_HOOK or "we have an update that may be useful for you").rstrip(".")
        msg = (f"Hi {name}, quick follow-up from our side: {hook}. "
               f"Want me to send {who} the details?")
    else:
        msg = (f"Hi {name}, following up on my email to {who}. "
               "Is this the best place to share a short intro?")
    return f"https://wa.me/{d}?text={quote(msg)}"

def esc(text):
    """HTML escape"""
    return html_mod.escape(str(text)) if text else ""

def load_data(filepath):
    with open(filepath, 'r', encoding="utf-8-sig") as f:
        return json.load(f)

def analyze_email_type(email):
    """Decide from the mailbox prefix whether it is a generic mailbox"""
    try:
        import config as _c
        generic_prefixes = [p + "@" for p in _c.GENERIC_MAILBOX_PREFIXES]
    except Exception:
        generic_prefixes = ['info@', 'contact@', 'sales@', 'hello@', 'support@', 'office@']
    email_lower = email.lower()
    for prefix in generic_prefixes:
        if email_lower.startswith(prefix):
            return 'generic'
    return 'named'

def generate_html(data, title="B2B E-mail Outreach Dashboard"):
    records = data.get("records", [])
    milestones = data.get("milestones", [])
    success_cases = data.get("success_cases", [])
    # Customer pool / reserve pool / blacklist / follow-up stages (data layer and step 6 of the SOP map)
    pool = data.get("pool", {})            # {"total_unique": 11148, "pipeline_reserve": 320, "blacklist": 45, "wa_contacts": 12}
    followups = data.get("followups", [])  # [{"stage": 1..5, ...}] follow-up stage distribution; stage=1/2/3 = nth follow-up, 4 = stopped, 5 = moved to WA
    
    # fill email_type
    for r in records:
        if not r.get("email_type"):
            r["email_type"] = analyze_email_type(r.get("email", ""))
    
    # ========== Statistics ==========
    total_sent = len(records)
    total_bounced = sum(1 for r in records if r.get("status") == "bounced")
    total_delivered = total_sent - total_bounced
    total_opened = sum(1 for r in records if r.get("status") in ("opened", "replied"))
    total_replied = sum(1 for r in records if r.get("status") == "replied")
    delivery_rate = round(total_delivered / total_sent * 100, 1) if total_sent else 0
    open_rate = round(total_opened / total_delivered * 100, 1) if total_delivered else 0
    reply_rate = round(total_replied / total_delivered * 100, 1) if total_delivered else 0
    
    # by region
    region_counter = Counter(r.get("region", "Unknown") for r in records)
    region_bounced = Counter(r.get("region", "Unknown") for r in records if r.get("status") == "bounced")
    
    # trend by date
    date_counter = Counter()
    date_bounced = Counter()
    for r in records:
        d = r.get("sent_date", "")
        if d:
            date_counter[d] += 1
            if r.get("status") == "bounced":
                date_bounced[d] += 1
    
    # generic vs decision-maker delivery rate
    named_sent = sum(1 for r in records if r.get("email_type") == "named")
    named_bounced = sum(1 for r in records if r.get("email_type") == "named" and r.get("status") == "bounced")
    generic_sent = sum(1 for r in records if r.get("email_type") == "generic")
    generic_bounced = sum(1 for r in records if r.get("email_type") == "generic" and r.get("status") == "bounced")
    named_delivery = round((named_sent - named_bounced) / named_sent * 100, 1) if named_sent else 0
    generic_delivery = round((generic_sent - generic_bounced) / generic_sent * 100, 1) if generic_sent else 0
    
    # ========== need_tag distribution (core asset: research before outreach) ==========
    # need_tag values are user-defined in profile.positioning.need_tags and shown as-is;
    # below are only the generic reserved values and display names of the decision-driver tags (solution_tag).
    need_tag_labels_map = {
        "multi": "multiple lines", "unknown": "to research", "review": "to review", "open": "open",
        "compliance": "compliance first", "sustainability": "sustainability first", "quality_upgrade": "quality upgrade",
        "cost": "cost first", "speed": "speed first", "low_commitment": "low-commitment trial",
        "innovation": "new product / new approach", "exclusive_custom": "custom / exclusive", "one_stop": "one-stop",
        "dedicated_service": "dedicated service", "strategic_scale": "scale / strategic",
    }
    need_counter = Counter(r.get("need_tag", "unknown") or "unknown" for r in records)
    need_sorted = sorted(need_counter.keys(), key=lambda x: need_counter[x], reverse=True)
    need_labels = json.dumps([need_tag_labels_map.get(t, t) for t in need_sorted])
    need_values = json.dumps([need_counter[t] for t in need_sorted])
    
    # ========== Follow-up stage distribution (step 6: 5-level cooldown) ==========
    stage_names = {1: "1st follow-up", 2: "2nd follow-up", 3: "3rd follow-up", 4: "stopped", 5: "moved to WhatsApp"}
    stage_colors = {1: "#3b82f6", 2: "#6366f1", 3: "#8b5cf6", 4: "#94a3b8", 5: "#22c55e"}
    stage_counter = Counter(f.get("stage", 1) for f in followups)
    
    # ========== WhatsApp outreach list (e-mail → WA channel loop) ==========
    # Any record / success case that carries a WhatsApp number is picked up here for the later WA outreach flow
    def _digits(s):
        return "".join(ch for ch in str(s or "") if ch.isdigit() or ch == "+")
    wa_targets = {}   # de-duplicated by wa_number
    for r in records:
        wa = _digits(r.get("whatsapp", ""))
        if not wa:
            continue
        # status wa_only or stage 5 = already moved to WA; otherwise WA pending
        is_sent_wa = (r.get("status") == "wa_only") or (r.get("wa_status") == "sent")
        wa_targets[wa] = {
            "whatsapp": wa, "brand": r.get("brand", ""), "contact": r.get("contact", ""),
            "region": r.get("region", ""), "need_tag": r.get("need_tag", ""),
            "email": r.get("email", ""), "email_status": r.get("status", ""),
            "wa_sent": is_sent_wa,
        }
    # WhatsApp numbers from won cases are included too (high-value customers, default: to follow up / nurture)
    for c in success_cases:
        wa = _digits(c.get("whatsapp", ""))
        if wa and wa not in wa_targets:
            wa_targets[wa] = {
                "whatsapp": wa, "brand": c.get("brand", ""), "contact": c.get("contact", ""),
                "region": c.get("region", ""), "need_tag": c.get("need_tag", ""),
                "email": c.get("email", ""), "email_status": "won", "wa_sent": True,
            }
    wa_list = list(wa_targets.values())
    wa_pending = [w for w in wa_list if not w["wa_sent"]]   # can receive a WA outreach message now
    wa_done = [w for w in wa_list if w["wa_sent"]]           # moved to WA / already in contact
    
    # ========== Success case statistics ==========
    total_cases = len(success_cases)
    total_amount = sum(c.get("order_amount", 0) for c in success_cases)
    
    # confirmed vs pending
    confirmed_cases = [c for c in success_cases if c.get("confirmed", False)]
    pending_cases = [c for c in success_cases if not c.get("confirmed", False)]
    
    # success cases by region
    case_region_counter = Counter(c.get("region", "Unknown") for c in success_cases)
    # by need_tag
    case_need_counter = Counter(c.get("need_tag", "unknown") for c in success_cases)
    # by hook_type
    case_hook_counter = Counter(c.get("hook_type", "unknown") for c in success_cases)
    
    # success-point keyword frequency
    word_freq = Counter()
    for c in success_cases:
        points = c.get("success_points", "")
        # naive tokenising: split on spaces / punctuation / list numbers
        tokens = points.replace(".", " ").replace(",", " ").replace(";", " ").replace("、", " ").split()
        for t in tokens:
            t = t.strip().strip("0123456789.、。，,")
            if len(t) >= 2:
                word_freq[t] += 1
    top_keywords = word_freq.most_common(10)
    
    # Top 5 cases (by amount)
    top5_cases = sorted(success_cases, key=lambda c: c.get("order_amount", 0), reverse=True)[:5]
    
    # ========== Chart.js data ==========
    # sending trend
    sorted_dates = sorted(date_counter.keys())
    trend_labels = json.dumps(sorted_dates)
    trend_sent = json.dumps([date_counter[d] for d in sorted_dates])
    trend_bounced = json.dumps([date_bounced.get(d, 0) for d in sorted_dates])
    
    # region distribution
    regions_sorted = sorted(region_counter.keys(), key=lambda x: region_counter[x], reverse=True)
    region_labels = json.dumps(regions_sorted)
    region_values = json.dumps([region_counter[r] for r in regions_sorted])
    region_bounced_values = json.dumps([region_bounced.get(r, 0) for r in regions_sorted])
    
    # success cases by region
    case_regions_sorted = sorted(case_region_counter.keys(), key=lambda x: case_region_counter[x], reverse=True)
    case_region_labels = json.dumps(case_regions_sorted)
    case_region_values = json.dumps([case_region_counter[r] for r in case_regions_sorted])
    
    # ========== Success case cards HTML ==========
    def case_card_html(case, idx):
        is_confirmed = case.get("confirmed", False)
        status_badge = '<span class="badge confirmed">✅ Confirmed</span>' if is_confirmed else '<span class="badge pending">⏳ Pending</span>'
        # WhatsApp badge + one-click call: won customer → repeat-order / new-range follow-up (stage=repeat)
        wa_num = case.get("whatsapp", "")
        wa_d = wa_digits(wa_num)
        wa_url = wa_link(wa_num, case.get("contact", ""), case.get("brand", ""), stage="repeat")
        wa_badge = (f'<a class="badge wa-has" href="{wa_url}" target="_blank" onclick="event.stopPropagation()" title="Open WhatsApp follow-up: {esc(wa_num)}">📱 WhatsApp</a>'
                    if wa_d else '<span class="badge wa-none">No WhatsApp</span>')
        
        # pain-point display
        if is_confirmed:
            points_display = esc(case.get("success_points", ""))
        else:
            ai_note = esc(case.get("ai_analysis", "AI analysis in progress"))
            user_note = case.get("success_points", "")
            if user_note:
                points_display = f'<span class="ai-hint">⏳ Awaiting user confirmation</span><br>AI analysis: {ai_note}<br>User note: {esc(user_note)}'
            else:
                points_display = f'<span class="ai-hint">⏳ Awaiting user confirmation</span><br>AI analysis: {ai_note}'
        
        return f'''
        <div class="case-card" onclick="toggleCaseDetail('detail-{idx}')">
            <div class="case-header">
                <div class="case-brand">{esc(case.get('brand', 'Unknown'))}</div>
                <div class="case-badges">{status_badge}{wa_badge}</div>
            </div>
            <div class="case-info">
                <span class="case-tag">{esc(case.get('region', ''))}</span>
                <span class="case-tag">{esc(case.get('contact', ''))}</span>
                <span class="case-amount">${case.get('order_amount', 0):,.0f}</span>
            </div>
            <div class="case-points" id="summary-{idx}">
                {points_display[:100]}{"..." if len(str(points_display)) > 100 else ""}
            </div>
            <div class="case-detail" id="detail-{idx}" style="display:none">
                <hr>
                <p><strong>Contact:</strong> {esc(case.get('contact', ''))} {esc(case.get('title', ''))}</p>
                <p><strong>E-mail:</strong> {esc(case.get('email', ''))}</p>
                {f"<p><strong>WhatsApp:</strong> <span class='wa-num'>{esc(wa_num)}</span></p><a class='wa-cta' href='{wa_url}' target='_blank' onclick=\"event.stopPropagation()\">📱 Open WhatsApp follow-up (repeat-order text pre-filled)</a>" if wa_d else "<p><strong>WhatsApp:</strong> <span style='color:#94a3b8'>not provided — ask on the next call</span></p>"}
                <p><strong>Region:</strong> {esc(case.get('region', ''))}</p>
                <p><strong>Need tag:</strong> {esc(case.get('need_tag', ''))}</p>
                <p><strong>Hook type:</strong> {esc(case.get('hook_type', ''))}</p>
                <p><strong>Language:</strong> {esc(case.get('language', ''))}</p>
                <p><strong>First sent:</strong> {esc(case.get('first_sent_date', ''))}</p>
                <p><strong>Reply date:</strong> {esc(case.get('reply_date', ''))}</p>
                <p><strong>Order date:</strong> {esc(case.get('order_date', ''))}</p>
                <p><strong>Order amount:</strong> ${case.get('order_amount', 0):,.0f}</p>
                <p><strong>Confirmation:</strong> {status_badge}</p>
                <p><strong>Success points:</strong><br>{points_display}</p>
                {"<p class='confirm-notice'>💡 This pain-point analysis has not been confirmed by the user; confirm it during the review</p>" if not is_confirmed else ""}
            </div>
        </div>'''
    
    case_cards = "\n".join(case_card_html(c, i) for i, c in enumerate(success_cases))
    
    # ========== Review summary panel ==========
    review_summary_html = ""
    if total_cases > 0:
        confirmed_count = len(confirmed_cases)
        pending_count = len(pending_cases)
        
        review_summary_html = f'''
        <div class="review-panel">
            <h3>📊 Review summary</h3>
            <div class="review-stats">
                <div class="review-stat">
                    <div class="review-number">{total_cases}</div>
                    <div class="review-label">Success cases</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#10b981">{confirmed_count}</div>
                    <div class="review-label">✅ Confirmed pain points</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#f59e0b">{pending_count}</div>
                    <div class="review-label">⏳ Pending pain points</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#6366f1">${total_amount:,.0f}</div>
                    <div class="review-label">Total won amount</div>
                </div>
            </div>
            {f'<div class="pending-notice">⚠️ {pending_count} cases have pain-point analyses awaiting user confirmation. Run the review flow; the AI lists candidate pain points for you to choose from.</div>' if pending_count > 0 else ''}
            <div class="review-charts">
                <div class="mini-chart">
                    <h4>Won cases · by region</h4>
                    <div style="position:relative;height:220px"><canvas id="caseRegionChart"></canvas></div>
                </div>
                <div class="mini-chart">
                    <h4>Won cases · by hook type</h4>
                    <div style="position:relative;height:220px"><canvas id="caseHookChart"></canvas></div>
                </div>
            </div>
            <div class="keywords-panel">
                <h4>🔑 Top 10 success-point keywords</h4>
                <div class="keywords">
                    {"".join(f'<span class="keyword" style="font-size:{max(12, min(24, freq*3))}px">{esc(word)}</span>' for word, freq in top_keywords)}
                </div>
            </div>
            <div class="top5-panel">
                <h4>🏆 Top 5 cases</h4>
                <table class="top5-table">
                    <tr><th>#</th><th>Customer</th><th>Region</th><th>Amount</th><th>Hook type</th><th>Confirmation</th></tr>
                    {"".join(f'<tr><td>{i+1}</td><td>{esc(c.get("brand",""))}</td><td>{esc(c.get("region",""))}</td><td>${c.get("order_amount",0):,.0f}</td><td>{esc(c.get("hook_type",""))}</td><td>{"✅" if c.get("confirmed") else "⏳"}</td></tr>' for i, c in enumerate(top5_cases))}
                </table>
            </div>
        </div>'''
    
    # ========== WhatsApp outreach list HTML ==========
    def wa_row_html(w):
        badge = '<span class="wa-badge done">✅ Moved to WA</span>' if w["wa_sent"] else '<span class="wa-badge todo">📩 WA pending</span>'
        need = need_tag_labels_map.get(w.get("need_tag", ""), w.get("need_tag", "") or "—")
        wa_num = w.get("whatsapp", "")
        wa_d = wa_digits(wa_num)
        # same call logic as the card wall: pending = first outreach text (first), moved = repeat/follow-up text (repeat)
        stage = "repeat" if w["wa_sent"] else "first"
        if wa_d:
            url = wa_link(wa_num, w.get("contact", ""), w.get("brand", ""), stage=stage)
            cta_label = "💬 Follow up" if w["wa_sent"] else "📩 Send outreach"
            num_cell = f'<a class="wa-num-link" href="{url}" target="_blank">{esc(wa_num)}</a>'
            action_cell = f'<a class="wa-row-btn" href="{url}" target="_blank">{cta_label}</a>'
        else:
            num_cell = '<span style="color:#cbd5e1">—</span>'
            action_cell = '<span style="color:#cbd5e1">—</span>'
        return f'''<tr data-wa-sent="{'1' if w['wa_sent'] else '0'}">
            <td>{badge}</td>
            <td><strong>{esc(w.get("brand",""))}</strong></td>
            <td>{esc(w.get("contact","") or "—")}</td>
            <td>{esc(w.get("region","") or "—")}</td>
            <td><span class="wa-need">{esc(need)}</span></td>
            <td class="wa-num">{num_cell}</td>
            <td>{esc(w.get("email","") or "—")}</td>
            <td>{action_cell}</td>
        </tr>'''
    wa_section_html = ""
    if wa_list:
        wa_rows = "\n".join(wa_row_html(w) for w in sorted(wa_list, key=lambda x: x["wa_sent"]))
        pending_nums = " ".join(w["whatsapp"] for w in wa_pending)
        wa_section_html = f'''
        <div class="panel wa-panel">
            <h2>📱 WhatsApp outreach list <span style="font-size:13px;color:#94a3b8;font-weight:400">(e-mail → WA channel loop; call directly to send outreach)</span></h2>
            <div class="wa-stats">
                <div class="wa-stat"><span class="wa-stat-num" style="color:#0ea5e9">{len(wa_list)}</span><span class="wa-stat-lbl">Have WhatsApp</span></div>
                <div class="wa-stat"><span class="wa-stat-num" style="color:#f59e0b">{len(wa_pending)}</span><span class="wa-stat-lbl">📩 WA outreach pending</span></div>
                <div class="wa-stat"><span class="wa-stat-num" style="color:#22c55e">{len(wa_done)}</span><span class="wa-stat-lbl">✅ Moved to WA / in contact</span></div>
            </div>
            <div class="wa-toolbar">
                <button class="wa-btn active" onclick="filterWA('all',this)">All</button>
                <button class="wa-btn" onclick="filterWA('todo',this)">📩 Pending only</button>
                <button class="wa-btn" onclick="filterWA('done',this)">✅ Moved only</button>
                <button class="wa-btn copy" onclick="copyWANums()">📋 Copy all pending numbers</button>
                <span class="wa-copy-tip" id="waCopyTip"></span>
            </div>
            <div style="overflow-x:auto">
            <table class="wa-table" id="waTable">
                <tr><th>Status</th><th>Customer</th><th>Contact</th><th>Region</th><th>Need tag</th><th>WhatsApp</th><th>E-mail</th><th>One-click</th></tr>
                {wa_rows}
            </table>
            </div>
            <textarea id="waPendingNums" style="position:absolute;left:-9999px">{esc(pending_nums)}</textarea>
            <p style="margin-top:10px;font-size:12px;color:#94a3b8">💡 "WA pending" = has a WhatsApp number but has not been contacted on WA yet. <code>wa_targets.json</code> is exported as well and can feed the WhatsApp outreach flow directly.</p>
        </div>'''

    # ========== Customer pool / data layer overview bar ==========
    pool_html = ""
    if pool:
        total_unique = pool.get("total_unique", 0)
        pipeline_reserve = pool.get("pipeline_reserve", 0)
        blacklist_cnt = pool.get("blacklist", 0)
        wa_cnt = pool.get("wa_contacts", 0)
        contacted = total_sent
        coverage = round(contacted / total_unique * 100, 1) if total_unique else 0
        pool_html = f'''
        <div class="pool-bar">
            <div class="pool-item">
                <div class="pool-num" style="color:#0ea5e9">{total_unique:,}</div>
                <div class="pool-lbl">Customer pool (unique)</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#6366f1">{contacted:,}</div>
                <div class="pool-lbl">Contacted (coverage {coverage}%)</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#f59e0b">{pipeline_reserve:,}</div>
                <div class="pool-lbl">🗂️ Reserve pool</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#22c55e">{wa_cnt:,}</div>
                <div class="pool-lbl">📱 Moved to WhatsApp</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#ef4444">{blacklist_cnt:,}</div>
                <div class="pool-lbl">🚫 Blacklist (bounced)</div>
            </div>
        </div>
        <div class="pool-progress">
            <div class="pool-progress-fill" style="width:{min(100,coverage)}%"></div>
            <span class="pool-progress-txt">Pool coverage {coverage}% ({max(0,total_unique-contacted):,} accounts still to work)</span>
        </div>'''

    # ========== Milestones HTML ==========
    milestone_html = ""
    if milestones:
        items = []
        for m in milestones:
            color = m.get("color", "#3b82f6")
            items.append(f'<div class="milestone-item" style="border-left-color:{color}"><strong>{esc(m.get("date",""))}</strong> {esc(m.get("event",""))} — {esc(m.get("result",""))}</div>')
        milestone_html = '<div class="milestones">' + "".join(items) + '</div>'
    
    # ========== Assemble the full HTML ==========
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f1f5f9; color:#1e293b; padding:20px; }}
.dashboard {{ max-width:1400px; margin:0 auto; }}
h1 {{ text-align:center; margin-bottom:8px; font-size:28px; color:#0f172a; }}
.subtitle {{ text-align:center; color:#64748b; margin-bottom:24px; font-size:14px; }}

/* success case card wall - always on top */
.success-section {{ background:#fff; border-radius:16px; padding:24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,.1); border:2px solid #10b981; }}
.success-section h2 {{ color:#059669; margin-bottom:16px; font-size:22px; }}
.case-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(320px,1fr)); gap:16px; }}
.case-card {{ background:#f0fdf4; border:1px solid #bbf7d0; border-radius:12px; padding:16px; cursor:pointer; transition:all .2s; }}
.case-card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(16,185,129,.15); }}
.case-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
.case-brand {{ font-weight:700; font-size:18px; color:#065f46; }}
.badge {{ padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }}
.badge.confirmed {{ background:#d1fae5; color:#065f46; }}
.badge.pending {{ background:#fef3c7; color:#92400e; }}
.badge.wa-has {{ background:#dcfce7; color:#15803d; cursor:pointer; text-decoration:none; }}
.badge.wa-has:hover {{ background:#22c55e; color:#fff; }}
.badge.wa-none {{ background:#f1f5f9; color:#94a3b8; }}
.case-badges {{ display:flex; gap:6px; align-items:center; flex-wrap:wrap; }}
.wa-cta {{ display:inline-block; margin-top:6px; padding:6px 14px; background:#22c55e; color:#fff !important; border-radius:8px; font-size:13px; font-weight:600; text-decoration:none; }}
.wa-cta:hover {{ background:#16a34a; }}
.case-info {{ display:flex; gap:8px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }}
.case-tag {{ background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:8px; font-size:12px; }}
.case-amount {{ font-weight:700; color:#059669; font-size:16px; }}
.case-points {{ color:#64748b; font-size:13px; line-height:1.5; }}
.case-detail {{ color:#475569; font-size:13px; line-height:1.8; }}
.case-detail hr {{ border:none; border-top:1px solid #e2e8f0; margin:8px 0; }}
.ai-hint {{ color:#d97706; font-weight:600; }}
.confirm-notice {{ background:#fef3c7; padding:8px 12px; border-radius:8px; color:#92400e; font-size:13px; margin-top:8px; }}

/* review summary panel */
.review-panel {{ background:#fff; border-radius:16px; padding:24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,.1); }}
.review-panel h3 {{ margin-bottom:16px; font-size:20px; }}
.review-stats {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:16px; margin-bottom:20px; }}
.review-stat {{ text-align:center; padding:16px; background:#f8fafc; border-radius:12px; }}
.review-number {{ font-size:28px; font-weight:700; }}
.review-label {{ font-size:13px; color:#64748b; margin-top:4px; }}
.pending-notice {{ background:#fef3c7; border:1px solid #fde68a; padding:12px 16px; border-radius:8px; color:#92400e; margin-bottom:16px; font-size:14px; }}
.review-charts {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }}
.mini-chart {{ background:#f8fafc; padding:16px; border-radius:12px; }}
.mini-chart h4 {{ margin-bottom:8px; font-size:15px; color:#334155; }}
.mini-chart canvas {{ max-height:220px !important; }}
.keywords-panel {{ margin-bottom:16px; }}
.keywords-panel h4 {{ margin-bottom:8px; }}
.keywords {{ display:flex; flex-wrap:wrap; gap:8px; }}
.keyword {{ background:#ede9fe; color:#5b21b6; padding:4px 12px; border-radius:16px; }}
.top5-panel {{ margin-bottom:8px; }}
.top5-table {{ width:100%; border-collapse:collapse; }}
.top5-table th, .top5-table td {{ padding:8px 12px; text-align:left; border-bottom:1px solid #e2e8f0; }}
.top5-table th {{ background:#f8fafc; font-size:13px; color:#64748b; }}

/* generic panel styles */
.panel {{ background:#fff; border-radius:16px; padding:24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,.1); }}
.panel h2 {{ margin-bottom:16px; font-size:20px; }}
.panel-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}

/* funnel */
.funnel {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
.funnel-step {{ display:flex; align-items:center; justify-content:center; padding:12px; border-radius:8px; color:#fff; font-weight:600; text-align:center; transition:width .3s; }}
.funnel-arrow {{ color:#94a3b8; font-size:20px; }}

/* milestones */
.milestones {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }}
.milestone-item {{ padding:8px 16px; background:#fff; border-radius:8px; border-left:4px solid; font-size:13px; box-shadow:0 1px 2px rgba(0,0,0,.05); }}

/* chart containers */
.chart-container {{ position:relative; height:300px; }}

/* customer pool overview bar */
.pool-bar {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:12px; }}
.pool-item {{ background:#fff; border-radius:12px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
.pool-num {{ font-size:26px; font-weight:800; }}
.pool-lbl {{ font-size:12px; color:#64748b; margin-top:4px; }}
.pool-progress {{ position:relative; background:#e2e8f0; border-radius:10px; height:26px; margin-bottom:24px; overflow:hidden; }}
.pool-progress-fill {{ position:absolute; left:0; top:0; height:100%; background:linear-gradient(90deg,#0ea5e9,#6366f1); border-radius:10px; }}
.pool-progress-txt {{ position:absolute; left:12px; top:0; line-height:26px; font-size:12px; color:#0f172a; font-weight:600; }}

/* follow-up stage bars */
.stage-list {{ display:flex; flex-direction:column; gap:12px; padding:8px 0; }}
.stage-row {{ display:flex; align-items:center; gap:10px; }}
.stage-dot {{ width:12px; height:12px; border-radius:50%; flex-shrink:0; }}
.stage-name {{ width:96px; font-size:13px; color:#334155; flex-shrink:0; }}
.stage-bar-wrap {{ flex:1; background:#f1f5f9; border-radius:6px; height:16px; overflow:hidden; }}
.stage-bar {{ height:100%; border-radius:6px; min-width:2px; transition:width .3s; }}
.stage-cnt {{ width:48px; text-align:right; font-size:13px; font-weight:600; color:#475569; flex-shrink:0; }}

/* WhatsApp outreach list */
.wa-panel {{ border:2px solid #22c55e33; }}
.wa-stats {{ display:flex; gap:24px; margin-bottom:16px; flex-wrap:wrap; }}
.wa-stat {{ display:flex; flex-direction:column; }}
.wa-stat-num {{ font-size:26px; font-weight:800; }}
.wa-stat-lbl {{ font-size:12px; color:#64748b; }}
.wa-toolbar {{ display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }}
.wa-btn {{ padding:6px 14px; border:1px solid #cbd5e1; background:#fff; border-radius:8px; font-size:13px; cursor:pointer; color:#334155; transition:all .15s; }}
.wa-btn:hover {{ background:#f1f5f9; }}
.wa-btn.active {{ background:#0ea5e9; color:#fff; border-color:#0ea5e9; }}
.wa-btn.copy {{ background:#22c55e; color:#fff; border-color:#22c55e; margin-left:auto; }}
.wa-btn.copy:hover {{ background:#16a34a; }}
.wa-copy-tip {{ font-size:12px; color:#22c55e; font-weight:600; }}
.wa-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.wa-table th, .wa-table td {{ padding:9px 12px; text-align:left; border-bottom:1px solid #eef2f7; white-space:nowrap; }}
.wa-table th {{ background:#f8fafc; color:#64748b; font-size:12px; }}
.wa-table tr:hover td {{ background:#f8fffb; }}
.wa-num-link {{ color:#0f766e; font-weight:600; text-decoration:none; border-bottom:1px dashed #14b8a6; }}
.wa-num-link:hover {{ color:#0d5c56; border-bottom-style:solid; }}
.wa-row-btn {{ display:inline-block; padding:5px 12px; background:#22c55e; color:#fff !important; border-radius:7px; font-size:12px; font-weight:600; text-decoration:none; white-space:nowrap; }}
.wa-row-btn:hover {{ background:#16a34a; }}
.wa-num {{ font-family:ui-monospace,Menlo,monospace; font-weight:600; color:#0f766e; }}
.wa-badge {{ padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600; white-space:nowrap; }}
.wa-badge.todo {{ background:#fef3c7; color:#92400e; }}
.wa-badge.done {{ background:#d1fae5; color:#065f46; }}
.wa-need {{ background:#e0e7ff; color:#3730a3; padding:1px 8px; border-radius:8px; font-size:12px; }}

@media (max-width:768px) {{
    .panel-grid, .review-charts {{ grid-template-columns:1fr; }}
    .case-grid {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<div class="dashboard">
    <h1>{esc(title)}</h1>
    <p class="subtitle">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} | Sources: customer pool + sent_history + success_cases + followups</p>
    
    {pool_html}
    
    {milestone_html}
    
    <!-- ========== Module A: success case card wall (always on top) ========== -->
    <div class="success-section">
        <h2>🏆 Success case review ({total_cases})</h2>
        <p style="color:#64748b;margin-bottom:16px;font-size:14px">
            ✅ = pain point confirmed by the user | ⏳ = preliminary AI analysis awaiting confirmation<br>
            <strong>Important:</strong> a pain-point analysis is only recorded after the user confirms it. The AI makes preliminary suggestions, never the final call.
        </p>
        {f'<div class="case-grid">{case_cards}</div>' if total_cases > 0 else '<p style="color:#94a3b8;text-align:center;padding:40px">No success cases yet</p>'}
    </div>
    
    <!-- ========== Module B: review summary panel ========== -->
    {review_summary_html}
    
    <!-- ========== Module C: sending funnel ========== -->
    <div class="panel">
        <h2>📊 Sending funnel</h2>
        <div class="funnel">
            <div class="funnel-step" style="width:100%;background:#3b82f6">📤 Sent: {total_sent}</div>
            <div class="funnel-arrow">↓ {delivery_rate}%</div>
            <div class="funnel-step" style="width:{max(30,delivery_rate)}%;background:#10b981">✅ Delivered: {total_delivered}</div>
            <div class="funnel-arrow">↓ {open_rate}%</div>
            <div class="funnel-step" style="width:{max(20,open_rate)}%;background:#8b5cf6">👁 Opened: {total_opened}</div>
            <div class="funnel-arrow">↓ {reply_rate}%</div>
            <div class="funnel-step" style="width:{max(15,reply_rate)}%;background:#f59e0b">💬 Replied: {total_replied}</div>
        </div>
        <div style="margin-top:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;text-align:center">
            <div><div style="font-size:24px;font-weight:700;color:#ef4444">{total_bounced}</div><div style="color:#64748b;font-size:13px">Bounced</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#10b981">{delivery_rate}%</div><div style="color:#64748b;font-size:13px">Delivery rate</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#8b5cf6">{open_rate}%</div><div style="color:#64748b;font-size:13px">Open rate</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#f59e0b">{reply_rate}%</div><div style="color:#64748b;font-size:13px">Reply rate</div></div>
        </div>
    </div>
    
    <!-- ========== Modules: need-tag distribution + follow-up stages ========== -->
    <div class="panel-grid">
        <div class="panel">
            <h2>🏷️ Need-tag distribution <span style="font-size:13px;color:#94a3b8;font-weight:400">(core asset of research-first outreach)</span></h2>
            <div class="chart-container"><canvas id="needChart"></canvas></div>
            <p style="margin-top:8px;font-size:12px;color:#94a3b8">Research every account before deciding its need; never guess from the company name — the fuller the tags, the sharper the hooks.</p>
        </div>
        <div class="panel">
            <h2>⏳ Follow-up stages <span style="font-size:13px;color:#94a3b8;font-weight:400">(5-level cooldown 3/3/10 days → stop → WhatsApp)</span></h2>
            {("<div class='stage-list'>" + "".join(f'<div class=\"stage-row\"><span class=\"stage-dot\" style=\"background:{stage_colors.get(s,chr(35)+chr(57)*6)}\"></span><span class=\"stage-name\">{stage_names.get(s,"stage "+str(s))}</span><span class=\"stage-bar-wrap\"><span class=\"stage-bar\" style=\"width:{round(stage_counter[s]/max(1,sum(stage_counter.values()))*100)}%;background:{stage_colors.get(s,chr(35)+chr(57)*6)}\"></span></span><span class=\"stage-cnt\">{stage_counter[s]}</span></div>' for s in sorted(stage_counter.keys())) + "</div>") if stage_counter else '<p style="color:#94a3b8;text-align:center;padding:40px">No accounts in follow-up</p>'}
            <p style="margin-top:8px;font-size:12px;color:#94a3b8">Three e-mails without a reply → stop e-mail and switch to WhatsApp as a different channel.</p>
        </div>
    </div>

    <!-- ========== Module: WhatsApp outreach list ========== -->
    {wa_section_html}

    <!-- ========== Modules D+E: trend chart + region distribution ========== -->
    <div class="panel-grid">
        <div class="panel">
            <h2>📈 Sending trend</h2>
            <div class="chart-container"><canvas id="trendChart"></canvas></div>
        </div>
        <div class="panel">
            <h2>🌍 Region distribution</h2>
            <div class="chart-container"><canvas id="regionChart"></canvas></div>
        </div>
    </div>
    
    <!-- ========== Module F: generic vs decision-maker delivery rate ========== -->
    <div class="panel">
        <h2>📬 Generic mailbox vs. named decision-maker mailbox · delivery rate</h2>
        <div class="chart-container" style="height:250px"><canvas id="typeChart"></canvas></div>
        <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:center">
            <div style="padding:16px;background:#f0fdf4;border-radius:12px">
                <div style="font-size:14px;color:#64748b">Named decision-maker mailbox</div>
                <div style="font-size:28px;font-weight:700;color:#10b981">{named_delivery}%</div>
                <div style="font-size:12px;color:#94a3b8">sent {named_sent} / bounced {named_bounced}</div>
            </div>
            <div style="padding:16px;background:#fef2f2;border-radius:12px">
                <div style="font-size:14px;color:#64748b">Generic mailbox</div>
                <div style="font-size:28px;font-weight:700;color:#ef4444">{generic_delivery}%</div>
                <div style="font-size:12px;color:#94a3b8">sent {generic_sent} / bounced {generic_bounced}</div>
            </div>
        </div>
    </div>
</div>

<script>
// sending trend chart
new Chart(document.getElementById('trendChart'), {{
    type: 'bar',
    data: {{
        labels: {trend_labels},
        datasets: [
            {{ label:'Sent', data:{trend_sent}, backgroundColor:'rgba(59,130,246,.6)', borderRadius:4 }},
            {{ label:'Bounced', data:{trend_bounced}, backgroundColor:'rgba(239,68,68,.6)', borderRadius:4 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'bottom' }} }}, scales:{{ x:{{ stacked:true }}, y:{{ stacked:true, beginAtZero:true }} }} }}
}});

// region distribution chart
new Chart(document.getElementById('regionChart'), {{
    type: 'bar',
    data: {{
        labels: {region_labels},
        datasets: [
            {{ label:'Sent', data:{region_values}, backgroundColor:'rgba(59,130,246,.6)', borderRadius:4 }},
            {{ label:'Bounced', data:{region_bounced_values}, backgroundColor:'rgba(239,68,68,.6)', borderRadius:4 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{ legend:{{ position:'bottom' }} }}, scales:{{ x:{{ stacked:true, beginAtZero:true }}, y:{{ stacked:true }} }} }}
}});

// delivery rate comparison chart
new Chart(document.getElementById('typeChart'), {{
    type: 'bar',
    data: {{
        labels: ['Named decision-maker mailbox', 'Generic mailbox'],
        datasets: [
            {{ label:'Delivery rate', data:[{named_delivery},{generic_delivery}], backgroundColor:['rgba(16,185,129,.7)','rgba(239,68,68,.7)'], borderRadius:8 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }} }}, scales:{{ y:{{ beginAtZero:true, max:100, ticks:{{ callback:v=>v+'%' }} }} }} }}
}});

// success cases by region pie chart
{f"""
new Chart(document.getElementById('caseRegionChart'), {{
    type: 'doughnut',
    data: {{
        labels: {case_region_labels},
        datasets: [{{ data:{case_region_values}, backgroundColor:['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#84cc16','#ec4899'] }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});

new Chart(document.getElementById('caseHookChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(list(case_hook_counter.keys()))},
        datasets: [{{ data:{json.dumps(list(case_hook_counter.values()))}, backgroundColor:['#6366f1','#14b8a6','#f97316','#e11d48','#8b5cf6','#0ea5e9','#84cc16'] }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});
""" if total_cases > 0 else ""}

// need-tag distribution chart
if (document.getElementById('needChart')) {{
    new Chart(document.getElementById('needChart'), {{
        type: 'bar',
        data: {{
            labels: {need_labels},
            datasets: [{{ label:'Accounts', data:{need_values}, backgroundColor:'rgba(99,102,241,.65)', borderRadius:6 }}]
        }},
        options: {{ responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{ legend:{{ display:false }} }}, scales:{{ x:{{ beginAtZero:true }} }} }}
    }});
}}

// card expand / collapse
function toggleCaseDetail(id) {{
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}

// WhatsApp list filter
function filterWA(mode, btn) {{
    document.querySelectorAll('.wa-btn').forEach(b => {{ if(!b.classList.contains('copy')) b.classList.remove('active'); }});
    if (btn) btn.classList.add('active');
    document.querySelectorAll('#waTable tr[data-wa-sent]').forEach(tr => {{
        const sent = tr.getAttribute('data-wa-sent') === '1';
        let show = true;
        if (mode === 'todo') show = !sent;
        if (mode === 'done') show = sent;
        tr.style.display = show ? '' : 'none';
    }});
}}
// one-click copy of pending WA numbers
function copyWANums() {{
    const ta = document.getElementById('waPendingNums');
    const nums = (ta.value || '').trim();
    const tip = document.getElementById('waCopyTip');
    if (!nums) {{ if(tip) tip.textContent = 'No pending WA numbers'; return; }}
    ta.style.left = '0'; ta.select();
    try {{ document.execCommand('copy'); if(tip) tip.textContent = 'Copied ' + nums.split(' ').filter(Boolean).length + ' numbers ✓'; }}
    catch(e) {{ navigator.clipboard && navigator.clipboard.writeText(nums); if(tip) tip.textContent='Copied ✓'; }}
    ta.style.left = '-9999px';
    setTimeout(()=>{{ if(tip) tip.textContent=''; }}, 2500);
}}
</script>
</body>
</html>'''


def export_wa_targets(data):
    """Extract every customer with a WhatsApp number from data, split into pending / moved, for the WA outreach flow."""
    def _digits(s):
        return "".join(ch for ch in str(s or "") if ch.isdigit() or ch == "+")
    records = data.get("records", [])
    success_cases = data.get("success_cases", [])
    targets = {}
    for r in records:
        wa = _digits(r.get("whatsapp", ""))
        if not wa:
            continue
        is_sent = (r.get("status") == "wa_only") or (r.get("wa_status") == "sent")
        targets[wa] = {
            "whatsapp": wa, "brand": r.get("brand", ""), "contact": r.get("contact", ""),
            "region": r.get("region", ""), "need_tag": r.get("need_tag", ""),
            "email": r.get("email", ""), "email_status": r.get("status", ""), "wa_sent": is_sent,
        }
    for c in success_cases:
        wa = _digits(c.get("whatsapp", ""))
        if wa and wa not in targets:
            targets[wa] = {
                "whatsapp": wa, "brand": c.get("brand", ""), "contact": c.get("contact", ""),
                "region": c.get("region", ""), "need_tag": c.get("need_tag", ""),
                "email": c.get("email", ""), "email_status": "won", "wa_sent": True,
            }
    vals = list(targets.values())
    return {
        "pending": [v for v in vals if not v["wa_sent"]],   # can receive a WA outreach message now
        "done": [v for v in vals if v["wa_sent"]],
        "all": vals,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_dashboard.html')
    title = sys.argv[3] if len(sys.argv) > 3 else "B2B E-mail Outreach Dashboard"
    
    data = load_data(input_file)
    html_content = generate_html(data, title)
    
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write(html_content)
    
    # export the WhatsApp target list (feeds the WA outreach flow directly)
    wa_json = export_wa_targets(data)
    wa_path = os.path.join(os.path.dirname(os.path.abspath(output_file)), 'wa_targets.json')
    with open(wa_path, 'w', encoding="utf-8") as f:
        json.dump(wa_json, f, ensure_ascii=False, indent=2)
    print(f"📱 WhatsApp targets exported: {wa_path} (pending {len(wa_json['pending'])} / moved {len(wa_json['done'])})")
    
    print(f"✅ Dashboard generated: {output_file}")
    print(f"   Records: {len(data.get('records', []))}")
    print(f"   Success cases: {len(data.get('success_cases', []))}")
    confirmed = sum(1 for c in data.get('success_cases', []) if c.get('confirmed'))
    pending = sum(1 for c in data.get('success_cases', []) if not c.get('confirmed'))
    if pending > 0:
        print(f"   ⚠️ {pending} case pain points await user confirmation, {confirmed} confirmed")


if __name__ == '__main__':
    main()
