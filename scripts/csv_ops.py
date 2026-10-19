#!/usr/bin/env python3
"""B2B客户开发 CSV数据层操作脚本（技能版本 v3.1）
用法: python3 scripts/csv_ops.py <command> [args]
Commands:
  check <email>              — 查sent_history+blacklist+wa_contacts,返回该邮箱状态+备注
  add_sent <email> <brand> <subject> <need_tag> [notes]  — 追加发送记录(含需求标签+备注)
  add_blacklist <email> <brand> <reason>           — 追加黑名单
  add_wa <wa_number> <brand> <contact_name> <status> — 追加WA联系人
  add_note <email> <note>    — 给该邮箱最新记录追加备注
  mark_bounced <email>       — 标记退信(sent_history+bounced, blacklist)
  mark_replied <email>       — 标记回复
  mark_wa_only <email> <wa_number> <brand> <contact_name> — 转WA渠道
  cooldown <email>           — 检查冷却期状态
  cross_brand_check <domain> — 检查跨品牌排重(按域名)
  stats                      — 统计数据概览
  add_success <email> <brand> <contact> <order_amount> <success_points> [options] — 添加成功案例(含完整客户档案)
    Options: --region --need_tag --hook_type --language --source_channel --won_channel(email/wa) --company_info --contact_phone --company_address --website --whatsapp --products_info --social_linkedin --social_instagram --notes
  list_success [--region XX] [--need_tag XX] [--channel XX] — 列出成功案例(可按地区/需求标签/渠道筛选)
  review_success             — 输出复盘摘要(提炼成功要点,供启动开发前学习)
  
  # === 备用池管理（v5新增）===
  pipeline_check             — 检查备用池状态（已备/待备数量，是否低于最低阈值）
  add_pipeline <email> <brand> <region> <need_tag> [priority] [notes] — 添加到备用池（已完成背调）
  list_pipeline [--status ready] [--region US] [--min 100] — 列出备用池（可按状态/地区筛选）
  use_pipeline <email>       — 标记备用池条目为已使用（移出备用池）
"""
import csv, os, sys, datetime, re, json
from collections import Counter

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")

# === 冷却期规则（与SKILL.md/csv_guide.md统一）===
# followup_count(已发封数-1) -> 冷却天数
#   第1封后(0): 3天 | 第2封后(1): 3天 | 第3封后(2): 10天
#   第4封(3): 永久停通用邮箱 | 第5封(4+): 永久停发，仅WA/个人邮箱
COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}
MAX_GENERIC_FOLLOWUP = 3   # 第4封起停用通用邮箱
MAX_TOTAL_FOLLOWUP = 4     # 第5封起(followup>=4)永久停发

def _path(name):
    return os.path.join(DATA_DIR, name)

def _read_csv(name):
    p = _path(name)
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def _write_csv(name, fieldnames, rows):
    p = _path(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def _append_csv(name, fieldnames, row):
    p = _path(name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    file_exists = os.path.exists(p) and os.path.getsize(p) > 0
    with open(p, 'a', newline='', encoding='utf-8') as f:
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
    
    # Check wa_contacts — 仅当WA联系人的品牌与本邮箱已发记录的品牌一致时才判定wa_only
    # （wa_contacts无email字段，靠brand关联；避免"任意一条wa_only就误伤全部"的bug）
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
    
    # 5级递进规则（先判最严的>=MAX_TOTAL，再判>=MAX_GENERIC，避免>=5分支不可达）
    if followup >= MAX_TOTAL_FOLLOWUP:      # 已发5封及以上
        result['action'] = 'stop_all'
        result['can_followup'] = False
        result['reason'] = '5+ emails sent, permanent stop — WA/personal inbox only'
    elif followup >= MAX_GENERIC_FOLLOWUP:  # 已发4封
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
        'won_channel': won_channel.strip(),  # 成单渠道：email / wa（空=未标，wa_review 会靠brand关联兜底判定）
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
        print("NO_DATA: 暂无成功案例，无法复盘")
        return
    
    
    total_amount = sum(float(c.get('order_amount','0') or 0) for c in cases)
    
    # 按维度统计
    by_region = Counter(c.get('region','Unknown') for c in cases)
    by_need_tag = Counter(c.get('need_tag','Unknown') for c in cases)
    by_hook_type = Counter(c.get('hook_type','Unknown') for c in cases)
    by_language = Counter(c.get('language','EN') for c in cases)
    by_source_channel = Counter(c.get('source_channel','Unknown') for c in cases)
    
    # 提炼成功要点（词频）
    all_points = ' '.join(c.get('success_points','') for c in cases)
    keywords = ['个性化', '具名', '决策人', '钩子', '跟进', '差异化', '母语', '本地化', '样品', '试用', '演示', '案例', '试点', '认证', '合规', '可持续', '新品']
    keyword_hits = {k: all_points.count(k) for k in keywords if all_points.count(k) > 0}
    
    # 按金额排序Top案例
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
            f"最高效地区: {by_region.most_common(1)[0][0] if by_region else 'N/A'} ({by_region.most_common(1)[0][1] if by_region else 0}单)",
            f"最常见需求类型: {by_need_tag.most_common(1)[0][0] if by_need_tag else 'N/A'}",
            f"最有效钩子类型: {by_hook_type.most_common(1)[0][0] if by_hook_type else 'N/A'}",
            f"最有效获客渠道: {by_source_channel.most_common(1)[0][0] if by_source_channel else 'N/A'} ({by_source_channel.most_common(1)[0][1] if by_source_channel else 0}单)",
            f"母语邮件占比: {by_language.get('EN',0)}/{len(cases)} 用英文，其余用本地语言"
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

# === 备用池管理（v5新增）===
PIPELINE_FIELDS = ['email','brand','region','need_tag','status','priority','research_done','added_date','notes']

def cmd_pipeline_check():
    """Check pipeline status: ready/pending counts, minimum threshold"""
    cases = _read_csv('pipeline.csv')
    ready = [c for c in cases if c.get('status','') == 'ready']
    pending = [c for c in cases if c.get('status','') == 'pending']
    disqualified = [c for c in cases if c.get('status','') == 'disqualified']
    
    MIN_READY = 100  # 7天储备量
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
    
    # 按地区统计
    by_region = Counter(c.get('region','Unknown') for c in ready)
    result['by_region'] = dict(by_region.most_common())
    
    # 按需求标签统计
    by_need_tag = Counter(c.get('need_tag','Unknown') for c in ready)
    result['by_need_tag'] = dict(by_need_tag.most_common())
    
    if shortage > 0:
        result['action_required'] = f"⚠️ 备用池不足！当前{len(ready)}家，最低{MIN_READY}家，需补充{shortage}家"
    else:
        result['action_required'] = f"✅ 备用池充足：{len(ready)}家已备，{len(pending)}家待备"
    
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
