#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_platforms.py — 10 大海外社媒「免登录公开搜索」配方 + 采购链职位词库（30 个，三档）

只做一件事：生成可直接粘进 Google / Bing 的公开搜索式（site: 运算符），
从搜索引擎已公开索引的页面里找「目标公司 / 决策人主页 / 行业群组 / 评论区信号」。
- 不登录、不注册、不调用任何平台接口、不自动加好友 / 私信 / 进群 / 关注。
- 需要登录才能做的动作（连接请求、DM、进群、看粉丝列表）一律列为「人工 · 需登录」，
  本技能不执行，只在 references/social_media_playbooks.md 给方法。
- 每条结果仍要走：官网 → 具名邮箱 → filter --against 查库去重 → 背调（S1/S2 证据）。

被 search_customers.py social 子命令调用；也可单独 import。
纯标准库。
"""

from urllib.parse import quote_plus
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------- 采购链职位词库：决策层 / 执行层 / 影响层 各 10 个 ----------------
TITLE_TIERS = {
    "decision": [  # 拍板、批预算
        "Owner", "Founder", "CEO", "Managing Director", "General Manager",
        "Head of Purchasing", "Procurement Director", "VP Operations",
        "Commercial Director", "Category Director",
    ],
    "execution": [  # 具体找供应商、比价、下单
        "Buyer", "Senior Buyer", "Purchasing Manager", "Procurement Manager",
        "Sourcing Manager", "Category Manager", "Supply Chain Manager",
        "Product Manager", "Merchandiser", "Vendor Manager",
    ],
    "influence": [  # 提需求、做评估、影响选型
        "Operations Manager", "Quality Manager", "Technical Director",
        "Engineering Manager", "Project Manager", "Product Development Manager",
        "Brand Manager", "Marketing Manager", "IT Manager", "Office Manager",
    ],
}
TIER_CN = {"decision": "决策层", "execution": "执行层", "influence": "影响层"}

# ---------------- 10 平台配方 ----------------
# tmpl 占位：{cat} 品类/客户行业词 · {role} 角色词 · {region} 地区 · {t3} 三个职位的 OR 组
#           {tag} 话题标签词（由品类词生成）· {competitor} 参照/竞品品牌
PLATFORMS = {
    "linkedin": {
        "name": "LinkedIn", "star": "⭐⭐⭐⭐⭐", "stage": "找决策人",
        "tmpl": [
            'site:linkedin.com/in ({t3}) "{cat}" "{region}"',
            'site:linkedin.com/company "{cat}" {role} "{region}"',
            'site:linkedin.com/posts "{cat}" ("looking for" OR sourcing OR RFQ OR tender) "{region}"',
        ],
        "extract": "姓名、职位、公司名、公司官网（公司页 About）；帖子里的采购/招标信号",
        "login": "连接请求、InMail、看完整履历、Sales Navigator 筛选",
    },
    "instagram": {
        "name": "Instagram", "star": "⭐⭐⭐⭐", "stage": "找品牌/门店",
        "tmpl": [
            'site:instagram.com "{cat}" ({role} OR stockist OR wholesale OR distributor) "{region}"',
            'site:instagram.com "#{tag}" "{region}"',
            'site:instagram.com "{competitor}" (stockist OR retailer OR "available at" OR partner)',
        ],
        "extract": "账号简介里的官网链接、Email 按钮文字、城市；是否标注 stockist/wholesale",
        "login": "看粉丝/关注列表、话题页滚动、DM、点赞评论",
    },
    "facebook": {
        "name": "Facebook", "star": "⭐⭐⭐", "stage": "找群组/商家页",
        "tmpl": [
            'site:facebook.com/groups "{cat}" (buyers OR wholesale OR B2B OR procurement OR sourcing) "{region}"',
            'site:facebook.com "{cat}" {role} "{region}" (email OR contact)',
        ],
        "extract": "公开群组名与主题（判断买家聚集地）、商家页 About 里的官网/邮箱/地址",
        "login": "进群、群内发帖、Messenger 私信",
    },
    "youtube": {
        "name": "YouTube", "star": "⭐⭐⭐", "stage": "评论区/频道挖买家",
        "tmpl": [
            'site:youtube.com "{cat}" (review OR unboxing OR "how to choose" OR "factory tour" OR demo) "{region}"',
            'site:youtube.com "{cat}" {role}',
        ],
        "url": "https://www.youtube.com/results?search_query={q}",
        "extract": "频道简介「商务合作」邮箱、频道外链官网；视频标题里的行业/地区；评论区自报身份的买家",
        "login": "评论、订阅、社区帖互动",
    },
    "tiktok": {
        "name": "TikTok", "star": "⭐⭐⭐", "stage": "短视频/评论区信号",
        "tmpl": [
            'site:tiktok.com "{cat}" (wholesale OR supplier OR "small business" OR {role}) "{region}"',
            'site:tiktok.com "#{tag}"',
        ],
        "extract": "账号简介官网链接、品牌名；评论区里问「哪里进货 / 供应商」的账号",
        "login": "评论、私信、关注",
    },
    "pinterest": {
        "name": "Pinterest", "star": "⭐⭐⭐", "stage": "图版/长尾找品牌",
        "tmpl": [
            'site:pinterest.com "{cat}" (wholesale OR catalog OR lookbook OR supplier OR {role})',
        ],
        "extract": "Pin 指向的外链域名（真实品牌/店铺官网）、图版名称里的细分品类",
        "login": "收藏、关注、私信",
    },
    "x": {
        "name": "X (Twitter)", "star": "⭐⭐", "stage": "需求对话监听",
        "tmpl": [
            'site:x.com "{cat}" ("looking for" OR "recommend a" OR supplier OR vendor OR RFQ) "{region}"',
        ],
        "extract": "发需求帖的账号与其简介官网；行业会议/展会话题下的公司账号",
        "login": "回复、私信、关注",
    },
    "threads": {
        "name": "Threads", "star": "⭐⭐", "stage": "与 IG 联动",
        "tmpl": [
            'site:threads.net "{cat}" ({role} OR supplier OR wholesale OR sourcing)',
        ],
        "extract": "账号名（通常与 IG 同名，可回 IG 公开页取官网）",
        "login": "回复、私信",
    },
    "whatsapp": {
        "name": "WhatsApp", "star": "⭐⭐⭐⭐", "stage": "转化/跟进主场（不是搜索源）",
        "tmpl": [
            '"{cat}" {role} "{region}" ("wa.me" OR "WhatsApp Business" OR "WhatsApp us")',
        ],
        "extract": "官网/目录页公开的 WhatsApp 商务号（只记录，不立即发；按第七步 WhatsApp 触发条件进 WA 名单）",
        "login": "所有发送动作都走 wa_bulk 引擎的人工确认 + 防封铁律",
    },
    "lemon8": {
        "name": "Lemon8", "star": "⭐⭐", "stage": "图文种草/新锐品牌",
        "tmpl": [
            'site:lemon8-app.com "{cat}" "{region}"',
        ],
        "extract": "帖子提到的品牌名/店铺名 → 回搜官网",
        "login": "评论、私信、关注",
    },
}
PLATFORM_ORDER = list(PLATFORMS.keys())


TAG_SUFFIXES = ("", "wholesale", "supplier", "b2b", "store", "brand", "design", "trade")


def tag_terms(cat, region=""):
    """品类词 → 9 组话题标签：#品类 / #品类wholesale / supplier / b2b / store / brand / design / trade / #地区品类"""
    base = "".join(ch for ch in cat.lower() if ch.isalnum())
    if not base:
        return []
    tags = [base + suf for suf in TAG_SUFFIXES]
    reg = "".join(ch for ch in (region or "").lower() if ch.isalnum())
    if reg:
        tags.append(reg + base)
    return tags


def titles_for(tier="all", profile_titles=None):
    """profile 的 buyer_titles 优先；词库补位。tier=decision/execution/influence/all"""
    lib = []
    tiers = TIER_CN.keys() if tier in ("", "all", None) else [tier]
    for t in tiers:
        lib += TITLE_TIERS.get(t, [])
    out, seen = [], set()
    for t in list(profile_titles or []) + lib:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t.strip())
    return out


def build(platforms, regions, cats, roles, titles, competitors, max_cats=3, max_roles=2, max_tags=9):
    """返回 [(platform_id, query)]，已去重。"""
    out, seen = [], set()
    cats = [c for c in cats if c][:max_cats] or [""]
    roles = [r for r in roles if r][:max_roles] or [""]
    t3_groups = []
    for i in range(0, min(len(titles), 9), 3):
        grp = titles[i:i + 3]
        if grp:
            t3_groups.append(" OR ".join(f'"{t}"' for t in grp))
    t3_groups = t3_groups or ['"Buyer" OR "Purchasing Manager" OR "Owner"']
    for pid in platforms:
        spec = PLATFORMS.get(pid)
        if not spec:
            continue
        for tmpl in spec["tmpl"]:
            if "{competitor}" in tmpl:
                for comp in competitors[:6]:
                    out.append((pid, tmpl.format(competitor=comp)))
                continue
            for region in regions:
                for cat in cats:
                    tags = tag_terms(cat, region) if "{tag}" in tmpl else [""]
                    groups = t3_groups if "{t3}" in tmpl else [""]
                    rls = roles if "{role}" in tmpl else [""]
                    for tag in tags[:max_tags]:
                        for g in groups:
                            for role in rls:
                                out.append((pid, tmpl.format(cat=cat, role=role, region=region,
                                                             t3=g, tag=tag, competitor="")))
    uniq = []
    for pid, q in out:
        q = " ".join(q.split())
        if (pid, q) not in seen:
            seen.add((pid, q))
            uniq.append((pid, q))
    return uniq


def youtube_url(query):
    return PLATFORMS["youtube"]["url"].format(q=quote_plus(query.replace("site:youtube.com", "").strip()))
