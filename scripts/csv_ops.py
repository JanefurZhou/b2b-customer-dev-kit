#!/usr/bin/env python3
"""B2B customer development — CSV data-layer operations (skill v3.1)
Usage: python3 scripts/csv_ops.py <command> [args]
Commands:
  check <email>              — look up sent_history + blacklist + wa_contacts; return the mailbox status + notes
  add_sent <email> <brand> <subject> <need_tag> [notes]  — append a send record (with need tag + notes)
  add_blacklist <email> <brand> <reason>           — append to the blacklist
  add_wa <wa_number> <brand> <contact_name> <status> — append a WA contact
  add_note <email> <note>    — append a note to the mailbox's latest record
  mark_bounced <email>       — mark bounced (sent_history+bounced, blacklist)
  mark_replied <email>       — mark replied
  mark_wa_only <email> <wa_number> <brand> <contact_name> — hand over to the WA channel
  cooldown <email>           — check cooldown status
  cross_brand_check <domain> — cross-brand de-dup check (by domain)
  stats                      — data overview
  add_success <email> <brand> <contact> <order_amount> <success_points> [options] — add a success case (full customer record)
    Options: --region --need_tag --hook_type --language --source_channel --won_channel(email/wa) --company_info --contact_phone --company_address --website --whatsapp --products_info --social_linkedin --social_instagram --notes
  list_success [--region XX] [--need_tag XX] [--channel XX] — list success cases (filter by region / need tag / channel)
  review_success             — print the review summary (distilled success points, to study before starting outreach)
  
  # === Pipeline (reserve pool) management (added in v5) ===
  pipeline_check             — check the reserve pool (ready / pending counts, below the minimum threshold or not)
  add_pipeline <email> <brand> <region> <need_tag> [priority] [notes] — add to the reserve pool (research done)
  list_pipeline [--status ready] [--region US] [--min 100] — list the reserve pool (filter by status / region)
  use_pipeline <email>       — mark a reserve-pool entry as used (removed from the pool)
"""
import csv, os, sys, datetime, re, json
from collections import Counter
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")

# === Cooldown rules (unified with SKILL.md / csv_guide.md) ===
# followup_count (e-mails sent − 1) -> cooldown days
#   after 1st (0): 3 days | after 2nd (1): 3 days | after 3rd (2): 10 days
#   4th (3): stop generic mailboxes permanently | 5th (4+): stop permanently, WA / personal mailbox only
COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}
MAX_GENERIC_FOLLOWUP = 3   # from the 4th e-mail stop generic mailboxes
MAX_TOTAL_FOLLOWUP = 4     # from the 5th e-mail (followup>=4) stop permanently

def _path(name):
    return os.path.join(DATA_DIR, name)

def _read_csv(name):
    p = _path(name)
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def _write_csv(name, fieldnames, rows):
    p = _path(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', newline='', encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def _append_csv(name, fieldnames, row):
    p = _path(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    file_exists = os.path.exists(p) and os.path.getsize(p) > 0
    with open(p, 'a', newline='', encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerow(row)

SENT_FIELDS = ['email','brand','send_date','subject','need_tag','followup_count','last_followup_date','status','notes']
BL_FIELDS = ['email','brand','reason','date']
WA_FIELDS = ['wa_number','brand','contact_name','source_date','status']

def cmd_check(email):
    """Check email across all CSVs, return status + notes"""
    email = email.lower().strip()
    results = {'email': email, 'sent': [], 'blacklisted': False, 'blacklist_reason': '', 'wa_only': False, 'notes': []}
    
    # Check blacklist
    for r in _read_csv('blacklist.csv'):
        if r.get('email','').lower().strip() == email:
            results['blacklisted'] = True
            results['blacklist_reason'] = r.get('reason','')
            break
    
    # Check sent_history
    for r in _read_csv('sent_history.csv'):
        if r.get('email','').lower().strip() == email:
            results['sent'].append(r)
            if r.get('status','') == 'permanent_stop':
                results['wa_only'] = True
            # Collect non-empty notes
            note = r.get('notes','').strip()
            if note:
                results['notes'].append({'date': r.get('send_date',''), 'note': note})
    
    # Check wa_contacts — only mark wa_only when the WA contact's brand matches the brand in this mailbox's send records
    # (wa_contacts has no email field; linked by brand; avoids the "any wa_only row hits everyone" bug)
    sent_brands = {r.get('brand','').strip().lower() for r in results['sent'] if r.get('brand','').strip()}
    for r in _read_csv('wa_contacts.csv'):
        if r.get('status','') == 'wa_only':
            wa_brand = r.get('brand','').strip().lower()
            if wa_brand and wa_brand in sent_brands:
                results['wa_only'] = True
                break
    
    results['sent_count'] = len(results['sent'])
    results['can_send'] = not results['blacklisted'] and not results['wa_only']
    
    # Cooldown check
    if results['sent']:
        latest = results['sent'][-1]
        followup = int(latest.get('followup_count','0'))
        last_date = latest.get('last_followup_date') or latest.get('send_date','')
        if last_date:
            try:
                last_dt = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                days_since = (datetime.date.today() - last_dt).days
                cooldown_days = COOLDOWN_RULES.get(followup, 999)
                results['cooldown_remaining'] = max(0, cooldown_days - days_since)
                results['in_cooldown'] = days_since < cooldown_days
                if results['cooldown_remaining'] > 0:
                    results['can_send'] = False
            except ValueError:
                pass
    
    print(json.dumps(results, ensure_ascii=False, indent=2))

def cmd_add_sent(email, brand, subject, need_tag, notes=''):
    today = datetime.date.today().isoformat()
    # Find existing records for this email to get followup_count
    existing = [r for r in _read_csv('sent_history.csv') if r.get('email','').lower().strip() == email.lower().strip()]
    followup = len(existing)  # 0-based, this will be the Nth email
    row = {
        'email': email.strip(),
        'brand': brand.strip(),
        'send_date': today,
        'subject': subject.strip(),
        'need_tag': need_tag.strip(),
        'followup_count': str(followup),
        'last_followup_date': today,
        'status': 'sent',
        'notes': notes.strip() if notes else ''
    }
    _append_csv('sent_history.csv', SENT_FIELDS, row)
    print(f"OK: added sent record for {email} (followup #{followup}, need_tag={need_tag})")

def cmd_add_blacklist(email, brand, reason):
    today = datetime.date.today().isoformat()
    row = {'email': email.strip(), 'brand': brand.strip(), 'reason': reason.strip(), 'date': today}
    _append_csv('blacklist.csv', BL_FIELDS, row)
    print(f"OK: added {email} to blacklist ({reason})")

def cmd_add_wa(wa_number, brand, contact_name, status='pending'):
    today = datetime.date.today().isoformat()
    row = {'wa_number': wa_number.strip(), 'brand': brand.strip(), 'contact_name': contact_name.strip(), 'source_date': today, 'status': status}
    _append_csv('wa_contacts.csv', WA_FIELDS, row)
    print(f"OK: added WA contact {wa_number} ({brand})")

def cmd_mark_bounced(email):
    email = email.lower().strip()
    rows = _read_csv('sent_history.csv')
    found = False
    for r in rows:
        if r.get('email','').lower().strip() == email:
            r['status'] = 'bounced'
            found = True
    if found:
        _write_csv('sent_history.csv', SENT_FIELDS, rows)
    # Also add to blacklist
    brand = rows[0].get('brand','') if rows else ''
    cmd_add_blacklist(email, brand, 'bounce')
    print(f"OK: marked {email} as bounced + added to blacklist")

def cmd_mark_replied(email):
    email = email.lower().strip()
    rows = _read_csv('sent_history.csv')
    for r in rows:
        if r.get('email','').lower().strip() == email:
            r['status'] = 'replied'
    _write_csv('sent_history.csv', SENT_FIELDS, rows)
    print(f"OK: marked {email} as replied")

def cmd_mark_wa_only(email, wa_number, brand, contact_name):
    email = email.lower().strip()
    # Mark in sent_history
    rows = _read_csv('sent_history.csv')
    for r in rows:
        if r.get('email','').lower().strip() == email:
            r['status'] = 'permanent_stop'
    _write_csv('sent_history.csv', SENT_FIELDS, rows)
    # Add/update wa_contacts
    cmd_add_wa(wa_number, brand, contact_name, 'wa_only')
    print(f"OK: {email} switched to WA-only channel")

def cmd_cooldown(email):
    email = email.lower().strip()
    rows = [r for r in _read_csv('sent_history.csv') if r.get('email','').lower().strip() == email]
    if not rows:
        print(json.dumps({'email': email, 'sent_count': 0, 'in_cooldown': False, 'can_followup': True}, ensure_ascii=False))
        return
    latest = rows[-1]
    followup = int(latest.get('followup_count','0'))
    last_date = latest.get('last_followup_date') or latest.get('send_date','')
    status = latest.get('status','')
    
    result = {'email': email, 'sent_count': len(rows), 'followup_count': followup, 'status': status}
    
    # 5-level progression (check the strictest >=MAX_TOTAL first, then >=MAX_GENERIC, so the >=5 branch stays reachable)
    if followup >= MAX_TOTAL_FOLLOWUP:      # 5 or more e-mails sent
        result['action'] = 'stop_all'
        result['can_followup'] = False
        result['reason'] = '5+ emails sent, permanent stop — WA/personal inbox only'
    elif followup >= MAX_GENERIC_FOLLOWUP:  # 4 e-mails sent
        result['action'] = 'stop_generic'
        result['can_followup'] = False
        result['reason'] = '4+ emails sent, stop generic inbox — LinkedIn/personal inbox only'
    else:
        try:
            last_dt = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
            days_since = (datetime.date.today() - last_dt).days
            cooldown_needed = COOLDOWN_RULES.get(followup, 999)
            remaining = max(0, cooldown_needed - days_since)
            result['days_since_last'] = days_since
            result['cooldown_needed'] = cooldown_needed
            result['cooldown_remaining'] = remaining
            result['in_cooldown'] = remaining > 0
            result['can_followup'] = remaining == 0
            if remaining > 0:
                result['next_eligible_date'] = (last_dt + datetime.timedelta(days=cooldown_needed)).isoformat()
        except ValueError:
            result['error'] = f'Cannot parse date: {last_date}'
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_cross_brand_check(domain):
    """Check if domain exists in sent_history (for cross-brand dedup)"""
    domain = domain.lower().strip()
    if not domain.startswith('@'):
        domain = '@' + domain
    matches = []
    for r in _read_csv('sent_history.csv'):
        if r.get('email','').lower().strip().endswith(domain):
            matches.append(r)
    result = {'domain': domain, 'found': len(matches) > 0, 'matches': len(matches), 'brands': list(set(r.get('brand','') for r in matches))}
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_add_note(email, note):
    """Add a note to the latest record for this email"""
    email = email.lower().strip()
    rows = _read_csv('sent_history.csv')
    found = False
    for r in reversed(rows):
        if r.get('email','').lower().strip() == email:
            existing_note = r.get('notes','').strip()
            if existing_note:
                r['notes'] = existing_note + '; ' + note.strip()
            else:
                r['notes'] = note.strip()
            found = True
            break
    if found:
        _write_csv('sent_history.csv', SENT_FIELDS, rows)
        print(f"OK: added note to {email}")
    else:
        print(f"WARN: no record found for {email}, note not added")

SUCCESS_FIELDS = ['email','brand','contact','region','need_tag','first_sent_date','reply_date','order_date','order_amount','success_points','email_subject','hook_type','language','source_channel','won_channel','company_info','contact_phone','company_address','website','social_linkedin','social_instagram','social_facebook','social_twitter','whatsapp','products_info','notes']

def cmd_add_success(email, brand, contact, order_amount, success_points, region='', need_tag='', email_subject='', hook_type='', language='EN', source_channel='', won_channel='', company_info='', contact_phone='', company_address='', website='', social_linkedin='', social_instagram='', social_facebook='', social_twitter='', whatsapp='', products_info='', notes=''):
    """Add a success case to success_cases.csv"""
    today = datetime.date.today().isoformat()
    # Try to find original sent record for dates
    sent_records = [r for r in _read_csv('sent_history.csv') if r.get('email','').lower().strip() == email.lower().strip()]
    first_sent = sent_records[0].get('send_date','') if sent_records else today
    reply_date = ''
    for r in sent_records:
        if r.get('status','') == 'replied':
            reply_date = r.get('last_followup_date','') or r.get('send_date','')
            break
    
    row = {
        'email': email.strip(),
        'brand': brand.strip(),
        'contact': contact.strip(),
        'region': region.strip(),
        'need_tag': need_tag.strip(),
        'first_sent_date': first_sent,
        'reply_date': reply_date,
        'order_date': today,
        'order_amount': str(order_amount).strip(),
        'success_points': success_points.strip(),
        'email_subject': email_subject.strip(),
        'hook_type': hook_type.strip(),
        'language': language.strip(),
        'source_channel': source_channel.strip(),
        'won_channel': won_channel.strip(),  # won channel: email / wa (empty = unmarked; wa_review falls back to brand association)
        'company_info': company_info.strip(),
        'contact_phone': contact_phone.strip(),
        'company_address': company_address.strip(),
        'website': website.strip(),
        'social_linkedin': social_linkedin.strip(),
        'social_instagram': social_instagram.strip(),
        'social_facebook': social_facebook.strip(),
        'social_twitter': social_twitter.strip(),
        'whatsapp': whatsapp.strip(),
        'products_info': products_info.strip(),
        'notes': notes.strip()
    }
    _append_csv('success_cases.csv', SUCCESS_FIELDS, row)
    print(f"OK: added success case {brand} ({contact}) - ${order_amount}")

def cmd_list_success(region='', need_tag='', channel=''):
    """List success cases with optional filters"""
    cases = _read_csv('success_cases.csv')
    if region:
        cases = [c for c in cases if c.get('region','').upper() == region.upper()]
    if need_tag:
        cases = [c for c in cases if c.get('need_tag','').lower() == need_tag.lower()]
    if channel:
        cases = [c for c in cases if channel.lower() in c.get('source_channel','').lower()]
    
    result = {
        'total': len(cases),
        'total_amount': sum(float(c.get('order_amount','0') or 0) for c in cases),
        'cases': cases
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_review_success():
    """Generate review summary: extract patterns from success cases"""
    cases = _read_csv('success_cases.csv')
    if not cases:
        print("NO_DATA: no success cases yet; nothing to review")
        return
    
    
    total_amount = sum(float(c.get('order_amount','0') or 0) for c in cases)
    
    # Split by dimension
    by_region = Counter(c.get('region','Unknown') for c in cases)
    by_need_tag = Counter(c.get('need_tag','Unknown') for c in cases)
    by_hook_type = Counter(c.get('hook_type','Unknown') for c in cases)
    by_language = Counter(c.get('language','EN') for c in cases)
    by_source_channel = Counter(c.get('source_channel','Unknown') for c in cases)
    
    # Distil success points (keyword frequency)
    all_points = ' '.join(c.get('success_points','') for c in cases)
    keywords = ['personalised', 'named', 'decision maker', 'hook', 'follow-up', 'differentiator', 'native language', 'localised', 'sample', 'trial', 'demo', 'case study', 'pilot', 'certification', 'compliance', 'sustainable', 'new range']
    keyword_hits = {k: all_points.count(k) for k in keywords if all_points.count(k) > 0}
    
    # Top cases by amount
    top_cases = sorted(cases, key=lambda c: float(c.get('order_amount','0') or 0), reverse=True)[:5]
    
    result = {
        'summary': {
            'total_cases': len(cases),
            'total_amount_usd': total_amount,
            'avg_amount': round(total_amount / len(cases), 2) if cases else 0
        },
        'by_region': dict(by_region.most_common()),
        'by_need_tag': dict(by_need_tag.most_common()),
        'by_hook_type': dict(by_hook_type.most_common()),
        'by_language': dict(by_language.most_common()),
        'by_source_channel': dict(by_source_channel.most_common()),
        'top_success_patterns': keyword_hits,
        'top_cases': [
            {
                'brand': c.get('brand',''),
                'contact': c.get('contact',''),
                'region': c.get('region',''),
                'amount': c.get('order_amount',''),
                'success_points': c.get('success_points',''),
                'hook_type': c.get('hook_type',''),
                'source_channel': c.get('source_channel','')
            } for c in top_cases
        ],
        'actionable_insights': [
            f"Top region: {by_region.most_common(1)[0][0] if by_region else 'N/A'} ({by_region.most_common(1)[0][1] if by_region else 0} deals)",
            f"Most common need type: {by_need_tag.most_common(1)[0][0] if by_need_tag else 'N/A'}",
            f"Most effective hook type: {by_hook_type.most_common(1)[0][0] if by_hook_type else 'N/A'}",
            f"Most effective acquisition channel: {by_source_channel.most_common(1)[0][0] if by_source_channel else 'N/A'} ({by_source_channel.most_common(1)[0][1] if by_source_channel else 0} deals)",
            f"Language split: {by_language.get('EN',0)}/{len(cases)} in English, the rest in the local language"
        ]
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_stats():
    sent = _read_csv('sent_history.csv')
    bl = _read_csv('blacklist.csv')
    wa = _read_csv('wa_contacts.csv')
    sc = _read_csv('success_cases.csv')
    result = {
        'sent_total': len(sent),
        'sent_by_status': {},
        'blacklist_total': len(bl),
        'wa_contacts_total': len(wa),
        'wa_only_count': len([r for r in wa if r.get('status') == 'wa_only']),
        'unique_brands': len(set(r.get('brand','') for r in sent)),
        'unique_emails': len(set(r.get('email','') for r in sent)),
        'success_cases': len(sc),
        'success_total_amount': sum(float(c.get('order_amount','0') or 0) for c in sc),
    }
    for r in sent:
        s = r.get('status','unknown')
        result['sent_by_status'][s] = result['sent_by_status'].get(s, 0) + 1
    print(json.dumps(result, ensure_ascii=False, indent=2))

# === Pipeline (reserve pool) management (added in v5) ===
PIPELINE_FIELDS = ['email','brand','region','need_tag','status','priority','research_done','added_date','notes']

def cmd_pipeline_check():
    """Check pipeline status: ready/pending counts, minimum threshold"""
    cases = _read_csv('pipeline.csv')
    ready = [c for c in cases if c.get('status','') == 'ready']
    pending = [c for c in cases if c.get('status','') == 'pending']
    disqualified = [c for c in cases if c.get('status','') == 'disqualified']
    
    MIN_READY = 100  # 7-day reserve
    shortage = max(0, MIN_READY - len(ready))
    
    result = {
        'pipeline_status': {
            'ready_count': len(ready),
            'pending_count': len(pending),
            'disqualified_count': len(disqualified),
            'total': len(cases)
        },
        'minimum_threshold': MIN_READY,
        'shortage': shortage,
        'need_supplement': shortage > 0,
        'by_region': {},
        'by_need_tag': {}
    }
    
    # By region
    by_region = Counter(c.get('region','Unknown') for c in ready)
    result['by_region'] = dict(by_region.most_common())
    
    # By need tag
    by_need_tag = Counter(c.get('need_tag','Unknown') for c in ready)
    result['by_need_tag'] = dict(by_need_tag.most_common())
    
    if shortage > 0:
        result['action_required'] = f"⚠️ Reserve pool low: {len(ready)} ready, minimum {MIN_READY}, {shortage} more needed"
    else:
        result['action_required'] = f"✅ Reserve pool sufficient: {len(ready)} ready, {len(pending)} pending"
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_add_pipeline(email, brand, region, need_tag, priority='MEDIUM', notes=''):
    """Add a candidate to pipeline (ready status, research done)"""
    today = datetime.date.today().isoformat()
    row = {
        'email': email.strip(),
        'brand': brand.strip(),
        'region': region.strip().upper(),
        'need_tag': need_tag.strip(),
        'status': 'ready',  # ready/pending/disqualified
        'priority': priority.strip().upper(),  # HIGH/MEDIUM/LOW
        'research_done': 'true',
        'added_date': today,
        'notes': notes.strip() if notes else ''
    }
    _append_csv('pipeline.csv', PIPELINE_FIELDS, row)
    print(f"OK: added {brand} ({region}) to pipeline [ready]")

def cmd_list_pipeline(status='', region='', min_count=0):
    """List pipeline entries with optional filters"""
    cases = _read_csv('pipeline.csv')
    if status:
        cases = [c for c in cases if c.get('status','').lower() == status.lower()]
    if region:
        cases = [c for c in cases if c.get('region','').upper() == region.upper()]
    
    result = {
        'total': len(cases),
        'by_status': {},
        'by_region': {},
        'entries': cases[:min_count] if min_count > 0 else cases
    }
    
    by_status = Counter(c.get('status','unknown') for c in cases)
    result['by_status'] = dict(by_status.most_common())
    
    by_region = Counter(c.get('region','Unknown') for c in cases)
    result['by_region'] = dict(by_region.most_common())
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

def cmd_use_pipeline(email):
    """Mark a pipeline entry as used (moved to sent)"""
    email = email.lower().strip()
    rows = _read_csv('pipeline.csv')
    found = False
    for r in rows:
        if r.get('email','').lower().strip() == email:
            r['status'] = 'used'
            found = True
    if found:
        _write_csv('pipeline.csv', PIPELINE_FIELDS, rows)
        print(f"OK: marked {email} as used (removed from pipeline)")
    else:
        print(f"WARN: {email} not found in pipeline")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    dispatch = {
        'check': lambda: cmd_check(args[0]),
        'add_sent': lambda: cmd_add_sent(args[0], args[1], args[2], args[3] if len(args)>3 else 'open', args[4] if len(args)>4 else ''),
        'add_blacklist': lambda: cmd_add_blacklist(args[0], args[1], args[2]),
        'add_wa': lambda: cmd_add_wa(args[0], args[1], args[2], args[3] if len(args)>3 else 'pending'),
        'mark_bounced': lambda: cmd_mark_bounced(args[0]),
        'mark_replied': lambda: cmd_mark_replied(args[0]),
        'mark_wa_only': lambda: cmd_mark_wa_only(args[0], args[1], args[2], args[3] if len(args)>3 else ''),
        'add_note': lambda: cmd_add_note(args[0], args[1]),
        'cooldown': lambda: cmd_cooldown(args[0]),
        'cross_brand_check': lambda: cmd_cross_brand_check(args[0]),
        'stats': lambda: cmd_stats(),
        'add_success': lambda: cmd_add_success(
            args[0], args[1], args[2], args[3], args[4],
            region=next((args[i+1] for i,a in enumerate(args) if a=='--region'), ''),
            need_tag=next((args[i+1] for i,a in enumerate(args) if a=='--need_tag'), ''),
            email_subject=next((args[i+1] for i,a in enumerate(args) if a=='--email_subject'), ''),
            hook_type=next((args[i+1] for i,a in enumerate(args) if a=='--hook_type'), ''),
            language=next((args[i+1] for i,a in enumerate(args) if a=='--language'), 'EN'),
            source_channel=next((args[i+1] for i,a in enumerate(args) if a=='--source_channel'), ''),
            won_channel=next((args[i+1] for i,a in enumerate(args) if a=='--won_channel'), ''),
            company_info=next((args[i+1] for i,a in enumerate(args) if a=='--company_info'), ''),
            contact_phone=next((args[i+1] for i,a in enumerate(args) if a=='--contact_phone'), ''),
            company_address=next((args[i+1] for i,a in enumerate(args) if a=='--company_address'), ''),
            website=next((args[i+1] for i,a in enumerate(args) if a=='--website'), ''),
            social_linkedin=next((args[i+1] for i,a in enumerate(args) if a=='--social_linkedin'), ''),
            social_instagram=next((args[i+1] for i,a in enumerate(args) if a=='--social_instagram'), ''),
            whatsapp=next((args[i+1] for i,a in enumerate(args) if a=='--whatsapp'), ''),
            products_info=next((args[i+1] for i,a in enumerate(args) if a=='--products_info'), ''),
            notes=next((args[i+1] for i,a in enumerate(args) if a=='--notes'), ''),
        ),
        'list_success': lambda: cmd_list_success(
            next((args[i+1] for i,a in enumerate(args) if a=='--region'), ''),
            next((args[i+1] for i,a in enumerate(args) if a=='--need_tag'), ''),
            next((args[i+1] for i,a in enumerate(args) if a=='--channel'), '')
        ),
        'review_success': lambda: cmd_review_success(),
        'pipeline_check': lambda: cmd_pipeline_check(),
        'add_pipeline': lambda: cmd_add_pipeline(args[0], args[1], args[2], args[3], args[4] if len(args)>4 else 'MEDIUM', args[5] if len(args)>5 else ''),
        'list_pipeline': lambda: cmd_list_pipeline(
            next((args[i+1] for i,a in enumerate(args) if a=='--status'), ''),
            next((args[i+1] for i,a in enumerate(args) if a=='--region'), ''),
            int(next((args[i+1] for i,a in enumerate(args) if a=='--min'), '0'))
        ),
        'use_pipeline': lambda: cmd_use_pipeline(args[0]),
    }
    
    if cmd not in dispatch:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
    
    dispatch[cmd]()
