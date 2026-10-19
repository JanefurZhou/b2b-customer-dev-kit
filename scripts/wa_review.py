#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wa_review.py — WhatsApp channel review script (generic edition, industry-agnostic)

[Purpose] Review the WhatsApp outreach channel on its own and answer three questions:
  1. How is the WA funnel performing? (reached → replied → won, conversion at each level)
  2. What do WA wins look like? (region / need tag / hook / variant split, the most effective opening words)
  3. WA vs e-mail: which channel deserves more investment? (--compare-email)

[Iron rules]
  - Read-only; never changes customer data (data rule 14). This script does not write success_cases.csv / wa_contacts.csv / wa_progress.json.
  - Suggestions only (actionable_insights); you make the final call. With too little signal it says NEED_MORE_DATA.

[How WA wins are identified] two channels combined:
  A2 (preferred, exact): rows in success_cases.csv with won_channel == 'wa'.
  A1 (fallback, by association): rows in success_cases.csv whose brand appears in wa_contacts.csv (and that WA contact's status contains 'wa'),
                    but won_channel is empty → treated as a "suspected WA win" and listed separately so you can fill won_channel.

[Data sources] all under B2B_DATA_DIR (default ./data):
  - success_cases.csv   success cases (won_channel / whatsapp / hook_type / need_tag / region ...)
  - wa_contacts.csv     WA contacts (wa_number/brand/contact_name/source_date/status)
  - wa_progress.json    bulk-send progress (total/sent/skipped/last_index; sent may be a string or a dict with phone/brand)

[Usage]
  python3 scripts/wa_review.py review                     # WA win review (JSON to stdout)
  python3 scripts/wa_review.py review --html out.html     # also produce a visual HTML report
  python3 scripts/wa_review.py review --compare-email     # add the "e-mail vs WA" comparison section
  python3 scripts/wa_review.py funnel                     # WA funnel only (reached → replied → won)
  python3 scripts/wa_review.py funnel --html funnel.html
"""

import os
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import csv
import json
import argparse
import html as _html
from collections import Counter
from datetime import datetime

DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")


# ---------- read-only IO ----------
def _path(name):
    return os.path.join(DATA_DIR, name)


def _read_csv(name):
    p = _path(name)
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _read_json(name):
    p = _path(name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, 'r', encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _f(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _norm(s):
    return (s or '').strip().lower()


# ---------- won-channel identification ----------
def _wa_brands(wa_contacts):
    """Return {normalised brand: raw status}, only contacts whose status contains 'wa' (wa_only / wa etc.)."""
    brands = {}
    for r in wa_contacts:
        st = _norm(r.get('status'))
        b = _norm(r.get('brand'))
        if not b:
            continue
        # status containing wa = WA-channel contact; empty status is kept too (was once on the WA list)
        if 'wa' in st or st == '':
            brands[b] = r.get('status', '')
    return brands


def classify_cases(cases, wa_contacts):
    """Split success cases into: confirmed WA wins / suspected WA wins / e-mail or other wins."""
    wa_brand_map = _wa_brands(wa_contacts)
    confirmed_wa, suspect_wa, other = [], [], []
    for c in cases:
        wc = _norm(c.get('won_channel'))
        brand = _norm(c.get('brand'))
        if wc == 'wa':
            confirmed_wa.append(c)
        elif wc in ('email', 'mail', 'e-mail'):
            other.append(c)
        elif wc == '' and brand in wa_brand_map:
            # no won_channel but the brand is on the WA list → suspected (A1 fallback)
            suspect_wa.append(c)
        else:
            other.append(c)
    return confirmed_wa, suspect_wa, other, wa_brand_map


# ---------- keyword frequency: WA opening words ----------
HOOK_KEYWORDS = ['personalised', 'named', 'decision maker', 'hook', 'follow-up', 'differentiator', 'native language',
                 'localised', 'sample', 'trial', 'demo', 'case study', 'pilot', 'process', 'certification', 'compliance',
                 'sustainable', 'new range', 'voice note', 'catalogue', 'MOQ', 'quote', 'video', 'photo']


def _keyword_hits(rows, field):
    blob = ' '.join(r.get(field, '') for r in rows)
    return {k: blob.count(k) for k in HOOK_KEYWORDS if blob.count(k) > 0}


def _dim(rows, field, default='Unknown'):
    return dict(Counter(r.get(field) or default for r in rows).most_common())


def _top_cases(rows, n=5):
    ordered = sorted(rows, key=lambda c: _f(c.get('order_amount')), reverse=True)[:n]
    return [{
        'brand': c.get('brand', ''),
        'contact': c.get('contact', ''),
        'region': c.get('region', ''),
        'need_tag': c.get('need_tag', ''),
        'amount': c.get('order_amount', ''),
        'hook_type': c.get('hook_type', ''),
        'whatsapp': c.get('whatsapp', ''),
        'success_points': c.get('success_points', ''),
    } for c in ordered]


# ---------- funnel ----------
def build_funnel(wa_contacts, wa_progress, confirmed_wa, suspect_wa):
    """WA funnel: reached (bulk sent) → replied (wa_contacts status=replied) → won (confirmed+suspect)."""
    # reached: prefer sent from wa_progress; otherwise count wa_contacts with status >= sent
    reached = None
    if wa_progress and isinstance(wa_progress.get('sent'), list):
        reached = len(wa_progress['sent'])
    elif wa_progress and isinstance(wa_progress.get('sent'), int):
        reached = wa_progress['sent']
    if reached is None:
        reached = sum(1 for r in wa_contacts if _norm(r.get('status')) in ('sent', 'replied', 'wa_only', 'wa'))

    replied = sum(1 for r in wa_contacts if 'replied' in _norm(r.get('status')) or 'reply' in _norm(r.get('status')))
    won = len(confirmed_wa)
    won_incl_suspect = len(confirmed_wa) + len(suspect_wa)

    def rate(a, b):
        return round(a / b * 100, 1) if b else None

    return {
        'reached': reached,
        'replied': replied,
        'won_confirmed': won,
        'won_incl_suspect': won_incl_suspect,
        'reply_rate_pct': rate(replied, reached),
        'won_rate_of_reached_pct': rate(won, reached),
        'won_rate_of_replied_pct': rate(won, replied),
        'note': 'Reached comes from wa_progress.json (bulk-send progress); if empty it falls back to wa_contacts.csv status counts. Reply rate depends on wa_contacts.csv status being written back as replied.'
    }


# ---------- review main logic ----------
def cmd_review(args):
    cases = _read_csv('success_cases.csv')
    wa_contacts = _read_csv('wa_contacts.csv')
    wa_progress = _read_json('wa_progress.json')

    if not cases:
        out = {'status': 'NO_DATA', 'message': 'No success cases yet (success_cases.csv is empty); the WA channel cannot be reviewed.'}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    confirmed, suspect, other, wa_brand_map = classify_cases(cases, wa_contacts)
    wa_rows = confirmed + suspect  # review scope: confirmed + suspected together, to see patterns

    if not wa_rows:
        out = {
            'status': 'NEED_MORE_DATA',
            'message': 'No WA win identified. Use csv_ops.py add_success with --won_channel wa when a deal closes, '
                       'or check whether the won brand is in wa_contacts.csv.',
            'hint': 'Total success cases=%d, of which won_channel=email/other=%d.' % (len(cases), len(other))
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    total_amount = sum(_f(c.get('order_amount')) for c in wa_rows)
    funnel = build_funnel(wa_contacts, wa_progress, confirmed, suspect)

    result = {
        'status': 'OK',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'channel': 'WhatsApp',
        'summary': {
            'wa_cases_total': len(wa_rows),
            'confirmed_wa': len(confirmed),
            'suspect_wa': len(suspect),
            'total_amount_usd': round(total_amount, 2),
            'avg_amount_usd': round(total_amount / len(wa_rows), 2),
        },
        'funnel': funnel,
        'by_region': _dim(wa_rows, 'region'),
        'by_need_tag': _dim(wa_rows, 'need_tag'),
        'by_hook_type': _dim(wa_rows, 'hook_type'),
        'best_opening_keywords': _keyword_hits(wa_rows, 'success_points'),
        'top_wa_cases': _top_cases(wa_rows, 5),
        'suspect_wa_cases_need_confirm': [
            {'brand': c.get('brand', ''), 'contact': c.get('contact', ''),
             'amount': c.get('order_amount', ''),
             'wa_status_in_contacts': wa_brand_map.get(_norm(c.get('brand')), '')}
            for c in suspect
        ],
        'actionable_insights': _insights(wa_rows, funnel, confirmed, suspect),
    }

    if getattr(args, 'compare_email', False):
        result['compare_email'] = _compare_email(wa_rows, other)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if getattr(args, 'html', None):
        _write_html_review(result, args.html)
        print('\n✅ HTML report generated: %s' % args.html, file=sys.stderr)


def _insights(wa_rows, funnel, confirmed, suspect):
    ins = []
    by_region = Counter(r.get('region') or 'Unknown' for r in wa_rows)
    by_need = Counter(r.get('need_tag') or 'Unknown' for r in wa_rows)
    by_hook = Counter(r.get('hook_type') or 'Unknown' for r in wa_rows)
    if by_region:
        ins.append('Top WA winning region: %s (%d deals) — weight the WA list towards it.'
                   % by_region.most_common(1)[0])
    if by_need:
        ins.append('Most common WA winning need type: %s — aim WA outreach hooks at it first.'
                   % by_need.most_common(1)[0][0])
    if by_hook:
        ins.append('Most effective WA hook: %s — use it first after {intro} in the bulk template.'
                   % by_hook.most_common(1)[0][0])
    if funnel.get('reply_rate_pct') is not None:
        ins.append('WA reply rate %.1f%%; if clearly above the e-mail reply rate, WA deserves to be the main conversion channel for "e-mail unanswered".'
                   % funnel['reply_rate_pct'])
    else:
        ins.append('WA reply rate cannot be computed yet: set status to replied for responding contacts in wa_contacts.csv (needed to close the loop).')
    if suspect:
        ins.append('%d suspected WA wins lack the won_channel mark — add --won_channel wa so the review scope is accurate.'
                   % len(suspect))
    ins.append('[Decision note] Everything above is a suggestion; scaling WA up or down is your call.')
    return ins


def _compare_email(wa_rows, email_rows):
    def block(rows, label):
        if not rows:
            return {'label': label, 'cases': 0, 'note': 'no data'}
        amt = sum(_f(r.get('order_amount')) for r in rows)
        return {
            'label': label,
            'cases': len(rows),
            'total_amount_usd': round(amt, 2),
            'avg_amount_usd': round(amt / len(rows), 2),
            'top_hook': (Counter(r.get('hook_type') or 'Unknown' for r in rows).most_common(1)[0][0]),
            'top_region': (Counter(r.get('region') or 'Unknown' for r in rows).most_common(1)[0][0]),
        }
    wa_b = block(wa_rows, 'WhatsApp')
    em_b = block(email_rows, 'Email/other')
    verdict = []
    if wa_b.get('avg_amount_usd') and em_b.get('avg_amount_usd'):
        if wa_b['avg_amount_usd'] > em_b['avg_amount_usd']:
            verdict.append('WA average deal size is higher → WA customers are higher quality; worth scaling.')
        else:
            verdict.append('E-mail average deal size is higher → WA suits volume/coverage; large deals still rely on e-mail.')
    verdict.append('[Decision note] Channel budget allocation is yours; the script only gives comparison facts.')
    return {'whatsapp': wa_b, 'email_other': em_b, 'verdict': verdict}


# ---------- funnel sub-command ----------
def cmd_funnel(args):
    cases = _read_csv('success_cases.csv')
    wa_contacts = _read_csv('wa_contacts.csv')
    wa_progress = _read_json('wa_progress.json')
    confirmed, suspect, other, _ = classify_cases(cases, wa_contacts)
    funnel = build_funnel(wa_contacts, wa_progress, confirmed, suspect)
    out = {'status': 'OK', 'channel': 'WhatsApp', 'funnel': funnel}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if getattr(args, 'html', None):
        _write_html_funnel(funnel, args.html)
        print('\n✅ HTML funnel chart generated: %s' % args.html, file=sys.stderr)


# ---------- HTML rendering ----------
def _esc(s):
    return _html.escape(str(s))


def _bars(d, title):
    if not d:
        return '<p class="muted">(no data)</p>'
    mx = max(d.values()) or 1
    rows = []
    for k, v in d.items():
        w = int(v / mx * 100)
        rows.append(
            '<div class="bar-row"><span class="bar-label">%s</span>'
            '<span class="bar"><span class="bar-fill" style="width:%d%%"></span></span>'
            '<span class="bar-val">%s</span></div>' % (_esc(k), w, _esc(v)))
    return '<div class="bars">%s</div>' % ''.join(rows)


HTML_CSS = """
body{font-family:'Noto Sans CJK SC','Microsoft YaHei',Arial,sans-serif;margin:0;background:#f5f6f8;color:#1f2937}
.wrap{max-width:900px;margin:0 auto;padding:28px 20px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 10px;color:#25D366;border-left:4px solid #25D366;padding-left:8px}
.sub{color:#6b7280;font-size:12px;margin-bottom:18px}
.cards{display:flex;gap:12px;flex-wrap:wrap}
.card{flex:1;min-width:130px;background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card .n{font-size:24px;font-weight:700;color:#111827}.card .l{font-size:12px;color:#6b7280;margin-top:2px}
.funnel{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.step{display:flex;align-items:center;gap:10px;margin:8px 0}
.step .box{background:#25D366;color:#fff;border-radius:8px;padding:8px 14px;font-weight:600}
.step .rate{color:#6b7280;font-size:12px}
.bars{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.bar-row{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.bar-label{width:150px;text-align:right;color:#374151}
.bar{flex:1;background:#eef0f3;border-radius:6px;height:16px;overflow:hidden}
.bar-fill{display:block;height:100%;background:linear-gradient(90deg,#25D366,#128C7E)}
.bar-val{width:40px;color:#6b7280}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #f0f1f3}th{background:#fafbfc;color:#374151}
ul.ins{background:#fff;border-radius:10px;padding:14px 16px 14px 34px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
ul.ins li{margin:6px 0;font-size:13px}.muted{color:#9ca3af;font-size:12px}
.warn{background:#fff7ed;border:1px solid #fdba74;border-radius:8px;padding:8px 12px;font-size:12px;color:#9a3412;margin-top:8px}
"""


def _funnel_html_block(f):
    def step(label, val, rate_label=''):
        return ('<div class="step"><span class="box">%s: %s</span>'
                '<span class="rate">%s</span></div>' % (_esc(label), _esc(val), _esc(rate_label)))
    rr = '' if f.get('reply_rate_pct') is None else 'reply rate %s%%' % f['reply_rate_pct']
    wr = '' if f.get('won_rate_of_reached_pct') is None else 'won rate of reached %s%%' % f['won_rate_of_reached_pct']
    return ('<div class="funnel">%s%s%s<div class="warn">%s</div></div>' % (
        step('Reached', f.get('reached', 0)),
        step('Replied', f.get('replied', 0), rr),
        step('Won (incl. suspected)', f.get('won_incl_suspect', 0), wr),
        _esc(f.get('note', ''))))


def _write_html_review(r, path):
    s = r['summary']
    top_rows = ''.join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            _esc(c['brand']), _esc(c['region']), _esc(c['need_tag']),
            _esc(c['hook_type']), _esc(c['amount']))
        for c in r.get('top_wa_cases', []))
    ins = ''.join('<li>%s</li>' % _esc(i) for i in r.get('actionable_insights', []))
    cmp_html = ''
    if 'compare_email' in r:
        ce = r['compare_email']
        def cb(b):
            return ('<div class="card"><div class="l">%s</div><div class="n">%s deals</div>'
                    '<div class="l">avg $%s · main hook %s</div></div>' % (
                        _esc(b['label']), _esc(b.get('cases', 0)),
                        _esc(b.get('avg_amount_usd', '-')), _esc(b.get('top_hook', '-'))))
        cmp_html = ('<h2>E-mail vs WhatsApp</h2><div class="cards">%s%s</div>'
                    '<ul class="ins">%s</ul>' % (
                        cb(ce['whatsapp']), cb(ce['email_other']),
                        ''.join('<li>%s</li>' % _esc(v) for v in ce.get('verdict', []))))
    doc = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>WhatsApp channel review</title>
<style>%s</style></head><body><div class="wrap">
<h1>📱 WhatsApp channel review</h1>
<div class="sub">generated %s · read-only · conclusions are suggestions, you decide</div>
<div class="cards">
<div class="card"><div class="n">%s</div><div class="l">WA wins (incl. suspected)</div></div>
<div class="card"><div class="n">$%s</div><div class="l">WA won amount</div></div>
<div class="card"><div class="n">$%s</div><div class="l">WA average deal</div></div>
<div class="card"><div class="n">%s / %s</div><div class="l">confirmed / suspected</div></div>
</div>
<h2>WA funnel</h2>%s
<h2>WA wins by region</h2>%s
<h2>WA wins by need type</h2>%s
<h2>Most effective WA hook types</h2>%s
<h2>Best WA opening words (frequency)</h2>%s
<h2>Top WA wins</h2>
<table><tr><th>Customer</th><th>Region</th><th>Need</th><th>Hook</th><th>Amount</th></tr>%s</table>
%s
<h2>Actionable insights (suggestions)</h2><ul class="ins">%s</ul>
</div></body></html>""" % (
        HTML_CSS, _esc(r.get('generated_at', '')),
        _esc(s['wa_cases_total']), _esc(s['total_amount_usd']), _esc(s['avg_amount_usd']),
        _esc(s['confirmed_wa']), _esc(s['suspect_wa']),
        _funnel_html_block(r['funnel']),
        _bars(r.get('by_region', {}), 'region'),
        _bars(r.get('by_need_tag', {}), 'need'),
        _bars(r.get('by_hook_type', {}), 'hook'),
        _bars(r.get('best_opening_keywords', {}), 'opening word'),
        top_rows or '<tr><td colspan="5" class="muted">none</td></tr>',
        cmp_html, ins)
    with open(path, 'w', encoding="utf-8") as f:
        f.write(doc)


def _write_html_funnel(f, path):
    doc = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>WhatsApp funnel</title>
<style>%s</style></head><body><div class="wrap">
<h1>📱 WhatsApp outreach funnel</h1>
<div class="sub">read-only · reached → replied → won</div>
%s</div></body></html>""" % (HTML_CSS, _funnel_html_block(f))
    with open(path, 'w', encoding="utf-8") as f2:
        f2.write(doc)


# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(
        description='WhatsApp channel review (read-only, never changes customer data)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest='cmd')

    pr = sub.add_parser('review', help='WA win review (JSON; optional --html / --compare-email)')
    pr.add_argument('--html', metavar='FILE', help='Also write an HTML report to this file')
    pr.add_argument('--compare-email', action='store_true', dest='compare_email',
                    help='Add the "e-mail vs WA" comparison section')
    pr.set_defaults(func=cmd_review)

    pf = sub.add_parser('funnel', help='WA funnel only (reached → replied → won)')
    pf.add_argument('--html', metavar='FILE', help='Write an HTML funnel chart')
    pf.set_defaults(func=cmd_funnel)

    return p


def main():
    p = build_parser()
    args = p.parse_args()
    if not getattr(args, 'cmd', None):
        p.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == '__main__':
    main()
