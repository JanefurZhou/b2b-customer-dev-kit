#!/usr/bin/env python3
"""B2B客户开发 邮件追踪看板生成脚本（技能版本 v3.1）
用法: python3 scripts/email_dashboard.py <data.json> [output.html] [title]

输入JSON格式:
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
    {"date": "6/15", "event": "首批发信", "result": "90封送达 / 110退信", "color": "#3b82f6"}
  ],
  "success_cases": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "region": "US",
      "order_amount": 15000,
      "success_points": "1.个性化钩子 2.决策人具名发信",
      "hook_type": "personalized_hook",
      "need_tag": "line_b",
      "language": "EN",
      "confirmed": true,           # true=用户已确认, false=AI初步分析待确认
      "ai_analysis": "可能痛点：现供应商交付不稳定",  # AI初步分析结果
      "first_sent_date": "2026-06-15",
      "reply_date": "2026-06-18",
      "order_date": "2026-07-01"
    }
  ]
}

输出: HTML文件
"""

import json, sys, os, html as html_mod
from datetime import datetime
from collections import Counter
from urllib.parse import quote


# 复购跟进的一句话来自 profile.offer.repeat_hook（行业通用；未填用中性句）
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
    """提取 WhatsApp 号码中的纯数字（wa.me 链接用）。"""
    return "".join(ch for ch in str(num or "") if ch.isdigit())

def wa_link(num, contact="", brand="", stage="first"):
    """统一生成 wa.me 调用链接（带预填话术）。
    stage='first' 首次开发信；stage='repeat' 成交老客户复购跟进。
    卡片墙与触达清单共用此函数，保证调用逻辑连贯一致。"""
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
    """HTML转义"""
    return html_mod.escape(str(text)) if text else ""

def load_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_email_type(email):
    """根据邮箱前缀判断是否为通用邮箱"""
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

def generate_html(data, title="B2B邮件发信追踪看板"):
    records = data.get("records", [])
    milestones = data.get("milestones", [])
    success_cases = data.get("success_cases", [])
    # 新增：客户池/备用池/黑名单/跟进阶段（对应作战地图的数据层与第6步跟进）
    pool = data.get("pool", {})            # {"total_unique": 11148, "pipeline_reserve": 320, "blacklist": 45, "wa_contacts": 12}
    followups = data.get("followups", [])  # [{"stage": 1..5, ...}] 跟进阶段分布，stage=1/2/3表示第几封跟进，4=停，5=转WA
    
    # 补充email_type
    for r in records:
        if not r.get("email_type"):
            r["email_type"] = analyze_email_type(r.get("email", ""))
    
    # ========== 统计数据 ==========
    total_sent = len(records)
    total_bounced = sum(1 for r in records if r.get("status") == "bounced")
    total_delivered = total_sent - total_bounced
    total_opened = sum(1 for r in records if r.get("status") in ("opened", "replied"))
    total_replied = sum(1 for r in records if r.get("status") == "replied")
    delivery_rate = round(total_delivered / total_sent * 100, 1) if total_sent else 0
    open_rate = round(total_opened / total_delivered * 100, 1) if total_delivered else 0
    reply_rate = round(total_replied / total_delivered * 100, 1) if total_delivered else 0
    
    # 按地区统计
    region_counter = Counter(r.get("region", "Unknown") for r in records)
    region_bounced = Counter(r.get("region", "Unknown") for r in records if r.get("status") == "bounced")
    
    # 按日期统计趋势
    date_counter = Counter()
    date_bounced = Counter()
    for r in records:
        d = r.get("sent_date", "")
        if d:
            date_counter[d] += 1
            if r.get("status") == "bounced":
                date_bounced[d] += 1
    
    # 通用vs决策人送达率
    named_sent = sum(1 for r in records if r.get("email_type") == "named")
    named_bounced = sum(1 for r in records if r.get("email_type") == "named" and r.get("status") == "bounced")
    generic_sent = sum(1 for r in records if r.get("email_type") == "generic")
    generic_bounced = sum(1 for r in records if r.get("email_type") == "generic" and r.get("status") == "bounced")
    named_delivery = round((named_sent - named_bounced) / named_sent * 100, 1) if named_sent else 0
    generic_delivery = round((generic_sent - generic_bounced) / generic_sent * 100, 1) if generic_sent else 0
    
    # ========== 新增：need_tag 需求标签分布（核心资产：调研先行的成果）==========
    # need_tag 取值由使用者在 profile.positioning.need_tags 自定义，原样显示；
    # 以下仅为通用保留值与决策驱动标签（solution_tag）的中文名。
    need_tag_labels_map = {
        "multi": "多条线", "unknown": "待调研", "review": "待复核", "open": "开放",
        "compliance": "合规优先", "sustainability": "可持续优先", "quality_upgrade": "品质升级",
        "cost": "成本优先", "speed": "时效优先", "low_commitment": "低门槛试水",
        "innovation": "新品/新方案", "exclusive_custom": "定制/独家", "one_stop": "一站式",
        "dedicated_service": "专属服务", "strategic_scale": "规模/战略",
    }
    need_counter = Counter(r.get("need_tag", "unknown") or "unknown" for r in records)
    need_sorted = sorted(need_counter.keys(), key=lambda x: need_counter[x], reverse=True)
    need_labels = json.dumps([need_tag_labels_map.get(t, t) for t in need_sorted])
    need_values = json.dumps([need_counter[t] for t in need_sorted])
    
    # ========== 新增：跟进阶段分布（第6步：5级冷却期）==========
    stage_names = {1: "第1封跟进", 2: "第2封跟进", 3: "第3封跟进", 4: "已停止", 5: "转WhatsApp"}
    stage_colors = {1: "#3b82f6", 2: "#6366f1", 3: "#8b5cf6", 4: "#94a3b8", 5: "#22c55e"}
    stage_counter = Counter(f.get("stage", 1) for f in followups)
    
    # ========== 新增：WhatsApp 触达清单（邮件→WA 渠道闭环）==========
    # 只要记录/成功案例里带了 whatsapp 号，就能被看板抓出来，供后续 WA 开发信调用
    def _digits(s):
        return "".join(ch for ch in str(s or "") if ch.isdigit() or ch == "+")
    wa_targets = {}   # 以 wa_number 去重
    for r in records:
        wa = _digits(r.get("whatsapp", ""))
        if not wa:
            continue
        # status为wa_only 或 跟进阶段=5 视为已转WA；否则为待发WA
        is_sent_wa = (r.get("status") == "wa_only") or (r.get("wa_status") == "sent")
        wa_targets[wa] = {
            "whatsapp": wa, "brand": r.get("brand", ""), "contact": r.get("contact", ""),
            "region": r.get("region", ""), "need_tag": r.get("need_tag", ""),
            "email": r.get("email", ""), "email_status": r.get("status", ""),
            "wa_sent": is_sent_wa,
        }
    # 成交案例里的 WhatsApp 也纳入（高价值客户，默认待跟进/维护）
    for c in success_cases:
        wa = _digits(c.get("whatsapp", ""))
        if wa and wa not in wa_targets:
            wa_targets[wa] = {
                "whatsapp": wa, "brand": c.get("brand", ""), "contact": c.get("contact", ""),
                "region": c.get("region", ""), "need_tag": c.get("need_tag", ""),
                "email": c.get("email", ""), "email_status": "成交", "wa_sent": True,
            }
    wa_list = list(wa_targets.values())
    wa_pending = [w for w in wa_list if not w["wa_sent"]]   # 可直接发 WA 开发信
    wa_done = [w for w in wa_list if w["wa_sent"]]           # 已转WA / 已沟通
    
    # ========== 成功案例统计 ==========
    total_cases = len(success_cases)
    total_amount = sum(c.get("order_amount", 0) for c in success_cases)
    
    # 已确认 vs 待确认
    confirmed_cases = [c for c in success_cases if c.get("confirmed", False)]
    pending_cases = [c for c in success_cases if not c.get("confirmed", False)]
    
    # 按地区统计成功案例
    case_region_counter = Counter(c.get("region", "Unknown") for c in success_cases)
    # 按need_tag统计
    case_need_counter = Counter(c.get("need_tag", "unknown") for c in success_cases)
    # 按hook_type统计
    case_hook_counter = Counter(c.get("hook_type", "unknown") for c in success_cases)
    
    # 成功要点词频统计
    word_freq = Counter()
    for c in success_cases:
        points = c.get("success_points", "")
        # 简单分词：按空格/标点/数字序号分割
        tokens = points.replace(".", " ").replace(",", " ").replace(";", " ").replace("、", " ").split()
        for t in tokens:
            t = t.strip().strip("0123456789.、。，,")
            if len(t) >= 2:
                word_freq[t] += 1
    top_keywords = word_freq.most_common(10)
    
    # Top5最佳案例（按金额排序）
    top5_cases = sorted(success_cases, key=lambda c: c.get("order_amount", 0), reverse=True)[:5]
    
    # ========== Chart.js 数据准备 ==========
    # 发信趋势
    sorted_dates = sorted(date_counter.keys())
    trend_labels = json.dumps(sorted_dates)
    trend_sent = json.dumps([date_counter[d] for d in sorted_dates])
    trend_bounced = json.dumps([date_bounced.get(d, 0) for d in sorted_dates])
    
    # 地区分布
    regions_sorted = sorted(region_counter.keys(), key=lambda x: region_counter[x], reverse=True)
    region_labels = json.dumps(regions_sorted)
    region_values = json.dumps([region_counter[r] for r in regions_sorted])
    region_bounced_values = json.dumps([region_bounced.get(r, 0) for r in regions_sorted])
    
    # 成功案例地区分布
    case_regions_sorted = sorted(case_region_counter.keys(), key=lambda x: case_region_counter[x], reverse=True)
    case_region_labels = json.dumps(case_regions_sorted)
    case_region_values = json.dumps([case_region_counter[r] for r in case_regions_sorted])
    
    # ========== 生成成功案例卡片HTML ==========
    def case_card_html(case, idx):
        is_confirmed = case.get("confirmed", False)
        status_badge = '<span class="badge confirmed">✅ 已确认</span>' if is_confirmed else '<span class="badge pending">⏳ 待确认</span>'
        # WhatsApp 标记 + 一键调用：成交老客户→复购/新品跟进（stage=repeat）
        wa_num = case.get("whatsapp", "")
        wa_d = wa_digits(wa_num)
        wa_url = wa_link(wa_num, case.get("contact", ""), case.get("brand", ""), stage="repeat")
        wa_badge = (f'<a class="badge wa-has" href="{wa_url}" target="_blank" onclick="event.stopPropagation()" title="点击打开 WhatsApp 跟进：{esc(wa_num)}">📱 WhatsApp</a>'
                    if wa_d else '<span class="badge wa-none">无WhatsApp</span>')
        
        # 痛点显示
        if is_confirmed:
            points_display = esc(case.get("success_points", ""))
        else:
            ai_note = esc(case.get("ai_analysis", "AI初步分析中"))
            user_note = case.get("success_points", "")
            if user_note:
                points_display = f'<span class="ai-hint">⏳ 待用户确认</span><br>AI分析: {ai_note}<br>用户备注: {esc(user_note)}'
            else:
                points_display = f'<span class="ai-hint">⏳ 待用户确认</span><br>AI分析: {ai_note}'
        
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
                <p><strong>联系人:</strong> {esc(case.get('contact', ''))} {esc(case.get('title', ''))}</p>
                <p><strong>邮箱:</strong> {esc(case.get('email', ''))}</p>
                {f"<p><strong>WhatsApp:</strong> <span class='wa-num'>{esc(wa_num)}</span></p><a class='wa-cta' href='{wa_url}' target='_blank' onclick=\"event.stopPropagation()\">📱 打开 WhatsApp 跟进（已预填复购话术）</a>" if wa_d else "<p><strong>WhatsApp:</strong> <span style='color:#94a3b8'>未留 — 建议回访时索取</span></p>"}
                <p><strong>地区:</strong> {esc(case.get('region', ''))}</p>
                <p><strong>需求标签:</strong> {esc(case.get('need_tag', ''))}</p>
                <p><strong>钩子类型:</strong> {esc(case.get('hook_type', ''))}</p>
                <p><strong>语言:</strong> {esc(case.get('language', ''))}</p>
                <p><strong>首次发送:</strong> {esc(case.get('first_sent_date', ''))}</p>
                <p><strong>回复日期:</strong> {esc(case.get('reply_date', ''))}</p>
                <p><strong>下单日期:</strong> {esc(case.get('order_date', ''))}</p>
                <p><strong>成交金额:</strong> ${case.get('order_amount', 0):,.0f}</p>
                <p><strong>确认状态:</strong> {status_badge}</p>
                <p><strong>成功要点:</strong><br>{points_display}</p>
                {"<p class='confirm-notice'>💡 此痛点分析尚未经用户确认，请在复盘时反馈确认</p>" if not is_confirmed else ""}
            </div>
        </div>'''
    
    case_cards = "\n".join(case_card_html(c, i) for i, c in enumerate(success_cases))
    
    # ========== 复盘摘要面板 ==========
    review_summary_html = ""
    if total_cases > 0:
        confirmed_count = len(confirmed_cases)
        pending_count = len(pending_cases)
        
        review_summary_html = f'''
        <div class="review-panel">
            <h3>📊 复盘摘要</h3>
            <div class="review-stats">
                <div class="review-stat">
                    <div class="review-number">{total_cases}</div>
                    <div class="review-label">成功案例总数</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#10b981">{confirmed_count}</div>
                    <div class="review-label">✅ 已确认痛点</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#f59e0b">{pending_count}</div>
                    <div class="review-label">⏳ 待确认痛点</div>
                </div>
                <div class="review-stat">
                    <div class="review-number" style="color:#6366f1">${total_amount:,.0f}</div>
                    <div class="review-label">累计成交金额</div>
                </div>
            </div>
            {f'<div class="pending-notice">⚠️ 有 {pending_count} 个案例的痛点分析待用户确认。请运行复盘流程，AI会列出候选痛点供您选择。</div>' if pending_count > 0 else ''}
            <div class="review-charts">
                <div class="mini-chart">
                    <h4>成交案例·按地区分布</h4>
                    <div style="position:relative;height:220px"><canvas id="caseRegionChart"></canvas></div>
                </div>
                <div class="mini-chart">
                    <h4>成交案例·按钩子类型分布</h4>
                    <div style="position:relative;height:220px"><canvas id="caseHookChart"></canvas></div>
                </div>
            </div>
            <div class="keywords-panel">
                <h4>🔑 成功要点关键词 Top10</h4>
                <div class="keywords">
                    {"".join(f'<span class="keyword" style="font-size:{max(12, min(24, freq*3))}px">{esc(word)}</span>' for word, freq in top_keywords)}
                </div>
            </div>
            <div class="top5-panel">
                <h4>🏆 Top 5 最佳案例</h4>
                <table class="top5-table">
                    <tr><th>#</th><th>客户</th><th>地区</th><th>金额</th><th>钩子类型</th><th>确认状态</th></tr>
                    {"".join(f'<tr><td>{i+1}</td><td>{esc(c.get("brand",""))}</td><td>{esc(c.get("region",""))}</td><td>${c.get("order_amount",0):,.0f}</td><td>{esc(c.get("hook_type",""))}</td><td>{"✅" if c.get("confirmed") else "⏳"}</td></tr>' for i, c in enumerate(top5_cases))}
                </table>
            </div>
        </div>'''
    
    # ========== 新增：WhatsApp 触达清单 HTML ==========
    def wa_row_html(w):
        badge = '<span class="wa-badge done">✅ 已转WA</span>' if w["wa_sent"] else '<span class="wa-badge todo">📩 待发WA</span>'
        need = need_tag_labels_map.get(w.get("need_tag", ""), w.get("need_tag", "") or "—")
        wa_num = w.get("whatsapp", "")
        wa_d = wa_digits(wa_num)
        # 与卡片墙共用同一套调用逻辑：待发=首次开发话术(first)，已转=复购/跟进话术(repeat)
        stage = "repeat" if w["wa_sent"] else "first"
        if wa_d:
            url = wa_link(wa_num, w.get("contact", ""), w.get("brand", ""), stage=stage)
            cta_label = "💬 跟进" if w["wa_sent"] else "📩 发开发信"
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
            <h2>📱 WhatsApp 触达清单 <span style="font-size:13px;color:#94a3b8;font-weight:400">（邮件→WA 渠道闭环，可直接调用发开发信）</span></h2>
            <div class="wa-stats">
                <div class="wa-stat"><span class="wa-stat-num" style="color:#0ea5e9">{len(wa_list)}</span><span class="wa-stat-lbl">有WhatsApp号</span></div>
                <div class="wa-stat"><span class="wa-stat-num" style="color:#f59e0b">{len(wa_pending)}</span><span class="wa-stat-lbl">📩 待发WA开发信</span></div>
                <div class="wa-stat"><span class="wa-stat-num" style="color:#22c55e">{len(wa_done)}</span><span class="wa-stat-lbl">✅ 已转WA/已沟通</span></div>
            </div>
            <div class="wa-toolbar">
                <button class="wa-btn active" onclick="filterWA('all',this)">全部</button>
                <button class="wa-btn" onclick="filterWA('todo',this)">📩 仅待发WA</button>
                <button class="wa-btn" onclick="filterWA('done',this)">✅ 仅已转WA</button>
                <button class="wa-btn copy" onclick="copyWANums()">📋 复制全部待发号码</button>
                <span class="wa-copy-tip" id="waCopyTip"></span>
            </div>
            <div style="overflow-x:auto">
            <table class="wa-table" id="waTable">
                <tr><th>状态</th><th>客户</th><th>联系人</th><th>地区</th><th>需求标签</th><th>WhatsApp</th><th>邮箱</th><th>一键调用</th></tr>
                {wa_rows}
            </table>
            </div>
            <textarea id="waPendingNums" style="position:absolute;left:-9999px">{esc(pending_nums)}</textarea>
            <p style="margin-top:10px;font-size:12px;color:#94a3b8">💡 “待发WA” = 有WhatsApp号但还没用WA触达过的客户。同时导出了 <code>wa_targets.json</code>，可直接喂给 WhatsApp 开发信流程。</p>
        </div>'''

    # ========== 新增：客户池/数据层概览条 ==========
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
                <div class="pool-lbl">客户池总量（唯一）</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#6366f1">{contacted:,}</div>
                <div class="pool-lbl">已触达（覆盖 {coverage}%）</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#f59e0b">{pipeline_reserve:,}</div>
                <div class="pool-lbl">🗂️ 备用池储备</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#22c55e">{wa_cnt:,}</div>
                <div class="pool-lbl">📱 已转WhatsApp</div>
            </div>
            <div class="pool-item">
                <div class="pool-num" style="color:#ef4444">{blacklist_cnt:,}</div>
                <div class="pool-lbl">🚫 黑名单（退信拉黑）</div>
            </div>
        </div>
        <div class="pool-progress">
            <div class="pool-progress-fill" style="width:{min(100,coverage)}%"></div>
            <span class="pool-progress-txt">客户池开发进度 {coverage}%（剩余 {max(0,total_unique-contacted):,} 家待开发）</span>
        </div>'''

    # ========== 里程碑HTML ==========
    milestone_html = ""
    if milestones:
        items = []
        for m in milestones:
            color = m.get("color", "#3b82f6")
            items.append(f'<div class="milestone-item" style="border-left-color:{color}"><strong>{esc(m.get("date",""))}</strong> {esc(m.get("event",""))} — {esc(m.get("result",""))}</div>')
        milestone_html = '<div class="milestones">' + "".join(items) + '</div>'
    
    # ========== 组装完整HTML ==========
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

/* 成功案例卡片墙 - 永远置顶 */
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

/* 复盘摘要面板 */
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

/* 通用面板样式 */
.panel {{ background:#fff; border-radius:16px; padding:24px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,.1); }}
.panel h2 {{ margin-bottom:16px; font-size:20px; }}
.panel-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}

/* 漏斗 */
.funnel {{ display:flex; flex-direction:column; align-items:center; gap:4px; }}
.funnel-step {{ display:flex; align-items:center; justify-content:center; padding:12px; border-radius:8px; color:#fff; font-weight:600; text-align:center; transition:width .3s; }}
.funnel-arrow {{ color:#94a3b8; font-size:20px; }}

/* 里程碑 */
.milestones {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }}
.milestone-item {{ padding:8px 16px; background:#fff; border-radius:8px; border-left:4px solid; font-size:13px; box-shadow:0 1px 2px rgba(0,0,0,.05); }}

/* 图表容器 */
.chart-container {{ position:relative; height:300px; }}

/* 客户池概览条 */
.pool-bar {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:12px; }}
.pool-item {{ background:#fff; border-radius:12px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
.pool-num {{ font-size:26px; font-weight:800; }}
.pool-lbl {{ font-size:12px; color:#64748b; margin-top:4px; }}
.pool-progress {{ position:relative; background:#e2e8f0; border-radius:10px; height:26px; margin-bottom:24px; overflow:hidden; }}
.pool-progress-fill {{ position:absolute; left:0; top:0; height:100%; background:linear-gradient(90deg,#0ea5e9,#6366f1); border-radius:10px; }}
.pool-progress-txt {{ position:absolute; left:12px; top:0; line-height:26px; font-size:12px; color:#0f172a; font-weight:600; }}

/* 跟进阶段条 */
.stage-list {{ display:flex; flex-direction:column; gap:12px; padding:8px 0; }}
.stage-row {{ display:flex; align-items:center; gap:10px; }}
.stage-dot {{ width:12px; height:12px; border-radius:50%; flex-shrink:0; }}
.stage-name {{ width:96px; font-size:13px; color:#334155; flex-shrink:0; }}
.stage-bar-wrap {{ flex:1; background:#f1f5f9; border-radius:6px; height:16px; overflow:hidden; }}
.stage-bar {{ height:100%; border-radius:6px; min-width:2px; transition:width .3s; }}
.stage-cnt {{ width:48px; text-align:right; font-size:13px; font-weight:600; color:#475569; flex-shrink:0; }}

/* WhatsApp 触达清单 */
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
    <p class="subtitle">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")} | 数据来源: 客户池 + sent_history + success_cases + followups</p>
    
    {pool_html}
    
    {milestone_html}
    
    <!-- ========== 模块A: 成功案例卡片墙（永远置顶） ========== -->
    <div class="success-section">
        <h2>🏆 成功案例复盘（{total_cases}个）</h2>
        <p style="color:#64748b;margin-bottom:16px;font-size:14px">
            ✅ = 用户已确认痛点 | ⏳ = AI初步分析，待用户确认<br>
            <strong>重要：</strong>痛点分析必须由用户确认后才正式记录。AI仅做初步分析建议，不做最终判定。
        </p>
        {f'<div class="case-grid">{case_cards}</div>' if total_cases > 0 else '<p style="color:#94a3b8;text-align:center;padding:40px">暂无成功案例</p>'}
    </div>
    
    <!-- ========== 模块B: 复盘摘要面板 ========== -->
    {review_summary_html}
    
    <!-- ========== 模块C: 发信漏斗 ========== -->
    <div class="panel">
        <h2>📊 发信漏斗</h2>
        <div class="funnel">
            <div class="funnel-step" style="width:100%;background:#3b82f6">📤 发送: {total_sent}封</div>
            <div class="funnel-arrow">↓ {delivery_rate}%</div>
            <div class="funnel-step" style="width:{max(30,delivery_rate)}%;background:#10b981">✅ 送达: {total_delivered}封</div>
            <div class="funnel-arrow">↓ {open_rate}%</div>
            <div class="funnel-step" style="width:{max(20,open_rate)}%;background:#8b5cf6">👁 打开: {total_opened}封</div>
            <div class="funnel-arrow">↓ {reply_rate}%</div>
            <div class="funnel-step" style="width:{max(15,reply_rate)}%;background:#f59e0b">💬 回复: {total_replied}封</div>
        </div>
        <div style="margin-top:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;text-align:center">
            <div><div style="font-size:24px;font-weight:700;color:#ef4444">{total_bounced}</div><div style="color:#64748b;font-size:13px">退信</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#10b981">{delivery_rate}%</div><div style="color:#64748b;font-size:13px">送达率</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#8b5cf6">{open_rate}%</div><div style="color:#64748b;font-size:13px">打开率</div></div>
            <div><div style="font-size:24px;font-weight:700;color:#f59e0b">{reply_rate}%</div><div style="color:#64748b;font-size:13px">回复率</div></div>
        </div>
    </div>
    
    <!-- ========== 新增模块: 需求标签分布 + 跟进阶段 ========== -->
    <div class="panel-grid">
        <div class="panel">
            <h2>🏷️ 需求标签分布 <span style="font-size:13px;color:#94a3b8;font-weight:400">（调研先行的核心资产）</span></h2>
            <div class="chart-container"><canvas id="needChart"></canvas></div>
            <p style="margin-top:8px;font-size:12px;color:#94a3b8">每家先背调再定需求，不凭公司名猜测——标签越全，话术钩子越精准。</p>
        </div>
        <div class="panel">
            <h2>⏳ 跟进阶段分布 <span style="font-size:13px;color:#94a3b8;font-weight:400">（5级冷却期 3/3/10天→停→转WA）</span></h2>
            {("<div class='stage-list'>" + "".join(f'<div class=\"stage-row\"><span class=\"stage-dot\" style=\"background:{stage_colors.get(s,chr(35)+chr(57)*6)}\"></span><span class=\"stage-name\">{stage_names.get(s,"阶段"+str(s))}</span><span class=\"stage-bar-wrap\"><span class=\"stage-bar\" style=\"width:{round(stage_counter[s]/max(1,sum(stage_counter.values()))*100)}%;background:{stage_colors.get(s,chr(35)+chr(57)*6)}\"></span></span><span class=\"stage-cnt\">{stage_counter[s]}人</span></div>' for s in sorted(stage_counter.keys())) + "</div>") if stage_counter else '<p style="color:#94a3b8;text-align:center;padding:40px">暂无跟进中的客户</p>'}
            <p style="margin-top:8px;font-size:12px;color:#94a3b8">连续3封无回复→停止邮件，转 WhatsApp 换个渠道触达。</p>
        </div>
    </div>

    <!-- ========== 新增模块: WhatsApp 触达清单 ========== -->
    {wa_section_html}

    <!-- ========== 模块D+E: 趋势图+地区分布 ========== -->
    <div class="panel-grid">
        <div class="panel">
            <h2>📈 发信趋势</h2>
            <div class="chart-container"><canvas id="trendChart"></canvas></div>
        </div>
        <div class="panel">
            <h2>🌍 地区分布</h2>
            <div class="chart-container"><canvas id="regionChart"></canvas></div>
        </div>
    </div>
    
    <!-- ========== 模块F: 通用vs决策人送达率对比 ========== -->
    <div class="panel">
        <h2>📬 通用邮箱 vs 决策人具名邮箱 送达率对比</h2>
        <div class="chart-container" style="height:250px"><canvas id="typeChart"></canvas></div>
        <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:center">
            <div style="padding:16px;background:#f0fdf4;border-radius:12px">
                <div style="font-size:14px;color:#64748b">决策人具名邮箱</div>
                <div style="font-size:28px;font-weight:700;color:#10b981">{named_delivery}%</div>
                <div style="font-size:12px;color:#94a3b8">发送{named_sent}封 / 退信{named_bounced}封</div>
            </div>
            <div style="padding:16px;background:#fef2f2;border-radius:12px">
                <div style="font-size:14px;color:#64748b">通用邮箱</div>
                <div style="font-size:28px;font-weight:700;color:#ef4444">{generic_delivery}%</div>
                <div style="font-size:12px;color:#94a3b8">发送{generic_sent}封 / 退信{generic_bounced}封</div>
            </div>
        </div>
    </div>
</div>

<script>
// 发信趋势图
new Chart(document.getElementById('trendChart'), {{
    type: 'bar',
    data: {{
        labels: {trend_labels},
        datasets: [
            {{ label:'发送', data:{trend_sent}, backgroundColor:'rgba(59,130,246,.6)', borderRadius:4 }},
            {{ label:'退信', data:{trend_bounced}, backgroundColor:'rgba(239,68,68,.6)', borderRadius:4 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'bottom' }} }}, scales:{{ x:{{ stacked:true }}, y:{{ stacked:true, beginAtZero:true }} }} }}
}});

// 地区分布图
new Chart(document.getElementById('regionChart'), {{
    type: 'bar',
    data: {{
        labels: {region_labels},
        datasets: [
            {{ label:'发送', data:{region_values}, backgroundColor:'rgba(59,130,246,.6)', borderRadius:4 }},
            {{ label:'退信', data:{region_bounced_values}, backgroundColor:'rgba(239,68,68,.6)', borderRadius:4 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{ legend:{{ position:'bottom' }} }}, scales:{{ x:{{ stacked:true, beginAtZero:true }}, y:{{ stacked:true }} }} }}
}});

// 送达率对比图
new Chart(document.getElementById('typeChart'), {{
    type: 'bar',
    data: {{
        labels: ['决策人具名邮箱', '通用邮箱'],
        datasets: [
            {{ label:'送达率', data:[{named_delivery},{generic_delivery}], backgroundColor:['rgba(16,185,129,.7)','rgba(239,68,68,.7)'], borderRadius:8 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }} }}, scales:{{ y:{{ beginAtZero:true, max:100, ticks:{{ callback:v=>v+'%' }} }} }} }}
}});

// 成功案例地区分布饼图
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

// 需求标签分布图
if (document.getElementById('needChart')) {{
    new Chart(document.getElementById('needChart'), {{
        type: 'bar',
        data: {{
            labels: {need_labels},
            datasets: [{{ label:'客户数', data:{need_values}, backgroundColor:'rgba(99,102,241,.65)', borderRadius:6 }}]
        }},
        options: {{ responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{ legend:{{ display:false }} }}, scales:{{ x:{{ beginAtZero:true }} }} }}
    }});
}}

// 卡片展开/收起
function toggleCaseDetail(id) {{
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}

// WhatsApp 清单筛选
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
// 一键复制待发WA号码
function copyWANums() {{
    const ta = document.getElementById('waPendingNums');
    const nums = (ta.value || '').trim();
    const tip = document.getElementById('waCopyTip');
    if (!nums) {{ if(tip) tip.textContent = '没有待发WA的号码'; return; }}
    ta.style.left = '0'; ta.select();
    try {{ document.execCommand('copy'); if(tip) tip.textContent = '已复制 ' + nums.split(' ').filter(Boolean).length + ' 个号码✓'; }}
    catch(e) {{ navigator.clipboard && navigator.clipboard.writeText(nums); if(tip) tip.textContent='已复制✓'; }}
    ta.style.left = '-9999px';
    setTimeout(()=>{{ if(tip) tip.textContent=''; }}, 2500);
}}
</script>
</body>
</html>'''


def export_wa_targets(data):
    """从 data 中抽取所有带 WhatsApp 号的客户，分为待发/已转两组，供 WA 开发信流程调用。"""
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
                "email": c.get("email", ""), "email_status": "成交", "wa_sent": True,
            }
    vals = list(targets.values())
    return {
        "pending": [v for v in vals if not v["wa_sent"]],   # 可直接发 WA 开发信
        "done": [v for v in vals if v["wa_sent"]],
        "all": vals,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_dashboard.html')
    title = sys.argv[3] if len(sys.argv) > 3 else "B2B邮件发信追踪看板"
    
    data = load_data(input_file)
    html_content = generate_html(data, title)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 导出 WhatsApp 目标清单（供后续 WA 开发信流程直接调用）
    wa_json = export_wa_targets(data)
    wa_path = os.path.join(os.path.dirname(os.path.abspath(output_file)), 'wa_targets.json')
    with open(wa_path, 'w', encoding='utf-8') as f:
        json.dump(wa_json, f, ensure_ascii=False, indent=2)
    print(f"📱 WhatsApp目标已导出: {wa_path}（待发{len(wa_json['pending'])} / 已转{len(wa_json['done'])}）")
    
    print(f"✅ 看板已生成: {output_file}")
    print(f"   记录数: {len(data.get('records', []))}")
    print(f"   成功案例: {len(data.get('success_cases', []))}")
    confirmed = sum(1 for c in data.get('success_cases', []) if c.get('confirmed'))
    pending = sum(1 for c in data.get('success_cases', []) if not c.get('confirmed'))
    if pending > 0:
        print(f"   ⚠️ {pending}个案例痛点待用户确认，{confirmed}个已确认")


if __name__ == '__main__':
    main()
