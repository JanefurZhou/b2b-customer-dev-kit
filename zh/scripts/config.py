#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — 统一公司档案加载器 + 首次配置门禁（所有业务脚本共用）

设计原则
--------
1. 本技能是**通用脱敏模板**，不内置任何真实公司名、产品、联系方式、关键词。
2. 所有业务信息都来自用户首次使用时填写的 `company_profile.json`。
3. 任何业务脚本在干活前都必须先 `load_profile(require_complete=True)`：
   - 没建档 / 有必填项没填 → 抛 `ProfileNotConfigured`，脚本立即停止，
     并打印"先跑 onboarding.py / 让 AI 带你建档"的明确指引。
4. 发信凭证（SMTP/IMAP 密码等）属于密钥，**不放进** profile，仍走环境变量。

路径解析：profile 默认放在技能根目录的 `config/company_profile.json`，
也可用环境变量 B2B_PROFILE 覆盖。纯标准库，无第三方依赖。
"""

import os
import re
import json
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---- profile 位置（基于本文件解析，不硬编码绝对路径）----
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_HERE)
DEFAULT_PROFILE = os.path.join(_SKILL_ROOT, "config", "company_profile.json")


def profile_path():
    return os.environ.get("B2B_PROFILE") or DEFAULT_PROFILE


class ProfileNotConfigured(RuntimeError):
    """档案不存在或必填项未完成。业务脚本捕获后应停止并引导建档。"""""


# 必填字段：键路径 -> 人类可读名称（首次建档必须拿到）
REQUIRED = {
    "business.industry": "所属行业/赛道（一句话，如\"工业阀门出口\"\"HR SaaS\"\"跨境物流\"）",
    "business.offer_type": "交付形态（physical_product / software / service / project / other）",
    "company.brand_display": "公司/品牌展示名（邮件落款用）",
    "contact.founder_name": "对外联系人姓名",
    "contact.email": "对外发件邮箱",
    "product.one_liner_en": "一句话产品/服务定位（英文）",
    "product.primary_keywords": "客户搜索你这类产品/服务时用的核心关键词（至少 3 个）",
    "product.differentiators": "差异化卖点（至少 2 条）",
    "targeting.buyer_titles": "目标客户决策角色（至少 1 个）",
    "data_sources.customer_db": "自有客户库（imported=已用 data_import.py 导入 / crm_sync=从 CRM 导出导入 / none=暂无，从零开发）",
}

# 自有客户库声明的允许取值（本技能不自带任何客户数据库，安装时由用户自己声明并导入）
CUSTOMER_DB_STATES = ("imported", "crm_sync", "none")
MAIL_ROUTES = ("smtp_env", "mailboxes", "mcp", "not_yet")


def _get_path(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _is_empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def load_profile(require_complete=True):
    """加载并（默认）校验公司档案。

    require_complete=True 时，档案缺失或必填项为空会抛 ProfileNotConfigured。
    require_complete=False 时返回原始 dict（可能为空模板），供工具/检查使用。
    """
    path = profile_path()
    if not os.path.exists(path):
        if require_complete:
            raise ProfileNotConfigured(
                "尚未找到公司档案 company_profile.json。\n"
                "这是一个通用模板技能，第一次使用必须先完成建档。\n"
                "请运行：python3 scripts/onboarding.py init  生成空白档案，"
                "或让 AI 按 SKILL.md 的『首次建档门禁』引导你逐项填写后，再执行本任务。"
            )
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ProfileNotConfigured(f"公司档案无法解析：{e}。请重新运行 onboarding.py init。")

    if require_complete and not data.get("configured"):
        raise ProfileNotConfigured(not_ready_message(data))
    if require_complete and data.get("confirmed_fingerprint") != confirm_fingerprint(data):
        raise ProfileNotConfigured(
            "公司档案或灵魂七件套在用户确认之后被修改过（内容指纹不一致），禁止执行业务任务。\n"
            "请运行 python3 scripts/onboarding.py check，把改动回读给用户，"
            "用户明确回复『确认无误』后再运行 python3 scripts/onboarding.py attest。")
    return data


_VOLATILE_KEYS = ("user_confirmed", "configured", "confirmed_at", "confirmed_fingerprint", "filled_at")


def confirm_fingerprint(data, kit_dir=None):
    """档案（去掉确认相关字段）+ 七件套全文 的 sha256。attest 时写入，确认后任何改动都会让它失配。"""
    import hashlib
    h = hashlib.sha256()
    core = {k: v for k, v in (data or {}).items() if k not in _VOLATILE_KEYS}
    h.update(json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    kit_dir = kit_dir or os.path.join(_SKILL_ROOT, "soul_seven_kit")
    for name in _KIT_FILES:
        fp = os.path.join(kit_dir, name)
        h.update(name.encode())
        if os.path.exists(fp):
            with open(fp, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


_KIT_FILES = ["IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md",
              "MEMORY.md", "USER.md", "HEARTBEAT.md"]


# 灵魂七件套内容体检（规则来自 soul-seven-kit：缺件 / 空壳 / 未替换示例 / 缺关键段）
KIT_REQUIRED_KEYWORDS = {
    "IDENTITY.md": ("岗位", "服务对象", "红线"),
    "SOUL.md": ("语气", "优先级", "决策"),
    "AGENTS.md": ("SOP", "人工确认", "禁"),
    "TOOLS.md": ("何时用", "怎么用", "坏了"),
    "MEMORY.md": ("结论", "待办", "下一步"),
    "USER.md": ("汇报", "审批", "敏感"),
    "HEARTBEAT.md": ("运行", "完成率", "错误"),
}
KIT_MIN_SUBSTANTIVE = 3   # 每份至少 3 条「真内容」（每份三五条即可）


def _kit_body(text):
    text = re.sub(r"(?s)\A---.*?---\s*", "", text, count=1)      # frontmatter
    return re.sub(r"(?s)<!--.*?-->", "", text)                   # HTML 注释


def _substantive(line):
    t = line.strip()
    if not t or t.startswith("#") or t.startswith("_最后更新"):
        return False
    t = re.sub(r"^(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)、]\s*)", "", t).strip()
    if not t or t.startswith("（例") or t.startswith("(例"):
        return False
    # 只有标签、冒号后为空（如「- 时间：」「完成率：/ （实发 / 计划）」）不算内容
    if re.fullmatch(r"[^：:]{0,20}[：:]\s*(?:/\s*)?(?:（[^）]*）)?\s*", t):
        return False
    return len(t) >= 4


def kit_health(kit_dir=None):
    """返回 {文件名: [问题…]}；空列表 = 这份通过。纯只读。"""
    kit_dir = kit_dir or os.path.join(_SKILL_ROOT, "soul_seven_kit")
    out = {}
    for name in _KIT_FILES:
        fp = os.path.join(kit_dir, name)
        probs = []
        if not os.path.exists(fp):
            out[name] = ["缺件：文件不存在（先运行 onboarding.py init）"]
            continue
        with open(fp, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        m = re.search(r"(?im)^\s*filled\s*:\s*(true|false)\s*$", text[:400])
        if not (m and m.group(1).lower() == "true"):
            probs.append("顶部 filled 不是 true")
        body = _kit_body(text)
        lines = body.splitlines()
        n_sub = sum(1 for ln in lines if _substantive(ln))
        if n_sub < KIT_MIN_SUBSTANTIVE:
            probs.append(f"空壳：真内容只有 {n_sub} 条（至少 {KIT_MIN_SUBSTANTIVE} 条）")
        left = [ln.strip() for ln in lines if re.match(r"^\s*(?:[-*]\s*)?[（(]例", ln)]
        if left:
            probs.append(f"还有 {len(left)} 行「（例…）」示例未替换成你的真实情况")
        ph = find_placeholder_text(body)
        if ph:
            probs.append("残留占位符：" + ", ".join(ph[:5]))
        miss = [k for k in KIT_REQUIRED_KEYWORDS.get(name, ()) if k not in body]
        if miss:
            probs.append("缺关键段：" + " / ".join(miss))
        out[name] = probs
    return out


def unfilled_kit_files():
    """返回灵魂七件套中未通过内容体检的文件名列表（目录不存在视为全部未填）。"""
    return [n for n, probs in kit_health().items() if probs]


def not_ready_message(data):
    """按建档三道关（必填项 → 灵魂七件套 → 用户确认）给出当前真正卡住的那一步。"""
    head = "公司档案尚未就绪（configured != true），禁止执行业务任务。\n"
    missing = missing_fields(data)
    if missing:
        return (head + "卡在第 1 步：company_profile.json 还缺以下必填项：\n" +
                "\n".join(f"  - {label}（{key}）" for key, label in missing) +
                "\n请让 AI 按 SKILL.md『首次建档门禁』逐项补齐，然后运行 "
                "python3 scripts/onboarding.py check。")
    unfilled = unfilled_kit_files()
    if unfilled:
        health = kit_health()
        return (head + "必填项已齐全；卡在第 2 步：灵魂七件套还有 "
                f"{len(unfilled)} 份未通过内容体检：\n" +
                "\n".join(f"  - soul_seven_kit/{n}：{'；'.join(health[n])}" for n in unfilled) +
                "\n如目录不存在，先运行 python3 scripts/onboarding.py init；"
                "填完后运行 python3 scripts/onboarding.py check。")
    if not data.get("user_confirmed"):
        return (head + "必填项与灵魂七件套均已就绪；卡在第 3 步：尚未经用户本人确认。\n"
                "请运行 python3 scripts/onboarding.py check，把档案原样回读给用户，"
                "用户明确回复『确认无误』后再运行 python3 scripts/onboarding.py attest。")
    return (head + "三项检查都已通过，但 configured 标记仍为 false。"
            "请运行 python3 scripts/onboarding.py attest 完成激活。")


OFFER_TYPES = ("physical_product", "software", "service", "project", "other")

# 模板占位符：<your-moq> / {intro} 这类文字一旦进入档案或外发邮件就是事故
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>@\n]{1,60}>|\{[A-Za-z_][A-Za-z0-9_.\[\]]{1,40}\}")
_PLACEHOLDER_SECTIONS = ("business", "company", "contact", "product", "offer")


def find_placeholder_text(text):
    """返回文本里残留的模板占位符列表（去重保序）。"""
    out = []
    for m in PLACEHOLDER_RE.findall(text or ""):
        if m not in out:
            out.append(m)
    return out


def find_placeholders(data):
    """扫描档案中对外会用到的段落，返回 [(dotted_path, placeholder), ...]。"""
    hits = []

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")
        elif isinstance(v, str):
            for ph in find_placeholder_text(v):
                hits.append((path, ph))
    for sec in _PLACEHOLDER_SECTIONS:
        walk((data or {}).get(sec, {}), sec)
    return hits


def missing_fields(data):
    """返回 [(key, label), ...] 所有空的必填项（offer_type 取值非法也算缺）。"""
    out = []
    for key, label in REQUIRED.items():
        v = _get_path(data, key)
        if _is_empty(v):
            out.append((key, label))
        elif key == "business.offer_type" and str(v).strip() not in OFFER_TYPES:
            out.append((key, label + f"——当前值「{v}」不在允许范围内"))
        elif key == "data_sources.customer_db" and str(v).strip() not in CUSTOMER_DB_STATES:
            out.append((key, label + f"——当前值「{v}」不在允许范围内"))
    for path, ph in find_placeholders(data):
        out.append((path, f"含未替换的模板占位符 {ph}（必须换成用户提供的真实值，或删除该项）"))
    return out


# ============================================================
# 行业包（方法层建议，不含任何公司事实）
# ============================================================
PACKS_FILE = os.path.join(_SKILL_ROOT, "references", "industry_packs.json")


def load_packs():
    """返回 {pack_id: pack_dict}；文件缺失返回空字典。"""
    try:
        with open(PACKS_FILE, encoding="utf-8-sig") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {p["id"]: p for p in doc.get("packs", []) if p.get("id")}


def active_pack(profile):
    """读取 profile.business.industry_pack 对应的行业包；未设置返回 None。"""
    pid = (get(profile or {}, "business.industry_pack", "") or "").strip()
    return load_packs().get(pid) if pid else None


# ============================================================
# 通用/职能邮箱前缀（全行业）：命中 = 非具名邮箱，只能 B 级入库或换决策人
# ============================================================
GENERIC_MAILBOX_PREFIXES = frozenset({
    # 通用收件
    "info", "contact", "hello", "hi", "mail", "email", "office", "general", "team",
    "enquiry", "enquiries", "inquiry", "inquiries", "reception", "admin", "webmaster",
    "noreply", "no-reply", "newsletter",
    # 销售/客服
    "sales", "support", "help", "service", "customercare", "customerservice", "orders",
    # 实体商品渠道
    "wholesale", "trade", "export", "import", "shop", "store",
    # 采购/合作/项目
    "purchasing", "procurement", "buying", "sourcing", "partners", "partnerships",
    "projects", "tenders", "bids", "vendors", "suppliers",
    # 职能部门
    "marketing", "press", "media", "pr", "hr", "careers", "jobs", "recruiting",
    "billing", "accounts", "finance", "invoices", "legal", "privacy", "compliance", "it",
})


# ============================================================
# 话术事实层：所有行业共用的「关键事实 + 收尾问句」
# ============================================================
NEUTRAL_CTA = "Is this worth a short reply?"


def offer_facts(profile, limit=3):
    """返回对外可用的短事实列表（只取用户建档填写的值，不推断）。

    优先 offer.key_facts（任何行业通用，如 "MOQ 50 pcs" / "setup in 2 days" /
    "ISO 13485 certified"）；未填时兼容旧字段 product.moq / sample_lead_time /
    bulk_lead_time（实体商品场景）。"""
    facts = [str(x).strip() for x in (get(profile, "offer.key_facts", []) or []) if str(x).strip()]
    facts = [f[0].upper() + f[1:] for f in facts]
    if not facts:
        p = (profile or {}).get("product", {}) or {}
        if (p.get("moq") or "").strip():
            facts.append(f"MOQ {p['moq'].strip()}")
        if (p.get("sample_lead_time") or "").strip():
            facts.append(f"Samples in {p['sample_lead_time'].strip()}")
        if (p.get("bulk_lead_time") or "").strip():
            facts.append(f"Production in {p['bulk_lead_time'].strip()}")
    return facts[:limit]


def cta_question(profile):
    """收尾问句：offer.cta_question（用户确认过）> 由 offer.entry_offer 组装 > 中性兜底。"""
    q = (get(profile, "offer.cta_question", "") or "").strip()
    if q:
        return q if q.endswith("?") else q.rstrip(".") + "?"
    entry = (get(profile, "offer.entry_offer", "") or "").strip()
    if entry:
        return f"Worth a {entry}?" if not entry.lower().startswith(("a ", "an ", "the ")) else f"Worth {entry}?"
    return NEUTRAL_CTA


# ============================================================
# 决策驱动标签（solution_tag / hook_type）——行业通用的 11 个取值
# ============================================================
DRIVER_TAGS = ("compliance", "sustainability", "quality_upgrade", "cost", "speed",
               "low_commitment", "innovation", "exclusive_custom", "one_stop",
               "dedicated_service", "strategic_scale", "open", "unknown")
# 旧版（v1.x）标签自动映射到新取值，避免历史数据失效
LEGACY_TAG_ALIASES = {
    "eco_only": "compliance", "regulated": "compliance", "eco_prefer": "sustainability",
    "traditional": "quality_upgrade", "category_only": "open", "low_moq": "low_commitment",
    "upgrade_opportunity": "quality_upgrade", "exclusive_design": "exclusive_custom",
    "strategic_partner": "strategic_scale", "seasonal": "speed", "category_expand": "one_stop",
}


def normalize_driver(tag):
    t = (tag or "").strip().lower()
    t = LEGACY_TAG_ALIASES.get(t, t)
    return t if t in DRIVER_TAGS else "unknown"


def get(profile, dotted, default=None):
    """安全读取 profile 中的点分路径。"""
    v = _get_path(profile, dotted)
    return default if _is_empty(v) else v


if __name__ == "__main__":
    # 自检入口：python3 config.py
    try:
        p = load_profile(require_complete=True)
        print("OK 档案已就绪：", get(p, "company.brand_display"))
    except ProfileNotConfigured as e:
        print("NOT_CONFIGURED")
        print(e)
        sys.exit(2)
