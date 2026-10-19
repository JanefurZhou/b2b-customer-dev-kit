#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wa_review.py — WhatsApp 渠道专属复盘脚本（通用版，行业无关）

【定位】把 WhatsApp 这条开发渠道单独拉出来复盘，回答三个问题：
  1. WA 漏斗跑得怎么样？（触达 → 回复 → 成单，各级转化率）
  2. WA 成单都长什么样？（地区/需求标签/钩子/材质分布，最有效的开场词）
  3. WA 和邮件比，哪条渠道更值得加码？（--compare-email）

【铁律遵守】
  - 只读，绝不改任何客户数据（14 数据铁律）。本脚本不写 success_cases.csv / wa_contacts.csv / wa_progress.json。
  - 只出建议（actionable_insights），最终由你拍板（元需求2）。信号不足会明说 NEED_MORE_DATA。

【WA 成单如何识别】双通道并用：
  A2（首选，精确）：success_cases.csv 里 won_channel == 'wa' 的行。
  A1（兜底，关联）：success_cases.csv 里 brand 出现在 wa_contacts.csv 中（且该 WA 联系人 status 含 'wa'），
                    但该行 won_channel 为空时，视为「疑似 WA 成单」并单列出来提示你补 won_channel。

【数据来源】统一走 B2B_DATA_DIR（默认 ./data）：
  - success_cases.csv   成功案例（含 won_channel / whatsapp / hook_type / need_tag / region ...）
  - wa_contacts.csv     WA 联系人（wa_number/brand/contact_name/source_date/status）
  - wa_progress.json    群发进度（total/sent/skipped/last_index；sent 可为字符串或含 phone/brand 的字典）

【用法】
  python3 scripts/wa_review.py review                     # WA 成单复盘（JSON 到 stdout）
  python3 scripts/wa_review.py review --html out.html     # 额外产出可视化 HTML 报告
  python3 scripts/wa_review.py review --compare-email     # 追加「邮件 vs WA」对比板块
  python3 scripts/wa_review.py funnel                     # 只看 WA 漏斗（触达→回复→成单）
  python3 scripts/wa_review.py funnel --html funnel.html
"""

import os
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
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


# ---------- 只读 IO ----------
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


# ---------- 成单渠道识别 ----------
def _wa_brands(wa_contacts):
    """返回 {规范化brand: status原文}，仅收 status 含 'wa' 的联系人（wa_only / wa 等）。"""
    brands = {}
    for r in wa_contacts:
        st = _norm(r.get('status'))
        b = _norm(r.get('brand'))
        if not b:
            continue
        # status 含 wa 视为 WA 渠道联系人；空 status 也保留（曾进过 WA 名单）
        if 'wa' in st or st == '':
            brands[b] = r.get('status', '')
    return brands


def classify_cases(cases, wa_contacts):
    """把成功案例分成：确定WA成单 / 疑似WA成单 / 邮件或其他成单。"""
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
            # 无 won_channel 但品牌在 WA 名单里 → 疑似（A1 兜底）
            suspect_wa.append(c)
        else:
            other.append(c)
    return confirmed_wa, suspect_wa, other, wa_brand_map


# ---------- 词频：WA 开场词 ----------
HOOK_KEYWORDS = ['个性化', '具名', '决策人', '钩子', '跟进', '差异化', '母语',
                 '本地化', '样品', '试用', '演示', 'demo', '案例', '试点', '工艺', '认证', '合规',
                 '可持续', '新品', '语音', '目录', 'MOQ', '报价', '视频', '图片']


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


# ---------- 漏斗 ----------
def build_funnel(wa_contacts, wa_progress, confirmed_wa, suspect_wa):
    """WA 漏斗：触达（群发 sent）→ 回复（wa_contacts status=replied）→ 成单（confirmed+suspect）。"""
    # 触达数：优先 wa_progress 的 sent；否则用 wa_contacts 里状态 >= sent 的数量
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
        'note': '触达数据来自 wa_progress.json（群发进度）；若为空则回退到 wa_contacts.csv 状态统计。回复率依赖 wa_contacts.csv 的 status 是否回写 replied。'
    }


# ---------- review 主逻辑 ----------
def cmd_review(args):
    cases = _read_csv('success_cases.csv')
    wa_contacts = _read_csv('wa_contacts.csv')
    wa_progress = _read_json('wa_progress.json')

    if not cases:
        out = {'status': 'NO_DATA', 'message': '暂无成功案例（success_cases.csv 为空），无法复盘 WA 渠道。'}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    confirmed, suspect, other, wa_brand_map = classify_cases(cases, wa_contacts)
    wa_rows = confirmed + suspect  # 复盘口径：确定 + 疑似 一起看规律

    if not wa_rows:
        out = {
            'status': 'NEED_MORE_DATA',
            'message': '未识别到任何 WA 成单。请在成交时用 csv_ops.py add_success 带上 --won_channel wa，'
                       '或确认成交品牌是否已进 wa_contacts.csv。',
            'hint': '当前成功案例总数=%d，其中 won_channel=email/其他=%d。' % (len(cases), len(other))
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
        print('\n✅ HTML 报告已生成: %s' % args.html, file=sys.stderr)


def _insights(wa_rows, funnel, confirmed, suspect):
    ins = []
    by_region = Counter(r.get('region') or 'Unknown' for r in wa_rows)
    by_need = Counter(r.get('need_tag') or 'Unknown' for r in wa_rows)
    by_hook = Counter(r.get('hook_type') or 'Unknown' for r in wa_rows)
    if by_region:
        ins.append('WA 最出单地区: %s（%d 单）— 建议 WA 名单向该地区加权。'
                   % by_region.most_common(1)[0])
    if by_need:
        ins.append('WA 最常成交的需求类型: %s — WA 开发信钩子优先命中它。'
                   % by_need.most_common(1)[0][0])
    if by_hook:
        ins.append('WA 最有效钩子: %s — 群发模板 {intro} 后优先用这个钩子。'
                   % by_hook.most_common(1)[0][0])
    if funnel.get('reply_rate_pct') is not None:
        ins.append('WA 回复率 %.1f%%；若明显高于邮件回复率，说明 WA 值得作为「邮件未回」的转化主渠道。'
                   % funnel['reply_rate_pct'])
    else:
        ins.append('WA 回复率暂无法计算：请在 wa_contacts.csv 里把回复的联系人 status 回写为 replied（闭环所需）。')
    if suspect:
        ins.append('有 %d 个疑似 WA 成单缺 won_channel 标记 — 建议补 --won_channel wa，复盘口径才准。'
                   % len(suspect))
    ins.append('【拍板提示】以上均为建议，最终 WA 加码/收缩由你决定。')
    return ins


def _compare_email(wa_rows, email_rows):
    def block(rows, label):
        if not rows:
            return {'label': label, 'cases': 0, 'note': '无数据'}
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
    em_b = block(email_rows, 'Email/其他')
    verdict = []
    if wa_b.get('avg_amount_usd') and em_b.get('avg_amount_usd'):
        if wa_b['avg_amount_usd'] > em_b['avg_amount_usd']:
            verdict.append('WA 单均金额更高 → WA 客户质量偏高，值得加码。')
        else:
            verdict.append('邮件单均金额更高 → WA 更适合走量/铺面，大单仍靠邮件精耕。')
    verdict.append('【拍板提示】渠道预算分配由你定，脚本只给对比事实。')
    return {'whatsapp': wa_b, 'email_other': em_b, 'verdict': verdict}


# ---------- funnel 子命令 ----------
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
        print('\n✅ HTML 漏斗图已生成: %s' % args.html, file=sys.stderr)


# ---------- HTML 渲染 ----------
def _esc(s):
    return _html.escape(str(s))


def _bars(d, title):
    if not d:
        return '<p class="muted">（暂无数据）</p>'
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
        return ('<div class="step"><span class="box">%s：%s</span>'
                '<span class="rate">%s</span></div>' % (_esc(label), _esc(val), _esc(rate_label)))
    rr = '' if f.get('reply_rate_pct') is None else '回复率 %s%%' % f['reply_rate_pct']
    wr = '' if f.get('won_rate_of_reached_pct') is None else '触达成单率 %s%%' % f['won_rate_of_reached_pct']
    return ('<div class="funnel">%s%s%s<div class="warn">%s</div></div>' % (
        step('触达', f.get('reached', 0)),
        step('回复', f.get('replied', 0), rr),
        step('成单(含疑似)', f.get('won_incl_suspect', 0), wr),
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
            return ('<div class="card"><div class="l">%s</div><div class="n">%s单</div>'
                    '<div class="l">单均 $%s · 主钩子 %s</div></div>' % (
                        _esc(b['label']), _esc(b.get('cases', 0)),
                        _esc(b.get('avg_amount_usd', '-')), _esc(b.get('top_hook', '-'))))
        cmp_html = ('<h2>邮件 vs WhatsApp 对比</h2><div class="cards">%s%s</div>'
                    '<ul class="ins">%s</ul>' % (
                        cb(ce['whatsapp']), cb(ce['email_other']),
                        ''.join('<li>%s</li>' % _esc(v) for v in ce.get('verdict', []))))
    doc = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>WhatsApp 渠道复盘</title>
<style>%s</style></head><body><div class="wrap">
<h1>📱 WhatsApp 渠道复盘报告</h1>
<div class="sub">生成时间 %s · 仅读不改 · 结论仅供参考，最终你拍板</div>
<div class="cards">
<div class="card"><div class="n">%s</div><div class="l">WA 成单数(含疑似)</div></div>
<div class="card"><div class="n">$%s</div><div class="l">WA 成单总额</div></div>
<div class="card"><div class="n">$%s</div><div class="l">WA 单均金额</div></div>
<div class="card"><div class="n">%s / %s</div><div class="l">确定 / 疑似</div></div>
</div>
<h2>WA 漏斗</h2>%s
<h2>WA 成单地区分布</h2>%s
<h2>WA 成单需求类型分布</h2>%s
<h2>WA 最有效钩子类型</h2>%s
<h2>WA 最佳开场词（词频）</h2>%s
<h2>Top WA 成单案例</h2>
<table><tr><th>客户</th><th>地区</th><th>需求</th><th>钩子</th><th>金额</th></tr>%s</table>
%s
<h2>可行动洞察（建议）</h2><ul class="ins">%s</ul>
</div></body></html>""" % (
        HTML_CSS, _esc(r.get('generated_at', '')),
        _esc(s['wa_cases_total']), _esc(s['total_amount_usd']), _esc(s['avg_amount_usd']),
        _esc(s['confirmed_wa']), _esc(s['suspect_wa']),
        _funnel_html_block(r['funnel']),
        _bars(r.get('by_region', {}), '地区'),
        _bars(r.get('by_need_tag', {}), '需求'),
        _bars(r.get('by_hook_type', {}), '钩子'),
        _bars(r.get('best_opening_keywords', {}), '开场词'),
        top_rows or '<tr><td colspan="5" class="muted">暂无</td></tr>',
        cmp_html, ins)
    with open(path, 'w', encoding="utf-8") as f:
        f.write(doc)


def _write_html_funnel(f, path):
    doc = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>WhatsApp 漏斗</title>
<style>%s</style></head><body><div class="wrap">
<h1>📱 WhatsApp 开发漏斗</h1>
<div class="sub">仅读不改 · 触达 → 回复 → 成单</div>
%s</div></body></html>""" % (HTML_CSS, _funnel_html_block(f))
    with open(path, 'w', encoding="utf-8") as f2:
        f2.write(doc)


# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(
        description='WhatsApp 渠道专属复盘（只读，不改客户数据）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = p.add_subparsers(dest='cmd')

    pr = sub.add_parser('review', help='WA 成单复盘（JSON，可选 --html / --compare-email）')
    pr.add_argument('--html', metavar='FILE', help='额外输出 HTML 报告到指定文件')
    pr.add_argument('--compare-email', action='store_true', dest='compare_email',
                    help='追加「邮件 vs WA」对比板块')
    pr.set_defaults(func=cmd_review)

    pf = sub.add_parser('funnel', help='只看 WA 漏斗（触达→回复→成单）')
    pf.add_argument('--html', metavar='FILE', help='输出 HTML 漏斗图')
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
