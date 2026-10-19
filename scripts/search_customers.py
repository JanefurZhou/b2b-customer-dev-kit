#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_customers.py  —  通用 B2B 客户搜索候选生成器 + 自循环引擎（技能版本 v3.1 · 配置驱动版）

【行业无关】：本脚本不内置任何具体行业的产品词/客户分层/排除词；实体商品、软件、
服务、项目型业务通用。可选的行业包（references/industry_packs.json，经
onboarding.py apply-pack 写入 profile）只提供方法层建议：意图词、站点词、推荐渠道。
全部业务词库在运行时从公司档案 config/company_profile.json 读取：
  - 核心产品词     product.primary_keywords + product.alt_keywords
  - 决策角色词     targeting.buyer_titles
  - 渠道词         targeting.channel_keywords
  - 客户分层       targeting.customer_levels（每层 name/desc/keyword_suffixes）
                   未定义时用 buyer_titles + channel_keywords 组合出一个默认单层
  - 非目标排除词   targeting.exclude_keywords（命中即拦截；为空则不做行业排除）
  - 竞品特征词     targeting.competitor_markers（命中即拦截；为空则不做竞品排除）
  - 目标地区       targeting.target_regions（也可用 --regions 临时覆盖）
  - 侧翼轴词       可选 search.scene_terms / intent_terms / channel_site_terms /
                   niche_terms / cert_terms（不配则意图轴/渠道站轴用行业中性通用词，
                   其余三轴不启用）
未建档/必填项未填齐时，任何业务子命令都会被 config.py 门禁拒绝（exit 2）。

自循环引擎（一年不枯竭 · 全自动触发 · 客户池保底）：
  1) 客户池保底（never dry）：A 级可发候选池 < 红线(默认100) → 自动触发补池 + 预警。
  2) 四维轮换状态机：深度(d1/d2/d3) → 远度(地区由近到远) → 高度(客户层级由高到低) → 广度(core/wide/max) 梯次轮换（state.json 记录进度）。
  3) 内置调度器（daemon）：schedule 常驻模式，每日定点跑
     「检查池→不足则补池→轮换搜索→回池」全闭环。

  breadth 三档：
  - core = {地区}×{核心产品词}×{分层角色词} 全组合
  - wide = core + 场景轴/意图轴（行业相关轴需在 profile 自行配置）
  - max  = core + 全部 5 个侧翼轴
  搜索只负责扩面找候选；如何打动目标客户由后续背调诊断决定。

命令：
  A. 只生成搜索词：  python3 search_customers.py queries [--out queries.txt]
  B. 渠道发现式：    python3 search_customers.py channels [--ch social maps ...] [--out ch.txt]
  C. 过滤+分级：     python3 search_customers.py filter results.json \
                        --against 全量客户数据库.csv [--since 2026-04-01] [--out candidates.csv]
  D. 检查保底并补池：python3 search_customers.py replenish --pool 客户管家库.csv
  E. 常驻调度器：    python3 search_customers.py schedule --pool 客户管家库.csv
  F. 看轮换进度：    python3 search_customers.py status
  G. 非目标复核：    python3 search_customers.py audit-exclude candidates.csv
                     （audit-category 为向后兼容别名）
  I. 10 平台社媒公开搜索：python3 search_customers.py social [--platforms linkedin instagram ...]
                        [--tier decision|execution|influence|all] [--regions UK,DE] [--out social.txt]
                     （只生成 Google/Bing 可用的 site: 公开搜索式；不登录、不注册、不私信；
                       --titles 只打印 30 个采购链职位词库）
  H. 标签冲突校正：  python3 search_customers.py conflict-check --against 客户管家库.csv \
                        [--new new.json] [--since 2026-04-01] [--out conflicts.csv]
                     （背调新结论 vs 库内旧标签，只标不改，交人工拍板）

results.json 期望结构：
  [{"url": "...", "title": "...", "snippet": "...", "emails": ["..."]}, ...]
（emails 可缺省，缺省时按启发式从文本提取）
"""

import sys
import os
import re
import json
import csv
import argparse
from urllib.parse import urlparse

# ============================================================
# 零、统一配置门禁（与所有业务脚本共用 config.py）
# ============================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import config as _cfg
except ImportError:
    _cfg = None

# 运行时业务上下文：main() 过门禁后从 company_profile.json 填充。
# 引擎函数只读本字典，模块内不保留任何具体行业词表。
RUNTIME = {
    "categories": [],        # 核心产品词（primary + alt）
    "spectrum": {},          # 客户分层 {层级名: [角色/渠道词]}
    "regions": [],           # 目标地区
    "exclude_keywords": [],  # 非目标排除词
    "competitor_markers": [],# 同行/竞品特征词（命中即拦截）
    "competitors": [],       # 参照/竞品品牌名（供"竞品逆向"渠道展开，不用于拦截）
    "axes": {                # 侧翼搜索轴（scene/niche/cert 默认空，由 profile 提供）
        "scene": [], "intent": [], "channel": [], "niche": [], "cert": [],
    },
    "default_level": False,  # profile 未定义 customer_levels 时的兜底单层标记
}

# ============================================================
# 一、侧翼轴：行业中性的通用意图词 / 渠道站点词
# ============================================================
# 这两组词不绑定任何行业，描述的是「买家正在找供应商」这一通用采购意图，
# 以及「在哪些站点找人」这一通用渠道。场景/人群/认证三轴与具体行业强相关，
# 不在此内置，需要时在 profile 的 search.*_terms 自行配置。
GENERIC_INTENT_TERMS = [
    # 行业中性的「正在找供应方」信号；实体商品/软件/服务/项目通用。
    # 行业专属意图词（如 low MOQ / free trial / tender）由行业包或 profile.search.intent_terms 提供。
    "looking for supplier", "looking for vendor", "new vendor", "vendor application",
    "request for proposal", "request for quotation", "seeking partner", "partner program",
    "alternative to", "switching provider",
]
GENERIC_CHANNEL_SITES = [
    "site:linkedin.com", "site:instagram.com",
    "site:facebook.com", "site:pinterest.com",
]
EMPTY_AXES = {
    "scene": [], "intent": list(GENERIC_INTENT_TERMS),
    "channel": list(GENERIC_CHANNEL_SITES), "niche": [], "cert": [],
}


def build_profile_context(profile):
    """从公司档案构造运行时词表上下文（业务数据的唯一来源）。"""
    def _dedup(seq):
        seen, out = set(), []
        for x in seq:
            x = str(x).strip()
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    # ① 核心词：
    #   offer 锚点   = primary_keywords + alt_keywords（客户的网页上会出现你的品类词：实体商品/工业品/项目型）
    #   customer 锚点 = targeting.customer_industries（客户按"他自己的行业"被找到：软件/服务常见，
    #                   比如卖 HR 软件要找"logistics company"，而不是搜"HR software"——那会搜到同行）
    offer_terms = _dedup(
        list(_cfg.get(profile, "product.primary_keywords", []) or [])
        + list(_cfg.get(profile, "product.alt_keywords", []) or [])
    )
    customer_inds = _dedup(_cfg.get(profile, "targeting.customer_industries", []) or [])
    offer_type = (_cfg.get(profile, "business.offer_type", "") or "other").strip()
    anchor = (_cfg.get(profile, "search.query_anchor", "") or "auto").strip().lower()
    if anchor not in ("offer", "customer"):
        anchor = "customer" if (offer_type in ("software", "service") and customer_inds) else "offer"
    if anchor == "customer" and not customer_inds:
        anchor = "offer"
    categories = customer_inds if anchor == "customer" else offer_terms

    # ② 客户分层 = customer_levels[].keyword_suffixes；未定义则角色词+渠道词兜底单层
    titles = list(_cfg.get(profile, "targeting.buyer_titles", []) or [])
    channels_kw = list(_cfg.get(profile, "targeting.channel_keywords", []) or [])
    levels = _cfg.get(profile, "targeting.customer_levels", []) or []
    spectrum = {}
    for lv in levels:
        if not isinstance(lv, dict):
            continue
        name = str(lv.get("name") or "").strip()
        if not name:
            continue
        suffixes = _dedup(lv.get("keyword_suffixes") or [])
        if suffixes:
            spectrum[name] = suffixes
    default_level = False
    if not spectrum:
        fallback = _dedup(titles + channels_kw) or ["buyer"]
        spectrum = {"L1_default": fallback}
        default_level = True

    # ③ 非目标排除词 + 竞品特征词（用户填什么排什么；为空不做行业过滤）
    exclude_keywords = _dedup(_cfg.get(profile, "targeting.exclude_keywords", []) or [])
    competitor_markers = _dedup(_cfg.get(profile, "targeting.competitor_markers", []) or [])

    # ④ 目标地区
    regions = _dedup(_cfg.get(profile, "targeting.target_regions", []) or [])

    # ⑤ 侧翼轴：profile > 行业包 > 行业中性通用词
    pack = _cfg.active_pack(profile) or {}
    axes = {
        "scene": _dedup(_cfg.get(profile, "search.scene_terms", []) or []),
        "intent": (_dedup(_cfg.get(profile, "search.intent_terms", []) or [])
                   or _dedup(pack.get("intent_terms") or [])
                   or list(GENERIC_INTENT_TERMS)),
        "channel": (_dedup(_cfg.get(profile, "search.channel_site_terms", []) or [])
                    or _dedup(pack.get("channel_site_terms") or [])
                    or list(GENERIC_CHANNEL_SITES)),
        "niche": _dedup(_cfg.get(profile, "search.niche_terms", []) or []),
        "cert": _dedup(_cfg.get(profile, "search.cert_terms", []) or []),
    }

    return {
        "categories": categories,
        "offer_terms": offer_terms,
        "anchor": anchor,
        "spectrum": spectrum,
        "regions": regions,
        "exclude_keywords": exclude_keywords,
        "competitor_markers": competitor_markers,
        "competitors": _dedup(_cfg.get(profile, "targeting.reference_brands", []) or []),
        "axes": axes,
        "default_level": default_level,
        "offer_type": offer_type,
        "default_channels": _dedup(_cfg.get(profile, "search.channels", []) or [])
                            or _dedup(pack.get("recommended_channels") or []),
        "positioning": _cfg.get(profile, "positioning", {}) or {},
        "buyer_titles": titles,
        "social_platforms": _dedup(_cfg.get(profile, "search.social_platforms", []) or []),
    }


# ============================================================
# 一·三、渠道配方库（新发现源 · 不止 Google/LinkedIn）
# ============================================================
# 模板占位符：{region}=地区  {cat}=核心产品/服务词  {role}=分层角色/客户类型词
# src  = "offer" 时 {cat} 用你的品类词（招标/招聘/评测/海关等描述"你卖的东西"）；
#        缺省用当前锚点词（customer 锚点下 = 客户所在行业）。
# fits = 适用的交付形态（business.offer_type）。未在 profile.search.channels / 行业包里
# 指定渠道时，channels 子命令按 offer_type 自动挑选 fits 命中的渠道；"all" 表示通用。
ALL = "all"
PHYS = ("physical_product",)
CHANNEL_RECIPES = {
    "social": {
        "name": "社媒/职业网络发现（10 平台免登录公开搜索，完整版用 social 子命令）", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "按关键词/地区找目标公司与决策人主页 → 官网 → 具名邮箱",
        "tmpl": [
            'site:linkedin.com/company {cat} {role} {region}',
            'site:linkedin.com/in {role} {cat} {region}',
            'site:instagram.com {cat} {role} {region}',
            'site:facebook.com {cat} {role} {region}',
        ],
    },
    "maps": {
        "name": "Google Maps / 本地商家目录", "star": "⭐⭐⭐⭐",
        "fits": ("physical_product", "service", "project"),
        "use": "按城市+客户类型找有实体地址的公司（门店/展厅/工程商/诊所/仓库），拿官网与电话",
        "tmpl": [
            '{role} {region} - Google Maps',
            '{cat} {role} {region} - Google Maps',
        ],
    },
    "customs": {
        "name": "海关/进出口贸易数据", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "service"),
        "use": "用产品词/HS 编码反查真实进口商（免注册路径优先：ImportYeti 基础搜索 / site:importyeti.com；付费平台可选）；操作见 references/海关数据操作指引.md",
        "tmpl": [
            '{cat} importer {region} customs data',
            '{cat} import records {region}',
            'who imports {cat} in {region}',
            'site:importyeti.com "{cat}"',
        ],
    },
    "rfq": {
        "name": "B2B 采购平台买家端 / RFQ", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "project"),
        "use": "不看卖家看买家：从询价/RFQ/采购需求页反找正在找供应方的活跃买家",
        "tmpl": [
            '{cat} RFQ buyer {region}',
            '{cat} sourcing request {region}',
            'looking for {cat} supplier {region}',
        ],
    },
    "tender": {
        "name": "公开招标/政府与机构采购", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ALL,
        "use": "招标=明确预算+明确需求；在各国公共采购门户（如 TED、SAM.gov、本地政府采购网）按关键词检索",
        "tmpl": [
            '{cat} tender {region}',
            '{cat} request for proposal {region}',
            '{cat} procurement notice {region}',
        ],
    },
    "hiring": {
        "name": "招聘信号（岗位=预算+痛点）", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ALL,
        "use": "在招与你解决的问题相关的岗位 → 说明在投入这件事；适合软件、服务、设备与耗材",
        "tmpl": [
            '{cat} job {region} site:linkedin.com/jobs',
            'hiring {cat} specialist {region}',
            '{cat} manager job opening {region}',
        ],
    },
    "directory": {
        "name": "行业目录/协会会员名录", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "行业协会、商会、行业目录（Kompass、Thomasnet、Europages、Clutch 等）集中列出同类公司",
        "tmpl": [
            '{cat} {role} directory {region}',
            '{cat} association members {region}',
            '{role} association {region}',
        ],
    },
    "review": {
        "name": "评测/比价站点（软件与服务）", "star": "⭐⭐⭐⭐", "src": "offer", "fits": ("software", "service"),
        "use": "G2/Capterra/Clutch 等评测页能看到谁在用竞品、谁在比较方案",
        "tmpl": [
            '{cat} reviews site:g2.com',
            '{cat} alternatives {region}',
            '{cat} agencies {region} site:clutch.co',
        ],
    },
    "partners": {
        "name": "合作伙伴/集成生态", "star": "⭐⭐⭐", "src": "offer", "fits": ("software", "service", "project"),
        "use": "生态市场、实施伙伴、经销伙伴页面 → 找可转介或联合交付的伙伴",
        "tmpl": [
            '{cat} implementation partner {region}',
            '{cat} reseller program {region}',
            '{cat} integration partners',
        ],
    },
    "events": {
        "name": "行业会议/峰会（赞助商·演讲人·参会者）", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "会议官网的 sponsors / speakers / exhibitors 页是高质量决策人名单",
        "tmpl": [
            '{cat} conference {region} speakers',
            '{cat} summit {region} sponsors',
        ],
    },
    "media": {
        "name": "行业媒体/榜单/融资与扩张新闻", "star": "⭐⭐⭐", "fits": ALL,
        "use": "新开店/新项目/融资/进入新市场=采购窗口期",
        "tmpl": [
            '{cat} {role} expansion {region}',
            '{role} raised funding {region}',
            'top {cat} {role} {region}',
        ],
    },
    "exhibition": {
        "name": "展会名录（参展商/买家名录）", "star": "⭐⭐⭐⭐⭐", "src": "offer", "fits": ("physical_product", "project"),
        "use": "锁定本行业目标市场展会，从 exhibitor list / buyer directory 批量找集中、对口的客户",
        "tmpl": [
            '{cat} trade fair exhibitor list {region}',
            '{cat} trade show exhibitors {region}',
            '{cat} expo buyer directory {region}',
        ],
    },
    "competitor": {
        "name": "竞品逆向（竞品的客户/经销商网络）", "star": "⭐⭐⭐⭐", "fits": ALL,
        "use": "以建档填写的竞品/参照品牌为起点，找它们的经销商、案例客户、集成伙伴",
        "tmpl": [
            '"{competitor}" distributors {region}',
            '"{competitor}" customers case study {region}',
            '"{competitor}" partner {region}',
        ],
        "needs_competitor": True,
    },
    "ecommerce": {
        "name": "电商独立站卖家（Shopify/DTC）", "star": "⭐⭐⭐⭐", "src": "offer", "fits": PHYS,
        "use": "找自建站卖同类/相邻产品的品牌（非平台卖家），从 about/contact/LinkedIn 挖采购联系人",
        "tmpl": [
            '{cat} brand shopify {region}',
            '{cat} "powered by shopify" {region}',
            '{cat} online store brand {region} -amazon -ebay -etsy',
        ],
    },
    "gift": {
        "name": "礼品/企业礼赠渠道（可选，需手动指定）", "star": "⭐⭐⭐", "src": "offer", "fits": PHYS,
        "opt_in": True,
        "use": "仅当产品具备礼品属性时启用：礼品店、企业礼赠公司、文创店",
        "tmpl": [
            'gift shop {cat} supplier {region}',
            'corporate gifts {cat} {region}',
        ],
    },
}


def default_channels():
    """profile.search.channels > 行业包 recommended_channels > 按 offer_type 匹配 fits。"""
    chosen = [c for c in (RUNTIME.get("default_channels") or []) if c in CHANNEL_RECIPES]
    if chosen:
        return chosen
    ot = RUNTIME.get("offer_type") or "other"
    return [k for k, r in CHANNEL_RECIPES.items()
            if not r.get("opt_in")
            and (r.get("fits") == ALL or ot in (r.get("fits") or ()) or ot == "other")]


def _top_roles(limit=6):
    """从各分层词表里取头部角色词，供渠道模板 {role} 使用（避免组合爆炸）。"""
    out = []
    for words in RUNTIME["spectrum"].values():
        for w in words:
            if w not in out:
                out.append(w)
    return out[:limit]


def build_channel_queries(channels=None, regions=None, cats=None, roles=None):
    """按渠道生成发现式。channels=None 则全渠道；cats=None 用头部核心产品词。"""
    chans = channels or default_channels()
    regs = regions or RUNTIME["regions"]
    all_cats = RUNTIME["categories"]
    offer_cats = RUNTIME.get("offer_terms") or all_cats
    top_roles = roles or _top_roles()
    out = []
    # 竞品逆向渠道需要用户在档案里给出参照品牌/竞品名；没给则无法生成
    competitors = list(RUNTIME.get("competitors") or [])
    for ch in chans:
        recipe = CHANNEL_RECIPES.get(ch)
        if not recipe:
            continue
        if recipe.get("needs_competitor") and not competitors:
            print(f"# 跳过渠道 [{ch}] {recipe['name']}：未配置参照/竞品品牌 "
                  f"（请在 company_profile 的 targeting.reference_brands 填写）",
                  file=__import__("sys").stderr)
            continue
        pool = offer_cats if recipe.get("src") == "offer" else all_cats
        use_cats = cats or pool[:8]
        for tmpl in recipe["tmpl"]:
            for region in regs:
                # 竞品逆向：以每个参照品牌为起点展开，不依赖产品词笛卡尔积
                if "{competitor}" in tmpl:
                    for comp in competitors[:6]:
                        out.append(tmpl.format(region=region, cat="", role="", competitor=comp))
                    continue
                for cat in use_cats:
                    if "{role}" in tmpl:
                        for role in top_roles:
                            out.append(tmpl.format(region=region, cat=cat, role=role))
                    else:
                        out.append(tmpl.format(region=region, cat=cat, role=""))
    seen, uniq = set(), []
    for q in out:
        q = " ".join(q.split())
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


# ============================================================
# 四、行业无关的技术性过滤规则（不针对任何具体行业）
# ============================================================
# 4.1 平台 / B2B 集市（非终端客户站点，排除）
PLATFORM_BLOCKLIST = [
    "alibaba.", "aliexpress.", "made-in-china.", "1688.", "globalsources.",
    "dhgate.", "amazon.", "ebay.", "wish.", "temu.", "shein.",
    "indiamart.", "tradeindia.", "ec21.", "tradekey.", "go4worldbusiness.",
    "etsy.com",
]
# 4.2 目录页 / 博客 / 媒体 / 无效页 URL 特征（排除）
#     注意：directory/tender/review/events 渠道搜到的名录页、招标页、评测页是「线索来源页」，
#     不是客户官网——要先人工/AI 从页面里取出公司名再反查官网，所以这里照常排除，不入候选池。
NONLEAD_URL_PATTERNS = [
    "/blog/", "/news/", "/press/", "/article/", "/wiki/", "wikipedia.org",
    "/category/", "/tag/", "pinterest.", "youtube.", "reddit.",
    "/directory/", "yellowpages.", "yelp.",
]
# 4.3 通用邮箱前缀（→ B 级入库，不再直接丢弃）
GENERIC_EMAIL_PREFIXES = set(_cfg.GENERIC_MAILBOX_PREFIXES) if _cfg is not None else {
    "info", "contact", "sales", "hello", "support", "office",
}
# 4.4 免费个人邮箱域（非企业邮箱 → 不作 A 级具名邮箱）
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "msn.com", "icloud.com", "me.com", "mail.com", "gmx.com",
    "proton.me", "protonmail.com",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


# ============================================================
# 五、生成搜索词（全组合，不截断）
# ============================================================
def build_queries(spectrum_keys=None, regions=None, breadth="core"):
    """生成搜索词全集（核心全组合 + 侧翼轴限定采样）。

    breadth:
        core = {地区}×{核心产品词}×{分层角色词}       全组合
        wide = core + 场景轴(scene)+意图轴(intent)    仅启用 profile 已配置/有通用词的轴
        max  = core + 全部 5 个侧翼轴                 空轴自动跳过
    """
    spectrum = RUNTIME["spectrum"]
    all_categories = RUNTIME["categories"]
    axes = RUNTIME["axes"]
    keys = spectrum_keys or list(spectrum.keys())
    regs = regions or RUNTIME["regions"]
    queries = []

    # ① 核心全组合：{地区} × {核心产品词} × {分层角色词}
    for region in regs:
        for cat in all_categories:
            for key in keys:
                for role in spectrum.get(key, []):
                    queries.append(f"{region} {cat} {role}")

    # ② 侧翼轴挂载（限定采样，不与核心全组合叠乘，避免爆炸）
    if breadth in ("wide", "max"):
        rep_cats = all_categories[:8] if len(all_categories) >= 8 else all_categories
        offer_terms = RUNTIME.get("offer_terms") or all_categories
        rep_offer = offer_terms[:8]
        if breadth == "wide":
            active_axes = [a for a in ("scene", "intent") if axes.get(a)]
        else:
            active_axes = [a for a in ("scene", "intent", "channel", "niche", "cert")
                           if axes.get(a)]
        for region in regs:
            for axis_name in active_axes:
                for term in axes[axis_name]:
                    if axis_name == "channel":
                        for cat in rep_cats:
                            queries.append(f"{term} {cat} {region}")
                    else:
                        # 意图轴描述的是"在找你这类东西"，永远配你的品类词
                        use = rep_offer if axis_name == "intent" else rep_cats
                        for cat in use:
                            queries.append(f"{region} {term} {cat}")

    # 去重保序
    seen, uniq = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


# ============================================================
# 六、结果过滤 + 全量域名去重 + 分级入库
# ============================================================
def domain_of(url):
    try:
        net = urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return ""


def is_platform(url):
    u = url.lower()
    return any(p in u for p in PLATFORM_BLOCKLIST)


def is_nonlead(url):
    u = url.lower()
    if any(p in u for p in NONLEAD_URL_PATTERNS):
        return True
    host = domain_of(url)
    return (host.startswith(("blog.", "news.", "wiki.", "press."))
            or host.endswith((".gov", ".mil")))


def is_non_target(rec):
    """非目标品类拦截：标题/正文命中 profile 的 targeting.exclude_keywords。
    用户未配置排除词时不做任何行业排除（仅保留技术性过滤）。"""
    keywords = RUNTIME["exclude_keywords"]
    if not keywords:
        return False
    blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('text','')}".lower()
    return any(str(k).lower() in blob for k in keywords)


def is_competitor(rec):
    """同行/竞品拦截：命中 profile 的 targeting.competitor_markers；
    或记录显式标记 is_competitor=True（旧字段 has_own_factory 兼容；仅在用户配置了竞品特征词时启用）。
    用户未配置竞品特征词时不做竞品排除。"""
    markers = RUNTIME["competitor_markers"]
    if not markers:
        return False
    blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('url','')}".lower()
    if rec.get("is_competitor") is True or rec.get("has_own_factory") is True:
        return True
    return any(str(k).lower() in blob for k in markers)


def extract_emails(rec):
    """从记录里取邮箱：优先显式 emails 字段，否则从 snippet/title 正则提取。"""
    emails = list(rec.get("emails") or [])
    if not emails:
        blob = f"{rec.get('title','')} {rec.get('snippet','')} {rec.get('text','')}"
        emails = EMAIL_RE.findall(blob)
    clean = []
    for e in emails:
        e = e.strip().lower()
        if e and not e.endswith((".png", ".jpg", ".gif")) and e not in clean:
            clean.append(e)
    return clean


def grade_email(emails):
    """分级：A=有企业具名邮箱直发；B=只有通用/免费个人邮箱，需找决策人；none=无邮箱。"""
    if not emails:
        return "none", ""
    named = []
    for e in emails:
        local = e.split("@")[0].split("+")[0]
        dom = e.split("@")[1] if "@" in e else ""
        if local not in GENERIC_EMAIL_PREFIXES and dom not in FREE_EMAIL_DOMAINS:
            named.append(e)
    if named:
        return "A", named[0]
    return "B", emails[0]


# ============================================================
# 六·一  客户管家库增量去重
# ============================================================
def domain_from_website(website):
    """从 website 字段取域名（兼容无 http 前缀 / 带 www）。"""
    if not website:
        return ""
    w = website.strip().lower()
    if "://" not in w:
        w = "http://" + w
    return domain_of(w)


def load_customer_db(csv_path, since=None):
    """加载客户管家库，建 email / 域名 / customer_code 三套索引。"""
    emails, domains, codes = set(), set(), set()
    loaded = 0
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if since:
                ts = (row.get("added_date") or row.get("created_at")
                      or row.get("updated_at") or "")[:10]
                if ts and ts < since:
                    continue
            loaded += 1
            em = (row.get("email") or "").strip().lower()
            if em:
                emails.add(em)
            dom = domain_from_website(row.get("website") or "")
            if dom:
                domains.add(dom)
            code = (row.get("customer_code") or "").strip()
            if code:
                codes.add(code)
    return emails, domains, codes, loaded


def in_customer_db(rec, dom, emails_set, domains_set, codes_set):
    """按 email → website域名 → customer_code 优先级判断是否已在库中。"""
    for e in extract_emails(rec):
        if e in emails_set:
            return True
    if dom and dom in domains_set:
        return True
    code = (rec.get("customer_code") or "").strip()
    if code and code in codes_set:
        return True
    return False


def filter_and_grade(results, db_index=None):
    """核心：库增量去重 + 全量域名去重 + 平台/目录/政府媒体技术过滤
    + 非目标词/竞品特征过滤（均由 profile 驱动）+ 分级。"""
    stats = {
        "input": len(results), "platform_skip": 0, "nonlead_skip": 0,
        "nontarget_skip": 0, "competitor_skip": 0,
        "dup_domain_skip": 0, "dup_in_db_skip": 0,
        "A": 0, "B": 0, "no_email": 0, "candidates": 0,
    }
    emails_set, domains_set, codes_set = db_index or (set(), set(), set())
    seen_domains = set()
    candidates = []
    for rec in results:
        url = rec.get("url", "")
        if not url:
            continue
        if is_platform(url):
            stats["platform_skip"] += 1
            continue
        if is_nonlead(url):
            stats["nonlead_skip"] += 1
            continue
        dom = domain_of(url)
        if not dom:
            continue
        if dom in seen_domains:
            stats["dup_domain_skip"] += 1
            continue
        seen_domains.add(dom)
        if db_index and in_customer_db(rec, dom, emails_set, domains_set, codes_set):
            stats["dup_in_db_skip"] += 1
            continue
        if is_non_target(rec):
            stats["nontarget_skip"] += 1
            continue
        if is_competitor(rec):
            stats["competitor_skip"] += 1
            continue

        emails = extract_emails(rec)
        grade, best = grade_email(emails)
        if grade == "A":
            stats["A"] += 1
        elif grade == "B":
            stats["B"] += 1
        else:
            stats["no_email"] += 1

        candidates.append({
            "domain": dom,
            "url": url,
            "brand": rec.get("title", "").strip()[:120],
            "email_grade": grade,
            "best_email": best,
            "all_emails": ";".join(emails),
            "region_hint": rec.get("region_hint", ""),
            "customer_type_hint": rec.get("customer_type_hint", ""),
            "next_action": {
                "A": "直发（有企业具名邮箱）",
                "B": "入库+LinkedIn找决策人/email_guesser补齐具名邮箱",
                "none": "入库+官网/LinkedIn补邮箱",
            }[grade],
            "note": "B级=仅通用/免费个人邮箱(info@/gmail.com 等)" if grade == "B" else "",
        })
    stats["candidates"] = len(candidates)
    return candidates, stats


# ============================================================
# 六之二、搜索漏斗诊断
# ============================================================
FUNNEL_DUP_DB_RED = 0.40      # 库内重复率 >40% → 标红
FUNNEL_NAMED_EMAIL_RED = 0.20 # 具名邮箱率 <20% → 标红


def build_funnel(stats):
    """把 filter 的 stats 转成漏斗诊断。"""
    total = max(stats["input"], 1)
    after_platform = stats["input"] - stats["platform_skip"] - stats["nonlead_skip"]
    after_dupdom = after_platform - stats["dup_domain_skip"]
    after_db = after_dupdom - stats["dup_in_db_skip"]
    after_nt = after_db - stats["nontarget_skip"]
    after_comp = after_nt - stats["competitor_skip"]
    cand = stats["candidates"]
    a = stats["A"]

    def pct(n):
        return f"{n/total*100:.0f}%"

    def step_pct(n, prev):
        return f"{n/max(prev,1)*100:.0f}%"

    rows = [
        ("搜索结果",       stats["input"], "—", "100%"),
        ("去平台/目录",    after_platform, step_pct(after_platform, stats["input"]), pct(after_platform)),
        ("去域名重复",     after_dupdom, step_pct(after_dupdom, after_platform), pct(after_dupdom)),
        ("去库内已有",     after_db, step_pct(after_db, after_dupdom), pct(after_db)),
        ("去非目标词",     after_nt, step_pct(after_nt, after_db), pct(after_nt)),
        ("去竞品特征",     after_comp, step_pct(after_comp, after_nt), pct(after_comp)),
        ("入库候选",       cand, step_pct(cand, after_comp), pct(cand)),
        ("  └ A级可直发",  a, step_pct(a, cand), pct(a)),
    ]

    dup_db_rate = stats["dup_in_db_skip"] / total
    named_rate = a / max(cand, 1)
    ratios = {
        "total": total,
        "in_db_rate": dup_db_rate,
        "candidate_rate": cand / total,
        "named_email_rate": named_rate,
        "sendable_rate": a / total,
    }

    diagnostics = []
    if dup_db_rate > FUNNEL_DUP_DB_RED:
        diagnostics.append(
            f"🔴 库内重复率 {dup_db_rate*100:.0f}% (>{FUNNEL_DUP_DB_RED*100:.0f}%)："
            f"搜索词大量命中已开发客户 → 换未覆盖地区/产品词/层级")
    if named_rate < FUNNEL_NAMED_EMAIL_RED and cand > 0:
        diagnostics.append(
            f"🔴 具名邮箱率仅 {named_rate*100:.0f}% (<{FUNNEL_NAMED_EMAIL_RED*100:.0f}%)："
            f"可直发太少 → B级客户走 email_guesser 补具名邮箱；优质客户勿因只有 info@ 丢弃")
    if stats["platform_skip"] + stats["nonlead_skip"] > total * 0.5:
        diagnostics.append(
            f"🟡 平台/目录占比 {(stats['platform_skip']+stats['nonlead_skip'])/total*100:.0f}%："
            f"搜索词太宽泛 → 收窄关键词、加 -site:平台域 排除")
    if stats["nontarget_skip"] > total * 0.3:
        diagnostics.append(
            f"🟡 非目标命中占比 {stats['nontarget_skip']/total*100:.0f}%："
            f"混入大量非目标结果 → 在 profile 的 targeting.exclude_keywords 补充排除词，"
            f"或在搜索词里加 -关键词 排除")
    if not diagnostics:
        diagnostics.append("✅ 各环转化率健康，无明显瓶颈。")
    return rows, diagnostics, ratios


def print_funnel(stats):
    rows, diagnostics, ratios = build_funnel(stats)
    print("\n===== 搜索漏斗诊断（转化率）=====")
    print(f"{'环节':<14}{'数量':>7}{'本环转化':>10}{'累计转化':>10}")
    for name, n, step, cum in rows:
        print(f"{name:<14}{n:>7}{step:>10}{cum:>10}")
    print("-------------------------------")
    print(f"最终转化率：入库 {ratios['candidate_rate']*100:.0f}%｜可直发 {ratios['sendable_rate']*100:.0f}%")
    print("\n💡 瓶颈诊断与优化建议：")
    for d in diagnostics:
        print(f"  {d}")
    return ratios


def save_funnel_history(state_path, stats, ratios):
    from datetime import datetime as _dt
    state = _load_state(state_path)
    entry = {
        "t": _dt.now().strftime("%Y-%m-%d %H:%M"),
        "input": stats["input"], "candidates": stats["candidates"],
        "A": stats["A"], "in_db_skip": stats["dup_in_db_skip"],
        "candidate_rate": round(ratios["candidate_rate"], 3),
        "sendable_rate": round(ratios["sendable_rate"], 3),
        "in_db_rate": round(ratios["in_db_rate"], 3),
    }
    state.setdefault("funnel_history", []).append(entry)
    _save_state(state_path, state)


# ============================================================
# 七、CLI 命令
# ============================================================
def _resolve_regions(cli_regions):
    """命令行 --regions 优先；否则用 profile 的 target_regions；都为空则拒绝。"""
    if cli_regions:
        return [r.strip() for r in cli_regions.split(",") if r.strip()]
    regs = RUNTIME["regions"]
    if not regs:
        print("ERROR: 未指定目标地区。请在 company_profile.json 的 "
              "targeting.target_regions 填写，或用 --regions USA,UK 临时传入。")
        sys.exit(2)
    return regs


def _print_level_hint():
    if RUNTIME.get("default_level"):
        print("# 提示：profile 未定义 targeting.customer_levels，"
              "当前用 buyer_titles+channel_keywords 兜底为单层 L1_default；"
              "可在 profile 自定义多层客户分层。", file=sys.stderr)


def cmd_queries(args):
    levels = args.levels.split(",") if args.levels else None
    if levels:
        bad = [l for l in levels if l not in RUNTIME["spectrum"]]
        if bad:
            print(f"ERROR: 层级 {bad} 不存在。可用分层（profile customer_levels.name）："
                  f"{list(RUNTIME['spectrum'].keys())}")
            sys.exit(2)
    regions = _resolve_regions(args.regions)
    breadth = getattr(args, "breadth", "core") or "core"
    qs = build_queries(spectrum_keys=levels, regions=regions, breadth=breadth)
    out = args.out
    reg_n = len(regions)
    lvl_n = len(levels) if levels else len(RUNTIME["spectrum"])
    cat_n = len(RUNTIME["categories"])
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(qs))
        print(f"OK: 生成 {len(qs)} 条搜索词 → {out}  (breadth={breadth}, 地区{reg_n}, 层级{lvl_n})")
    else:
        for q in qs:
            print(q)
        anchor_cn = "客户行业词" if RUNTIME.get("anchor") == "customer" else "产品/服务词"
        print(f"\n# 共 {len(qs)} 条搜索词（breadth={breadth}：{reg_n}地区 × {cat_n}{anchor_cn} × {lvl_n}层级 + 侧翼轴）",
              file=sys.stderr)
        if RUNTIME.get("anchor") == "offer" and RUNTIME.get("offer_type") in ("software", "service"):
            print("# 提示：软件/服务业务用你的品类词搜，容易搜到同行。建议在 targeting.customer_industries "
                  "填客户所在行业（如 logistics / manufacturing），脚本会自动改用客户锚点。", file=sys.stderr)
    _print_level_hint()


def cmd_channels(args):
    chans = args.ch if getattr(args, "ch", None) else None
    regions = _resolve_regions(args.regions) if (chans or args.out) else None
    if not chans and not args.out:
        print("===== 搜索客户渠道配方库（新发现源）=====")
        rec = set(default_channels())
        print(f"当前交付形态：{RUNTIME.get('offer_type') or 'other'}；▶ = 默认会生成的渠道")
        for key, r in CHANNEL_RECIPES.items():
            mark = "▶" if key in rec else " "
            print(f"\n{mark} [{key}] {r['name']}  {r['star']}")
            print(f"    适用：{r['use']}")
            print(f"    示例式：{r['tmpl'][0]}")
        print("\n# 生成发现式： channels --ch social maps  或  channels --out ch.txt")
        return
    qs = build_channel_queries(channels=chans, regions=regions)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(qs))
        picked = ",".join(chans) if chans else "默认渠道：" + ",".join(default_channels())
        print(f"OK: 生成 {len(qs)} 条渠道发现式（{picked}）→ {args.out}")
    else:
        for q in qs:
            print(q)
        print(f"\n# 共 {len(qs)} 条渠道发现式", file=sys.stderr)


def cmd_social(args):
    import social_platforms as _sp
    if args.titles:
        for tier, cn in _sp.TIER_CN.items():
            print(f"[{tier}] {cn}：" + " / ".join(_sp.TITLE_TIERS[tier]))
        print("# 档案 targeting.buyer_titles 会排在词库前面；--tier 选档。")
        return
    plats = args.platforms or RUNTIME.get("social_platforms") or _sp.PLATFORM_ORDER
    bad = [x for x in plats if x not in _sp.PLATFORMS]
    if bad:
        print(f"ERROR: 未知平台 {bad}。可用：{_sp.PLATFORM_ORDER}")
        sys.exit(2)
    if not args.platforms and not args.out and not args.all:
        print("===== 10 大海外社媒 · 免登录公开搜索（只读）=====")
        for pid in _sp.PLATFORM_ORDER:
            sp = _sp.PLATFORMS[pid]
            on = "▶" if pid in plats else " "
            print(f"\n{on} [{pid}] {sp['name']}  {sp['star']}  · {sp['stage']}")
            print(f"    公开搜索式：{sp['tmpl'][0]}")
            print(f"    从结果里取：{sp['extract']}")
            print(f"    人工 · 需登录（本技能不执行）：{sp['login']}")
        print("\n# 生成：social --all  或  social --platforms linkedin instagram --out social.txt")
        print("# 每条结果 → 官网 → 具名邮箱 → filter --against 查库 → 背调（S1/S2 证据）后才进发信。")
        return
    regions = _resolve_regions(args.regions)
    titles = _sp.titles_for(args.tier, RUNTIME.get("buyer_titles") or [])
    qs = _sp.build(plats, regions, RUNTIME["categories"], _top_roles(), titles,
                   list(RUNTIME.get("competitors") or []))
    lines = []
    cur = None
    for pid, q in qs:
        if pid != cur:
            sp = _sp.PLATFORMS[pid]
            lines.append(f"# ---- {sp['name']} {sp['star']} · {sp['stage']} · 取：{sp['extract']}")
            cur = pid
        lines.append(q)
        if pid == "youtube" and args.urls:
            lines.append("#   " + _sp.youtube_url(q))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"OK: 生成 {len(qs)} 条社媒公开搜索式（{len(plats)} 平台 · {len(regions)} 地区 · tier={args.tier}）→ {args.out}")
    else:
        print("\n".join(lines))
        print(f"\n# 共 {len(qs)} 条（{len(plats)} 平台）。只读公开搜索：不登录、不私信、不自动加好友。", file=sys.stderr)


def cmd_filter(args):
    with open(args.results, "r", encoding="utf-8") as f:
        results = json.load(f)
    if isinstance(results, dict) and "results" in results:
        results = results["results"]

    db_index = None
    db_loaded = 0
    if args.against:
        emails_set, domains_set, codes_set, db_loaded = load_customer_db(args.against, since=args.since)
        db_index = (emails_set, domains_set, codes_set)
    else:
        print("=" * 48)
        print("⚠️  你没有传 --against 查库！可能在做重复劳动。")
        print("    客户库里很可能已有这些客户，不查库=白搜+白背调。")
        print("    正确用法： filter results.json --against 全量客户数据库.csv")
        print("=" * 48)

    candidates, stats = filter_and_grade(results, db_index=db_index)

    out = args.out or "candidates.csv"
    fields = ["domain", "url", "brand", "email_grade", "best_email",
              "all_emails", "region_hint", "customer_type_hint", "next_action", "note"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(candidates)

    print("===== 搜索候选分级结果 =====")
    print(f"输入结果            : {stats['input']}")
    if args.against:
        since_txt = f"（≥{args.since} 近期数据）" if args.since else "（全量）"
        print(f"客户管家库比对      : 已加载 {db_loaded} 条{since_txt}")
        print(f"库内已有 去重       : {stats['dup_in_db_skip']}  ← 避免重复开发已有客户")
    print(f"平台/集市 过滤      : {stats['platform_skip']}")
    print(f"目录/媒体/政府 过滤 : {stats['nonlead_skip']}")
    print(f"非目标词 过滤       : {stats['nontarget_skip']}  ← profile exclude_keywords")
    print(f"竞品特征 过滤       : {stats['competitor_skip']}  ← profile competitor_markers")
    print(f"域名重复 过滤       : {stats['dup_domain_skip']}")
    print(f"-------------------------------")
    print(f"入库候选            : {stats['candidates']}")
    print(f"  ├─ A级(企业具名邮箱): {stats['A']}")
    print(f"  ├─ B级(通用/免费邮箱): {stats['B']}")
    print(f"  └─ 无邮箱(需补)     : {stats['no_email']}")
    print(f"→ 候选明细已写入      : {out}")

    ratios = print_funnel(stats)
    save_funnel_history(args.state, stats, ratios)

    print("\n下一步：对 A/B 级候选逐个走【背调→非目标复核→查重】后入 pipeline。")


# ============================================================
# 八、非目标品类复核（数据质量：只标不改，由 profile 排除词驱动）
# ============================================================
def cmd_audit_exclude(args):
    """挑出候选 CSV 中疑似命中非目标排除词/竞品特征词的记录，人工确认后再处理。
    绝不自动改动数据（删除/改动须负责人同意）。"""
    rules = [("exclude_keywords", k) for k in RUNTIME["exclude_keywords"]]
    rules += [("competitor_markers", k) for k in RUNTIME["competitor_markers"]]
    if not rules:
        print("profile 未配置 targeting.exclude_keywords / competitor_markers，"
              "没有行业过滤词可供复核。")
        print("（平台/目录/政府/媒体/免费邮箱等技术性过滤不在本复核范围内。）")
        return
    suspicious = []
    with open(args.csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 2):
            blob = " ".join([
                row.get("brand", ""), row.get("customer_type_hint", ""),
                row.get("note", ""), row.get("url", ""), row.get("domain", ""),
            ]).lower()
            hits = [f"{src}:{k}" for src, k in rules if str(k).lower() in blob]
            if hits:
                suspicious.append((i, row.get("brand") or row.get("domain"), hits))
    print(f"===== 非目标/竞品复核（共扫 {args.csv}）=====")
    if not suspicious:
        print("未发现命中非目标词/竞品特征词的可疑记录。")
    else:
        print(f"发现 {len(suspicious)} 条可疑记录（请人工背调复核，本工具不自动改）：")
        for ln, brand, hits in suspicious:
            print(f"  行{ln}: {brand} | 命中: {', '.join(sorted(set(hits)))}")
        print("\n→ 确认非目标/竞品的请移入黑名单/跳过，不要发信。")


# ============================================================
# 九、自循环引擎（保底补池 + 四维轮换：高度 / 广度 / 深度 / 远度 + 内置调度）
# ============================================================
# 四个维度（每次运行只取每维的一个档位，逐次推进，长线全覆盖、不一次打光）：
#   深度 depth   —— 同一片市场挖多深：d1 公司级发现 → d2 决策人穿透（采购链职位词）
#                   → d3 存量深挖（成交客户/参照品牌的同类、已发未回账户的其他角色）；转得最快，
#                   同一「地区×层级」连续三次运行由浅到深挖透，再换下一片。
#   远度 region  —— 市场半径：profile.targeting.target_regions 的顺序即「由近到远」
#                   （把已成交/最熟/时差最近的市场写在前面）；深度挖完一轮后换下一个地区。
#   高度 level   —— 客户价值梯队：profile.targeting.customer_levels 的顺序即「由高到低」
#                   （高价值/大客户层写在前面）；所有地区跑完一圈后降一档。
#   广度 breadth —— 搜索面宽窄：core 核心组合 → wide +场景/意图轴 → max +全部侧翼轴；转得最慢。
DEFAULT_STATE = "search_state.json"
DATA_DIR = os.environ.get("B2B_DATA_DIR", "data")
DEFAULT_POOL = os.path.join(DATA_DIR, "customer_db.csv")
DEPTHS = ["d1_company", "d2_decision", "d3_stock"]
BREADTHS = ["core", "wide", "max"]
DIM_LABELS = {"region": "远度", "level": "高度", "depth": "深度", "breadth": "广度"}
# 客户库里这些关系不进入冷开发可发池（老客户走生命周期，不当陌生人开发）
NON_COLD_RELATIONS = {"existing_customer", "do_not_contact", "competitor", "lost_do_not_contact"}


def _load_state(path):
    state = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = None
    if not isinstance(state, dict):
        state = {}
    # 兼容 v3.0 旧状态文件（没有 depth_idx）：补齐字段，不丢历史
    for k, v in (("region_idx", 0), ("level_idx", 0), ("depth_idx", 0), ("breadth_idx", 0),
                 ("run_count", 0), ("last_run", ""), ("history", [])):
        state.setdefault(k, v)
    return state


def _save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _rotate_plan(state):
    """四维梯次轮换：深度(d1/d2/d3，最快) × 远度(地区) × 高度(层级) × 广度(core/wide/max，最慢)。"""
    regions = RUNTIME["regions"]
    levels = list(RUNTIME["spectrum"].keys())
    r = state["region_idx"] % len(regions)
    l = state["level_idx"] % len(levels)
    d = state.get("depth_idx", 0) % len(DEPTHS)
    b = state["breadth_idx"] % len(BREADTHS)
    return {"region": regions[r], "level": levels[l], "depth": DEPTHS[d], "breadth": BREADTHS[b],
            "region_idx": r, "level_idx": l, "depth_idx": d, "breadth_idx": b}


def _advance_state(state):
    """深度转得最快（同一片市场连挖 d1→d2→d3）→ 远度（地区由近到远）→ 高度（层级由高到低）→ 广度（最慢）。"""
    regions_n = len(RUNTIME["regions"])
    levels_n = len(RUNTIME["spectrum"])
    state["depth_idx"] = (state.get("depth_idx", 0) + 1) % len(DEPTHS)
    if state["depth_idx"] == 0:
        state["region_idx"] = (state["region_idx"] + 1) % regions_n
        if state["region_idx"] == 0:
            state["level_idx"] = (state["level_idx"] + 1) % levels_n
            if state["level_idx"] == 0:
                state["breadth_idx"] = (state["breadth_idx"] + 1) % len(BREADTHS)
    return state


def _cycle_len():
    return (max(1, len(RUNTIME["regions"])) * max(1, len(RUNTIME["spectrum"]))
            * len(DEPTHS) * len(BREADTHS))


def _read_rows(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _stock_seeds():
    """d3 存量深挖的种子：成交客户品牌 + 参照品牌 + 已发≥2 封仍未回复的账户。"""
    won = [r.get("brand", "").strip() for r in _read_rows(os.path.join(DATA_DIR, "success_cases.csv"))]
    refs = list(RUNTIME.get("competitors") or [])
    quiet = []
    for r in _read_rows(os.path.join(DATA_DIR, "sent_history.csv")):
        st = (r.get("status") or "").lower()
        try:
            fu = int(r.get("followup_count") or 0)
        except ValueError:
            fu = 0
        if st in ("sent", "") and fu >= 1 and r.get("brand"):
            quiet.append(r["brand"].strip())

    def _u(seq):
        seen, out = set(), []
        for x in seq:
            k = x.lower()
            if x and k not in seen:
                seen.add(k)
                out.append(x)
        return out
    return _u(won), _u(refs), _u(quiet)


def _depth_titles(limit=8):
    import social_platforms as _sp
    titles = list(RUNTIME.get("buyer_titles") or [])
    titles += _sp.TITLE_TIERS.get("decision", [])[:4] + _sp.TITLE_TIERS.get("execution", [])[:4]
    out, seen = [], set()
    for t in titles:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t.strip())
    return out[:limit]


def build_depth_queries(depth, region, level, breadth):
    """按深度档生成今日搜索词。返回 (queries, note)。"""
    base = build_queries(spectrum_keys=[level], regions=[region], breadth=breadth)
    cats = RUNTIME["categories"][:3]
    if depth == "d1_company":
        return base, "d1 公司级发现：先找对的公司"
    titles = _depth_titles()
    d2 = []
    for cat in cats:
        for t in titles:
            d2.append(f'site:linkedin.com/in "{t}" {cat} {region}')
            d2.append(f'{region} {cat} "{t}" contact')
    if depth == "d2_decision":
        return _dedup_keep(base[:40] + d2), "d2 决策人穿透：在已知公司类型里找到具体拍板人/执行人"
    won, refs, quiet = _stock_seeds()
    d3 = []
    for seed in (won + refs)[:10]:
        d3 += [f"companies like {seed} {region}", f"{seed} competitors {region}",
               f"{seed} customers OR clients {region}"]
    for brand in quiet[:10]:
        for t in titles[:3]:
            d3.append(f'site:linkedin.com/in "{brand}" "{t}"')
    if not d3:
        return _dedup_keep(base[:40] + d2), ("d3 存量深挖暂无种子（无成交案例/参照品牌/已发未回账户）"
                                             "→ 本轮回落为 d2；导入客户库或首单成交后自动生效")
    return _dedup_keep(d3 + d2[:20]), "d3 存量深挖：成交客户/参照品牌的同类 + 已发未回账户的其他角色"


def _dedup_keep(seq):
    seen, out = set(), []
    for q in seq:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _count_sendable_pool(pool_csv):
    """数客户库里【现在可发】的冷开发候选：有邮箱 + 未发过 + 不是老客户/禁联。"""
    sendable = 0
    total = 0
    if not os.path.exists(pool_csv):
        return 0, 0
    already = {(r.get("email") or "").strip().lower() for r in _read_rows(os.path.join(DATA_DIR, "sent_history.csv"))}
    with open(pool_csv, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            total += 1
            email = (row.get("email") or "").strip()
            est = (row.get("email_status") or "").strip().lower()
            rel = (row.get("relation") or "").strip().lower()
            sent = est in ("sent", "已发", "replied", "已回复", "bounced", "退信")
            if email and "@" in email and not sent and rel not in NON_COLD_RELATIONS \
                    and email.lower() not in already:
                sendable += 1
    return sendable, total


def cmd_replenish(args):
    """保底补池：检查可发池是否低于红线，低于则按四维轮换生成今日搜索轮次。"""
    if not RUNTIME["regions"]:
        print("ERROR: profile 未配置 targeting.target_regions，无法轮换远度（地区）。"
              "请先在 company_profile.json 填写目标地区（由近到远排序）。")
        sys.exit(2)
    floor = args.floor
    daily = args.daily_target
    state = _load_state(args.state)
    sendable, total = _count_sendable_pool(args.pool)

    print("===== 客户池保底检查（自循环引擎）=====")
    print(f"客户库              : {args.pool}" + ("" if os.path.exists(args.pool) else
          "（不存在：安装时请先跑 data_import.py 导入自有客户库，或在档案里声明 none）"))
    print(f"库总量              : {total}")
    print(f"可发冷开发候选（有邮箱·未发·非老客户）: {sendable}")
    print(f"保底红线            : {floor}   ｜每日发送目标: {daily}")

    days_left = sendable // daily if daily else 0
    below_floor = sendable < floor
    below_ahead = days_left < args.ahead_days
    need_replenish = below_floor or below_ahead
    if below_floor:
        print(f"\n[!] 低于硬红线：可发 {sendable} < {floor}，只够 ~{days_left} 天，需立即补池。")
    elif below_ahead:
        print(f"\n[!] 低于提前储备线：只够发 ~{days_left} 天（<提前量 {args.ahead_days} 天），提前补池。")
    else:
        print(f"\n[OK] 池位充足：可支撑 ~{days_left} 天发送。")

    plan = _rotate_plan(state)
    if need_replenish or args.force:
        qs, note = build_depth_queries(plan["depth"], plan["region"], plan["level"], plan["breadth"])
        print(f"\n【今日四维轮换】远度={plan['region']} × 高度={plan['level']} × "
              f"深度={plan['depth']} × 广度={plan['breadth']}")
        print(f"  {note}")
        print(f"生成搜索词 {len(qs)} 条（四维梯次，不重打；全覆盖一轮 = {_cycle_len()} 次运行）")
        if args.emit:
            with open(args.emit, "w", encoding="utf-8") as f:
                f.write("\n".join(qs))
            print(f"→ 今日搜索词已写入：{args.emit}")
            print("  下一步：抽取后用 filter 子命令 --against 本库去重分级→非目标复核→背调→入 pipeline。")
        from datetime import datetime as _dt
        state["run_count"] += 1
        state["last_run"] = _dt.now().strftime("%Y-%m-%d %H:%M")
        state["history"] = (state.get("history", []) + [
            {"t": state["last_run"], "region": plan["region"], "level": plan["level"],
             "depth": plan["depth"], "breadth": plan["breadth"],
             "queries": len(qs), "sendable_before": sendable}])[-60:]
        _advance_state(state)
        _save_state(args.state, state)
    else:
        print("\n本日无需补池（如需强制轮换搜索加 --force）。")

    if need_replenish and args.warn_file:
        reason = f"可发{sendable}<硬红线{floor}" if below_floor else f"仅够{days_left}天<提前量{args.ahead_days}天"
        with open(args.warn_file, "w", encoding="utf-8") as f:
            f.write(f"[{state.get('last_run','')}] 客户池保底预警：{reason}。已触发补池轮换。")
        print(f"→ 预警已写入：{args.warn_file}")
    _print_level_hint()


def cmd_status(args):
    """看四维轮换进度：下次该跑哪里 + 历史轨迹。"""
    if not RUNTIME["regions"]:
        print("ERROR: profile 未配置 targeting.target_regions，无轮换计划。")
        sys.exit(2)
    state = _load_state(args.state)
    plan = _rotate_plan(state)
    print("===== 四维轮换进度（高度 / 广度 / 深度 / 远度）=====")
    print(f"已跑次数      : {state.get('run_count',0)}   ｜全覆盖一轮 = {_cycle_len()} 次运行")
    print(f"上次运行      : {state.get('last_run','') or '从未'}")
    print(f"下次将跑      : 远度={plan['region']} × 高度={plan['level']} × "
          f"深度={plan['depth']} × 广度={plan['breadth']}")
    print(f"远度梯次      : {' → '.join(RUNTIME['regions'])}（profile 顺序 = 由近到远）")
    print(f"高度梯次      : {' → '.join(RUNTIME['spectrum'].keys())}（profile 顺序 = 由高到低）")
    print(f"深度梯次      : {' → '.join(DEPTHS)}（转得最快：同一片市场连挖三层）")
    print(f"广度梯次      : {' → '.join(BREADTHS)}")
    hist = state.get("history", [])
    if hist:
        print("\n最近 8 次轮换：")
        for h in hist[-8:]:
            print(f"  {h['t']}  {h['region']:<10} {h['level']:<14} {h.get('depth','d1_company'):<12} "
                  f"{h['breadth']:<5} → {h['queries']}词（当时可发{h.get('sendable_before','?')}）")
    else:
        print("\n尚无轮换历史。先跑 replenish 或 schedule。")
    _print_level_hint()


# ============================================================
# 互斥标签组：同一字段内这些取值不可共存，新旧不一致=冲突。
# variant_tag 为产品变体泛化标签（具体含义由使用方定义）；
# need_tag 为客户需求向标签。
# 默认不预置任何行业的互斥关系；由 profile.positioning.conflict_groups 定义，例如
#   {"need_tag": [["line_a"], ["line_b"]], "variant_tag": [["variant_a"], ["variant_b"]]}
# 未定义的字段：新旧值不同即提示（仍只标不改）。
CONFLICT_GROUPS = {"need_tag": [], "variant_tag": [], "solution_tag": []}


def _load_conflict_config():
    pos = RUNTIME.get("positioning") or {}
    groups = dict(CONFLICT_GROUPS)
    for fld, gs in (pos.get("conflict_groups") or {}).items():
        groups[fld] = [set(_norm_tag(x) for x in g) for g in gs if g]
    rules = [r for r in (pos.get("tag_rules") or []) if isinstance(r, dict)]
    return groups, rules


def _norm_tag(v):
    return (v or "").strip().lower()


def _tags_conflict(field, old, new):
    """判断同一字段的旧标签 old 与新背调结论 new 是否矛盾。
    两者都非空且不相等，且分属互斥组 → 冲突。need_review/空 不算冲突。"""
    o, n = _norm_tag(old), _norm_tag(new)
    if not o or not n or o == n:
        return False
    if n in ("review", "need_review", "unknown"):
        return False
    groups = CONFLICT_GROUPS.get(field)
    if groups:
        for ga in groups:
            for gb in groups:
                if ga is not gb and o in ga and n in gb:
                    return True
    return o != n


def _load_db_rows(csv_path, since=None):
    """加载客户库整行，建 email/域名/customer_code → row 索引（保留旧标签供比对）。"""
    by_email, by_domain, by_code = {}, {}, {}
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if since:
                ts = (row.get("updated_at") or row.get("created_at") or "")[:10]
                if ts and ts < since:
                    continue
            em = (row.get("email") or "").strip().lower()
            if em:
                by_email.setdefault(em, row)
            web = row.get("website") or row.get("domain") or ""
            dom = domain_of(web) if "//" in web else web.strip().lower().replace("www.", "")
            if dom:
                by_domain.setdefault(dom, row)
            code = (row.get("customer_code") or "").strip()
            if code:
                by_code.setdefault(code, row)
    return by_email, by_domain, by_code


def _match_db_row(new_rec, by_email, by_domain, by_code):
    """按 email → 域名 → customer_code 优先级在库里找到同一客户的旧行。"""
    direct = (new_rec.get("email") or "").strip().lower()
    cand_emails = ([direct] if direct else []) + extract_emails(new_rec)
    for e in cand_emails:
        if e in by_email:
            return by_email[e]
    web = new_rec.get("website") or new_rec.get("domain") or new_rec.get("url") or ""
    dom = domain_of(web) if "//" in web else web.strip().lower().replace("www.", "")
    if dom and dom in by_domain:
        return by_domain[dom]
    code = (new_rec.get("customer_code") or "").strip()
    if code and code in by_code:
        return by_code[code]
    return None


def cmd_conflict_check(args):
    """标签冲突校正：背调新结论 vs 库内旧标签。
    两种模式：
      (A) 传 --new：把新背调结论文件（JSON/CSV，含 variant_tag/need_tag）
          与 --against 客户库逐条比对，找出同一客户新旧标签矛盾的。
      (B) 不传 --new：只扫 --against 库自身，找 variant_tag 与 need_tag 内部矛盾。
    一律【只标不改】，输出冲突清单交人工拍板（AI 只建议，人工决定）。"""
    by_email, by_domain, by_code = _load_db_rows(args.against, since=args.since)
    db_rows = list({id(r): r for r in list(by_email.values())
                    + list(by_domain.values()) + list(by_code.values())}.values())
    conflicts = []
    groups, rules = _load_conflict_config()
    CONFLICT_GROUPS.update(groups)
    fields = list(CONFLICT_GROUPS.keys())

    if args.new:
        if args.new.lower().endswith(".json"):
            with open(args.new, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            if isinstance(new_data, dict) and "results" in new_data:
                new_data = new_data["results"]
        else:
            with open(args.new, "r", encoding="utf-8-sig", newline="") as f:
                new_data = list(csv.DictReader(f))
        for rec in new_data:
            old_row = _match_db_row(rec, by_email, by_domain, by_code)
            if not old_row:
                continue
            name = rec.get("brand") or old_row.get("brand") or old_row.get("customer_name") or "?"
            for fld in fields:
                new_v = rec.get(fld)
                old_v = old_row.get(fld)
                if _tags_conflict(fld, old_v, new_v):
                    conflicts.append((name, fld, old_v, new_v,
                                      "新背调结论与库内旧标签矛盾"))
    else:
        # 库内自洽检查：规则全部来自 profile.positioning.tag_rules，不预置任何行业规则
        if not rules:
            print("ℹ️  profile.positioning.tag_rules 未配置：库内自洽检查无规则可用，"
                  "只能用 --new 做新旧比对。")
        for row in db_rows:
            name = row.get("brand") or row.get("customer_name") or "?"
            for r in rules:
                a = _norm_tag(row.get(r.get("if_field", "")))
                bval = _norm_tag(row.get(r.get("forbid_field", "")))
                if a and a == _norm_tag(r.get("equals")) and bval in {_norm_tag(x) for x in r.get("values", [])}:
                    conflicts.append((name, f"{r['if_field']}×{r['forbid_field']}", f"{r['if_field']}={a}",
                                      f"{r['forbid_field']}={bval}", r.get("reason") or "违反 tag_rules"))
    print("=" * 52)
    print("标签冲突校正：背调结论 vs 库内旧标签（只标不改）")
    print("=" * 52)
    if not conflicts:
        print("✅ 未发现标签冲突。")
    else:
        print(f"⚠️  发现 {len(conflicts)} 条标签冲突（本工具绝不自动改，请背调复核后拍板）：\n")
        for name, fld, old_v, new_v, why in conflicts:
            print(f"  ▸ {name} | {fld}：旧=[{old_v or '空'}] ≠ 新=[{new_v or '空'}] → {why}")
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "field", "old_tag", "new_tag", "reason", "decision"])
                for name, fld, old_v, new_v, why in conflicts:
                    w.writerow([name, fld, old_v, new_v, why, "pending_人工拍板"])
            print(f"\n→ 冲突清单已写入：{args.out}（decision 列留空，逐条定夺后才回写）")
    print("\n原则：标签冲突只提醒不自改；AI 只建议，最终由人工拍板。")


def cmd_funnel(args):
    """看历史多次搜索的累计转化率趋势（诊断搜索效率是否在改善）。"""
    state = _load_state(args.state)
    hist = state.get("funnel_history", [])
    if not hist:
        print("尚无漏斗历史。先跑几次 filter（带 --against）积累数据。")
        return
    print("===== 搜索漏斗历史转化率趋势 =====")
    print(f"{'时间':<18}{'输入':>6}{'入库':>6}{'入库率':>8}{'可直发率':>9}{'库重复率':>9}")
    for h in hist[-15:]:
        print(f"{h['t']:<18}{h['input']:>6}{h['candidates']:>6}"
              f"{h['candidate_rate']*100:>7.0f}%{h['sendable_rate']*100:>8.0f}%{h['in_db_rate']*100:>8.0f}%")
    n = len(hist)
    avg_cand = sum(h["candidate_rate"] for h in hist) / n
    avg_send = sum(h["sendable_rate"] for h in hist) / n
    avg_db = sum(h["in_db_rate"] for h in hist) / n
    print("-" * 56)
    print(f"{'历史均值':<18}{'':>6}{'':>6}{avg_cand*100:>7.0f}%{avg_send*100:>8.0f}%{avg_db*100:>8.0f}%")
    print("\n💡 趋势解读：")
    if avg_db > FUNNEL_DUP_DB_RED:
        print(f"  🔴 库重复率均值 {avg_db*100:.0f}% 偏高 → 搜索词长期命中已开发区，该换新地区/产品词。")
    if avg_send < FUNNEL_NAMED_EMAIL_RED:
        print(f"  🔴 可直发率均值 {avg_send*100:.0f}% 偏低 → 长期具名邮箱不足，强化 email_guesser 补齐。")
    if avg_db <= FUNNEL_DUP_DB_RED and avg_send >= FUNNEL_NAMED_EMAIL_RED:
        print("  ✅ 历史转化率健康。")


def cmd_schedule(args):
    import time
    from datetime import datetime as _dt

    class _Args:
        pool = args.pool
        floor = args.floor
        daily_target = args.daily_target
        ahead_days = args.ahead_days
        state = args.state
        emit = args.emit
        warn_file = args.warn_file
        force = True

    def _job():
        print(f"\n⏰ [{_dt.now().strftime('%Y-%m-%d %H:%M')}] 自循环触发：检查池→补池→轮换")
        cmd_replenish(_Args())

    print("===== 内置调度器启动（自循环引擎）=====")
    print(f"每日 {args.at} 自动跑 replenish 闭环｜保底红线 {args.floor}｜库 {args.pool}")
    print("Ctrl+C 停止。启动时先立即跑一次。\n")
    _job()
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
        hh, mm = args.at.split(":")
        sched = BlockingScheduler()
        sched.add_job(_job, "cron", hour=int(hh), minute=int(mm))
        print("（使用 APScheduler cron 调度）")
        sched.start()
    except ImportError:
        print("（未装 APScheduler，使用零依赖 sleep 循环；pip install apscheduler 可升级）")
        last_day = _dt.now().strftime("%Y-%m-%d")
        target_h, target_m = map(int, args.at.split(":"))
        while True:
            time.sleep(60)
            now = _dt.now()
            today = now.strftime("%Y-%m-%d")
            if today != last_day and (now.hour, now.minute) >= (target_h, target_m):
                last_day = today
                _job()


def _build_parser():
    p = argparse.ArgumentParser(
        description="通用 B2B 客户搜索候选生成器 + 自循环引擎（技能版本 v3.1 · 配置驱动·行业无关）")
    sub = p.add_subparsers(dest="cmd")

    pq = sub.add_parser("queries", help="生成搜索词全集（产品词×分层角色词×地区，词表来自 profile）")
    pq.add_argument("--out")
    pq.add_argument("--levels", help="只用部分层级，逗号分隔；层级名取自 profile customer_levels[].name")
    pq.add_argument("--regions", help="只跑部分地区，逗号分隔；缺省用 profile target_regions")
    pq.add_argument("--breadth", choices=["core", "wide", "max"], default="core")
    pq.set_defaults(func=cmd_queries)

    pc = sub.add_parser("channels", help="新发现源：按渠道（社媒/地图/海关/招标/招聘/目录/评测/会议/竞品…）生成发现式；缺省按行业包/交付形态自动挑渠道")
    pc.add_argument("--ch", nargs="+",
                    choices=list(CHANNEL_RECIPES.keys()),
                    help="只生成指定渠道（空白则列出全部渠道说明）")
    pc.add_argument("--regions", help="只跑部分地区，逗号分隔")
    pc.add_argument("--out")
    pc.set_defaults(func=cmd_channels)

    pso = sub.add_parser("social", help="10 平台社媒免登录公开搜索式（LinkedIn/IG/FB/YouTube/TikTok/Pinterest/X/Threads/WhatsApp/Lemon8）")
    pso.add_argument("--platforms", nargs="+", help="只生成指定平台（缺省用 profile search.social_platforms，再缺省 10 个全开）")
    pso.add_argument("--all", action="store_true", help="10 个平台全部生成")
    pso.add_argument("--tier", choices=["decision", "execution", "influence", "all"], default="all",
                     help="职位词档：决策层/执行层/影响层（LinkedIn 布尔式用）")
    pso.add_argument("--regions", help="只跑部分地区，逗号分隔")
    pso.add_argument("--titles", action="store_true", help="只打印 30 个采购链职位词库")
    pso.add_argument("--urls", action="store_true", help="YouTube 额外给站内搜索链接（公开页面，无需登录）")
    pso.add_argument("--out")
    pso.set_defaults(func=cmd_social)

    pf = sub.add_parser("filter", help="过滤+库增量去重+域名去重+非目标词/竞品特征门禁+分级")
    pf.add_argument("results")
    pf.add_argument("--out")
    pf.add_argument("--against", help="客户库 CSV（搜索前先查库去重）")
    pf.add_argument("--since", help="只比对该日期起的近期库数据")
    pf.add_argument("--state", default=DEFAULT_STATE, help="状态文件（存漏斗历史）")
    pf.set_defaults(func=cmd_filter)

    # 标签冲突校正：背调新结论 vs 库内旧标签（只标不改，人工拍板）
    pcc = sub.add_parser("conflict-check", help="背调新结论 vs 库内旧标签 冲突检查（只标不改，交人工拍板）")
    pcc.add_argument("--against", required=True, help="客户库 CSV 路径（旧标签来源）")
    pcc.add_argument("--new", help="新背调结论文件（JSON/CSV，含 need_tag/solution_tag/variant_tag）；不传则按 profile.positioning.tag_rules 查库内自相矛盾")
    pcc.add_argument("--since", help="只比对 updated_at/created_at ≥ 该日期(YYYY-MM-DD)的库记录")
    pcc.add_argument("--out", help="把冲突清单写到 CSV（decision 列=pending_人工拍板）")
    pcc.set_defaults(func=cmd_conflict_check)

    pfn = sub.add_parser("funnel", help="看历史搜索累计转化率趋势 + 瓶颈诊断")
    pfn.add_argument("--state", default=DEFAULT_STATE)
    pfn.set_defaults(func=cmd_funnel)

    pa = sub.add_parser("audit-exclude", aliases=["audit-category"],
                        help="非目标/竞品复核（按 profile 排除词挑可疑记录，不自动改）")
    pa.add_argument("csv", help="候选/客户库 CSV 路径")
    pa.set_defaults(func=cmd_audit_exclude)

    pr = sub.add_parser("replenish", help="保底补池：池<红线则按四维轮换（高度/广度/深度/远度）生成今日搜索词 + 预警")
    pr.add_argument("--pool", default=DEFAULT_POOL, help="客户库 CSV（默认 $B2B_DATA_DIR/customer_db.csv，由 data_import.py 生成）")
    pr.add_argument("--floor", type=int, default=100, help="硬保底红线，默认 100")
    pr.add_argument("--daily-target", type=int, default=100, dest="daily_target")
    pr.add_argument("--ahead-days", type=int, default=30, dest="ahead_days")
    pr.add_argument("--state", default=DEFAULT_STATE)
    pr.add_argument("--emit", help="把今日该跑的搜索词写到文件")
    pr.add_argument("--warn-file", dest="warn_file")
    pr.add_argument("--force", action="store_true")
    pr.set_defaults(func=cmd_replenish)

    ps = sub.add_parser("schedule", help="内置调度器：常驻每日定点自动跑 replenish 闭环")
    ps.add_argument("--pool", default=DEFAULT_POOL)
    ps.add_argument("--at", default="09:00")
    ps.add_argument("--floor", type=int, default=100)
    ps.add_argument("--daily-target", type=int, default=100, dest="daily_target")
    ps.add_argument("--ahead-days", type=int, default=30, dest="ahead_days")
    ps.add_argument("--state", default=DEFAULT_STATE)
    ps.add_argument("--emit", default="queries_today.txt")
    ps.add_argument("--warn-file", dest="warn_file", default="pool_warning.txt")
    ps.set_defaults(func=cmd_schedule)

    pst = sub.add_parser("status", help="看四维轮换进度（高度/广度/深度/远度）")
    pst.add_argument("--state", default=DEFAULT_STATE)
    pst.set_defaults(func=cmd_status)

    return p


def main():
    p = _build_parser()
    args = p.parse_args()  # -h/--help 由此直接输出用法并退出，无需档案
    if not getattr(args, "cmd", None):
        p.print_help()
        sys.exit(0)

    # 配置门禁：所有业务子命令必须先有完整公司档案
    if _cfg is None:
        print("ERROR: 找不到 config.py 配置门禁，拒绝执行。")
        sys.exit(2)
    try:
        profile = _cfg.load_profile(require_complete=True)
    except _cfg.ProfileNotConfigured as e:
        print("ERROR: 公司档案未就绪，禁止执行。\n" + str(e))
        sys.exit(2)

    RUNTIME.update(build_profile_context(profile))
    args.func(args)


if __name__ == "__main__":
    main()
