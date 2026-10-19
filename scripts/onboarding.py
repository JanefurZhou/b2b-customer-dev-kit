#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
onboarding.py — 通用 B2B 客户开发技能的「首次建档」工具

子命令
------
  start       新装必做清单：一屏列出「装好后马上要补的信息」及每项当前状态（只读）
  init        生成空白 config/company_profile.json + soul_seven_kit/（不覆盖已有文件）
  check       校验档案必填项 + 灵魂七件套内容体检 + 用户确认，三道关逐一报告
  kit-check   只做灵魂七件套内容体检（缺件 / 空壳 / 未替换示例 / 缺关键段 / 占位符）
  ask         交互式采访：逐项询问必填项并写入（也可只补缺失项）
  attest      用户本人明确确认后激活档案（configured=true）
  packs       列出内置行业包（方法层建议：分层/角色/渠道/意图词）
  pack <id>   查看某个行业包的全部建议
  apply-pack <id>  把行业包建议写进档案中【仍为空】的方法层字段（不碰公司事实），
                   并把 user_confirmed 重置为 false，需重新回读确认

重要：本脚本只负责"建档/校验"。它不编造任何公司信息——
所有字段都必须由使用者提供。AI 第一次加载本技能时，
应按 SKILL.md 顶部『首次建档门禁』引导用户填这份档案，
check 通过之前，任何搜索/发信/补池脚本都会被 config.py 拒绝。

纯标准库，无第三方依赖。
"""

import os
import re
import sys
import json
import datetime

try:
    import config as _cfg
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import config as _cfg

# ---- 灵魂七件套：模板目录 → 首次建档实例目录 ----
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_TEMPLATE_DIR = os.path.join(_SKILL_ROOT, "references", "soul_kit")
KIT_INSTANCE_DIR = os.path.join(_SKILL_ROOT, "soul_seven_kit")
KIT_FILES = ["IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md",
             "MEMORY.md", "USER.md", "HEARTBEAT.md"]


def blank_profile():
    """空白档案模板：所有业务字段留空，由使用者首次填写。"""
    return {
        "schema_version": 1,
        "configured": False,
        "user_confirmed": False,
        "confirmed_at": "",
        "filled_at": "",
        "business": {
            "industry": "",             # 必填：一句话行业/赛道，如 "industrial valves export" / "HR SaaS"
            "offer_type": "",           # 必填：physical_product / software / service / project / other
            "industry_pack": "",        # 选填：references/industry_packs.json 中的包 id
            "sales_motion": "",         # 选填：export / domestic / both
            "deal_size": "",            # 选填：典型单笔成交规模（只写事实）
            "sales_cycle": ""           # 选填：典型成交周期
        },
        "company": {
            "brand_display": "",        # 邮件落款公司/品牌名
            "legal_entity": "",         # 选填：法定公司名
            "website": "",              # 选填：主站
            "product_site": "",         # 选填：产品站（若与主站不同）
            "headquarters_country": ""  # 选填：公司所在国
        },
        "contact": {
            "founder_name": "",         # 对外联系人姓名（必填）
            "founder_title": "",        # 选填：头衔
            "email": "",                # 发件邮箱（必填）
            "whatsapp": "",             # 选填：WhatsApp 国际格式
            "signature_lines": []       # 选填：自定义签名附加行，留空用默认
        },
        "product": {                    # 「product」泛指你卖的东西：产品 / 软件 / 服务 / 项目能力
            "one_liner_en": "",         # 一句话产品/服务定位（英文，必填）
            "one_liner_local": "",      # 选填：其他语言版本
            "primary_keywords": [],     # 客户搜你时用的核心词（≥3，必填），如 ["<your-core-offer>"]
            "alt_keywords": [],         # 近义词/品类扩展词
            "differentiators": [],      # 差异化卖点（≥2，必填，须可验证）
            "moq": "",                  # 选填（实体商品）：起订量，如 "50 pcs"
            "sample_lead_time": "",     # 选填（实体商品）：打样周期
            "bulk_lead_time": ""        # 选填（实体商品）：大货周期
        },
        "offer": {                      # 行业通用的「成交入口」层，邮件/WhatsApp 都从这里取
            "entry_offer": "",          # 低门槛起步方式：free sample / 14-day trial / free audit / pilot / site visit
            "cta_question": "",         # 邮件收尾问句（英文），如 "Open to a 20-minute demo next week?"
            "key_facts": [],            # 2–4 条可对外的短事实：MOQ / 上线周期 / 认证 / 交付时效 / 客户数
            "min_commitment": "",       # 最低起步门槛：MOQ / 最低合同额 / 最短订阅期
            "delivery_time": "",        # 交付/上线/实施周期
            "proof_points": [],         # 可公开的案例或数据（须授权或已脱敏）
            "repeat_hook": ""           # 老客户复购跟进的一句话（如 "our 2027 range is ready"）
        },
        "positioning": {                # 背调标签的业务化定义（可选）
            "need_tags": [],            # 你的产品/服务线标签，如 ["line_a","line_b"]；need_tag 取值集合
            "conflict_groups": {},      # 互斥标签组：{"need_tag": [["a"],["b"]]}，conflict-check 用
            "tag_rules": [],            # 库内自洽规则：[{"if_field":"variant_tag","equals":"x",
                                        #   "forbid_field":"need_tag","values":["y"],"reason":"..."}]
            "hooks": {}                 # 按决策驱动覆盖开场句：{"cost": "...{one}...{lead}..."}
        },
        "targeting": {
            "customer_industries": [],  # 客户自己所在的行业（软件/服务强烈建议填），如 ["logistics","manufacturing"]
            "buyer_titles": [],         # 决策角色（≥1，必填），如 ["procurement manager"] / ["CTO"] / ["HR director"]
            "channel_keywords": [],     # 客户类型/渠道词，如 distributor / contractor / startup / clinic chain
            "customer_levels": [        # 用户自定义客户分层（搜索脚本据此生成词表）
                # 示例占位（可改/可增删）：
                # {"name": "L1_core", "desc": "", "keyword_suffixes": ["<customer-type-1>","<customer-type-2>"]}
            ],
            "target_regions": [],       # 目标市场，如 ["USA","UK","DE"]
            "languages": [],            # 发信语言，如 ["en","fr","de"]
            "exclude_keywords": [],     # 非目标排除词（行业无关，用户自填）
            "competitor_markers": [],   # 同行/竞品排除"特征词"（命中即拦截，如 manufacturer / agency）
            "reference_brands": [],     # 参照/竞品"品牌名"（供"竞品逆向"渠道搜它们的客户/经销商，不拦截）
        },
        "search": {                     # 侧翼搜索轴（可选；apply-pack 可预填意图词/站点词）
            "query_anchor": "auto",     # auto / offer（按你的品类词搜）/ customer（按客户行业词搜）
            "scene_terms": [], "intent_terms": [], "channel_site_terms": [],
            "niche_terms": [], "cert_terms": [], "channels": [],
            "social_platforms": []       # 空 = 10 个平台全开（只做免登录公开搜索）；可填 linkedin/instagram/...
        },
        "rules": {                      # 发信与风控规则（给默认值，可改）
            "daily_limit": 200,
            "local_send_window": "09:00-11:00,14:00-16:00",   # 收件人当地工作日窗口，send_window.py 强制
            "same_contact_cooldown_hours": 24,
            "require_confirmed_email": True,
            "opt_out_line": "",          # 正文退订提示；空 = 用默认英文句，"off" = 不加
            "notes": ""                 # 自定义红线
        },
        "data_sources": {               # 数据接入层：本技能不自带客户数据库，安装时由用户声明
            "customer_db": "",          # 必填：imported / crm_sync / none
            "customer_db_files": [],    # 选填：已导入的文件名（data_import.py 自动记 import_log.csv）
            "saas_sources": [],         # 选填：在用的外贸 SaaS / 海关数据平台名（只记名字，导出走 data_import）
            "mail_route": "",           # 建议：smtp_env（单邮箱密钥）/ mailboxes（多邮箱托管）/ mcp（连接器）/ not_yet
            "mail_provider": "",        # 建议：tencent_exmail / aliyun_qiye / netease_qiye / gmail / microsoft365 / custom
            "crm": "",                  # 选填：hubspot / salesforce / okki / fumeng / other / none
            "crm_route": ""             # 选填：csv / api / mcp
        },
        "credentials_note": "SMTP/IMAP 密码等密钥不要写在这里，运行时通过环境变量提供："
                            "SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/IMAP_*；多邮箱托管只在 config/mailboxes.json 里记变量名"
    }


def scaffold_seven_kit():
    """把灵魂七件套模板复制成可填写实例（不覆盖已存在文件）。返回 (新建数, 已存在数)。"""
    os.makedirs(KIT_INSTANCE_DIR, exist_ok=True)
    created, existed = 0, 0
    for name in KIT_FILES:
        src = os.path.join(KIT_TEMPLATE_DIR, name)
        dst = os.path.join(KIT_INSTANCE_DIR, name)
        if os.path.exists(dst):
            existed += 1
            continue
        with open(src, "rb") as f:
            content = f.read()
        with open(dst, "wb") as f:
            f.write(content)
        created += 1
    return created, existed


def _kit_filled_map():
    """返回 {文件名: bool 是否已填}。文件不存在视为未填。"""
    out = {}
    for name in KIT_FILES:
        p = os.path.join(KIT_INSTANCE_DIR, name)
        filled = False
        if os.path.exists(p):
            head = open(p, encoding="utf-8", errors="replace").read(400)
            # 仅认可 frontmatter 中 filled: true
            m = re.search(r"(?im)^\s*filled\s*:\s*(true|false)\s*$", head)
            filled = bool(m and m.group(1).lower() == "true")
        out[name] = filled
    return out


def cmd_kit_check():
    health = _cfg.kit_health()
    bad = 0
    for name, probs in health.items():
        if probs:
            bad += 1
            print(f"  ✖ {name}：{'；'.join(probs)}")
        else:
            print(f"  ✔ {name}")
    print(f"灵魂七件套体检：{7 - bad}/7 通过。" + ("" if not bad else
          " 参考写法：references/soul_kit/填写参考_客户开发岗.md"))
    sys.exit(1 if bad else 0)


def cmd_start():
    """新装必做清单（只读）：把「装好后马上要补的信息」一次列清，并给出每项当前状态。"""
    path = _cfg.profile_path()
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    missing = dict(_cfg.missing_fields(data)) if data else None
    health = _cfg.kit_health()
    g = lambda k: _cfg.get(data, k, None) if data else None
    mark = lambda ok: "✔" if ok else "✖"
    print("新装必做清单（B2B 客户开发 · 全行业通用版）")
    print("=" * 60)
    print("第 1 关 · 公司档案必填（config/company_profile.json）——不填齐，所有搜索/发信脚本拒绝运行")
    if missing is None:
        print("  ✖ 档案不存在 → 先运行 python3 scripts/onboarding.py init")
    else:
        for key, label in _cfg.REQUIRED.items():
            print(f"  {mark(key not in missing)} {label}  [{key}]")
    print("第 2 关 · 灵魂七件套（soul_seven_kit/）——AI 的身份、刹车、老板偏好、工作笔记")
    for name, probs in health.items():
        print(f"  {mark(not probs)} {name}" + ("" if not probs else f"：{'；'.join(probs)}"))
    print("第 3 关 · 用户本人确认（AI 回读全部内容 → 你回复「确认无误」→ attest）")
    fp_ok = bool(data) and data.get("confirmed_fingerprint") == _cfg.confirm_fingerprint(data)
    print(f"  {mark(bool(data.get('user_confirmed')) and fp_ok)} user_confirmed"
          + ("" if fp_ok or not data.get("user_confirmed") else "（确认后档案/七件套被改过，需重新 attest）"))
    print("-" * 60)
    print("建议马上补（不拦截，但直接影响效果）")
    rec = [
        ("targeting.target_regions", "目标市场（决定搜索地区与发信时区）"),
        ("targeting.buyer_titles", "采购链职位（决策层/执行层/影响层，见 search_customers.py social --titles）"),
        ("targeting.reference_brands", "参照/竞品品牌（用于竞品逆向与社媒公开搜索）"),
        ("offer.key_facts", "可验证的短事实（邮件证据，S1 级来源）"),
        ("offer.entry_offer", "低门槛首单/试用/样品方案"),
        ("rules.local_send_window", "收件人当地发信窗口（默认 09:00-11:00,14:00-16:00）"),
        ("search.social_platforms", "要用的社媒平台（默认 10 个全开，只做免登录公开搜索）"),
    ]
    for key, label in rec:
        v = g(key)
        print(f"  {mark(not _cfg._is_empty(v))} {label}  [{key}]")
    print("-" * 60)
    print("数据接入层（装好马上配；路径都在本技能里，不用另找教程）")
    db_state = g("data_sources.customer_db") or ""
    db_file = os.path.join(os.environ.get("B2B_DATA_DIR", "data"), "customer_db.csv")
    print(f"  {mark(db_state in _cfg.CUSTOMER_DB_STATES)} 自有客户库 [data_sources.customer_db]＝{db_state or '未声明'}"
          + ("" if db_state != "imported" or os.path.exists(db_file) else f"（声明已导入，但 {db_file} 不存在）"))
    print("      导入：python3 scripts/data_import.py inspect <Excel/CSV> → import --relation existing_customer|prospect --source own:excel")
    print("      SaaS/海关/CRM 导出同样走 data_import；对接说明 references/外贸SaaS对接指引.md")
    route = g("data_sources.mail_route") or ""
    env_ok = all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))
    try:
        import mail_setup as _ms
        n_mb = len(_ms.load_mailboxes()["mailboxes"])
    except Exception:
        n_mb = 0
    print(f"  {mark(route in ('smtp_env', 'mailboxes', 'mcp'))} 发信通道 [data_sources.mail_route]＝{route or '未选'}"
          f"｜SMTP 环境变量{'已设' if env_ok else '未设'}｜托管邮箱 {n_mb} 个")
    print("      企业邮箱密钥：python3 scripts/mail_setup.py providers → env <服务商> --user <邮箱> → test（只登录不发信）")
    print("      多邮箱托管+预热：mail_setup.py add <id> ...；MCP/连接器：references/mail_setup.md 路径 B")
    crm = g("data_sources.crm") or ""
    print(f"  {mark(bool(crm))} CRM 同步 [data_sources.crm]＝{crm or '未选'}"
          "｜python3 scripts/crm_sync.py export --target <hubspot|salesforce|okki|fumeng|generic>")
    print("  ·  数据触发口：python3 scripts/triggers.py scan（每天一次，挂定时任务见 automation_setup.md）")
    print("-" * 60)
    if missing is None:
        print("下一步：python3 scripts/onboarding.py init")
    elif missing:
        print("下一步：python3 scripts/onboarding.py ask（或让 AI 逐项问你），可先 packs / apply-pack <id> 套行业方法层")
    elif any(health.values()):
        print("下一步：按 references/soul_kit/填写参考_客户开发岗.md 填七件套 → onboarding.py kit-check")
    elif not data.get("user_confirmed") or not fp_ok:
        print("下一步：onboarding.py check → AI 回读 → 你确认 → onboarding.py attest")
    else:
        print("READY 三关全过。日常从 SKILL.md「第零步 全渠道复盘」开始。")


def cmd_init():
    path = _cfg.profile_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print(f"EXISTS 档案已存在，未覆盖：{path}")
        print("如需重新开始请先手动删除该文件。")
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blank_profile(), f, ensure_ascii=False, indent=2)
        print(f"CREATED 空白档案已生成：{path}")
    created, existed = scaffold_seven_kit()
    print(f"CREATED 灵魂七件套实例目录：{KIT_INSTANCE_DIR}（新建 {created} 份，已存在 {existed} 份，均不覆盖）")
    print("下一步：让 AI 按 SKILL.md『首次建档门禁』带你填 company_profile.json + 灵魂七件套，"
          "或运行 python3 scripts/onboarding.py ask；完成后运行 check。")


def cmd_check():
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED 档案不存在。先运行：python3 scripts/onboarding.py init")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    missing = _cfg.missing_fields(data)
    if missing:
        print(f"INCOMPLETE company_profile.json 还缺 {len(missing)} 个必填项：")
        for key, label in missing:
            print(f"  - {label}  [{key}]")
        sys.exit(1)

    # 灵魂七件套必须每份都通过内容体检（filled=true 只是自报，体检看真内容）
    health = _cfg.kit_health()
    unfilled = [name for name, probs in health.items() if probs]
    if unfilled:
        print(f"INCOMPLETE 灵魂七件套还有 {len(unfilled)} 份未通过内容体检：")
        for name in unfilled:
            print(f"  - {name}：{'；'.join(health[name])}")
        print("请让 AI 按 references/soul_kit/填写参考_客户开发岗.md 逐份引导填写（每份三五条，"
              "把「（例…）」换成你的真实做法），填完把顶部 filled 改成 true，再运行 check。")
        sys.exit(1)

    # 必填项 + 七件套都填了，只代表"内容已填"；还必须经用户本人确认，防 AI 自行编造。
    if not data.get("user_confirmed"):
        print("FILLED_NOT_CONFIRMED 必填项和灵魂七件套都已填写，但尚未经用户本人确认。")
        print("")
        print("下一步（AI 不得跳过、不得替用户确认）：")
        print("  1) 把 config/company_profile.json 全部关键信息和 soul_seven_kit/ 7 份内容")
        print("     原样回读给用户；任何联系方式、品牌名、产品事实必须来自用户原话/官网，")
        print("     不得由 AI 猜测或编造。")
        print("  2) 等用户明确回复『确认无误』后，才运行：")
        print("       python3 scripts/onboarding.py attest")
        print("  3) 用户未明确确认前，所有搜索/发信脚本仍会被门禁拦截。")
        sys.exit(3)

    if data.get("confirmed_fingerprint") != _cfg.confirm_fingerprint(data):
        print("CHANGED_AFTER_CONFIRM 档案或灵魂七件套在确认之后被修改过（内容指纹不一致）。")
        print("把改动回读给用户，用户明确回复『确认无误』后再运行 python3 scripts/onboarding.py attest。")
        sys.exit(3)

    print("READY 档案 + 灵魂七件套已就绪且经用户本人确认（user_confirmed=true）。可以开始搜索/发信。")
    biz = data.get("business", {})
    print("公司：", data["company"]["brand_display"], "| 行业：", biz.get("industry", ""),
          "| 形态：", biz.get("offer_type", ""), "| 行业包：", biz.get("industry_pack") or "未用",
          "| 定位：", data["product"]["one_liner_en"])
    _soft_warnings(data)


def _soft_warnings(data):
    """不拦截、只提醒：影响跨行业效果的选填项。"""
    biz, tg, of = data.get("business", {}), data.get("targeting", {}), data.get("offer", {})
    tips = []
    if biz.get("offer_type") in ("software", "service") and not tg.get("customer_industries"):
        tips.append("软件/服务业务建议填 targeting.customer_industries（客户所在行业），否则搜索容易搜到同行。")
    if not (of.get("entry_offer") or of.get("cta_question")):
        tips.append("offer.entry_offer / cta_question 都为空：邮件将用中性收尾问句，转化通常更低。")
    if not of.get("key_facts") and not (data.get("product", {}).get("moq")):
        tips.append("offer.key_facts 为空：邮件里没有可验证的短事实。")
    ds = data.get("data_sources", {})
    if ds.get("customer_db") in ("imported", "crm_sync"):
        dbf = os.path.join(os.environ.get("B2B_DATA_DIR", "data"), "customer_db.csv")
        if not os.path.exists(dbf):
            tips.append(f"已声明有自有客户库，但 {dbf} 还不存在：python3 scripts/data_import.py import <文件> "
                        "--relation existing_customer --source own:excel（老客户不会进冷开发池）。")
    if not ds.get("mail_route") or ds.get("mail_route") == "not_yet":
        tips.append("发信通道未配置：python3 scripts/mail_setup.py providers（企业邮箱密钥）或 references/mail_setup.md 路径 B（MCP）。")
    for t in tips:
        print("TIP " + t)


def cmd_attest():
    """用户本人确认无误后，由 AI 凭用户明确的确认回复调用，正式激活档案。"""
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED 档案不存在。先运行 init。")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    missing = _cfg.missing_fields(data)
    if missing:
        print(f"REFUSED 还有 {len(missing)} 个必填项未填，不能确认。先补全再 attest。")
        sys.exit(1)
    unfilled = _cfg.unfilled_kit_files()
    if unfilled:
        print("REFUSED 灵魂七件套未全部通过内容体检，不能确认：", ", ".join(unfilled),
              "（运行 onboarding.py kit-check 看原因）")
        sys.exit(1)
    data["user_confirmed"] = True
    data["configured"] = True
    today = datetime.date.today().isoformat()
    data["confirmed_at"] = today
    data.setdefault("filled_at", today)
    data["confirmed_fingerprint"] = _cfg.confirm_fingerprint(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("ACTIVATED 已记录用户本人确认，configured=true。技能正式可用。")
    print("NOTE 已记录档案 + 七件套的内容指纹：之后改动任何一处，脚本会要求重新回读确认再 attest。")


def _ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def _ask_list(prompt, min_n=0):
    print(f"{prompt}（逗号分隔，至少 {min_n} 个；直接回车结束）")
    while True:
        raw = input("> ").strip()
        items = [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]
        if len(items) >= min_n:
            return items
        print(f"  至少需要 {min_n} 个，请重新输入。")


def cmd_ask():
    path = _cfg.profile_path()
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = blank_profile()
        print("未发现档案，已载入空白模板。")
    else:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        print("已载入现有档案，按回车保留原值。")

    for k, v in blank_profile().items():           # 旧档案补齐新增的段落
        if isinstance(v, dict):
            data.setdefault(k, {})
            for kk, vv in v.items():
                data[k].setdefault(kk, vv)
    c, p_, t = data["company"], data["product"], data["targeting"]
    ct, b, o = data["contact"], data["business"], data["offer"]
    b["industry"] = _ask("所属行业/赛道（一句话）", b.get("industry", ""))
    while True:
        b["offer_type"] = _ask("交付形态 physical_product / software / service / project / other",
                               b.get("offer_type", ""))
        if b["offer_type"] in _cfg.OFFER_TYPES:
            break
        print("  请从以上 5 个取值中选一个。")
    c["brand_display"] = _ask("公司/品牌展示名", c["brand_display"])
    c["website"] = _ask("公司网站（选填，可留空）", c.get("website", ""))
    ct["founder_name"] = _ask("对外联系人姓名", ct.get("founder_name", ""))
    ct["email"] = _ask("对外发件邮箱", ct.get("email", ""))
    ct["whatsapp"] = _ask("WhatsApp（国际格式，选填）", ct.get("whatsapp", ""))
    p_["one_liner_en"] = _ask("一句话产品/服务定位（英文）", p_.get("one_liner_en", ""))
    if not p_.get("primary_keywords"):
        p_["primary_keywords"] = _ask_list("客户搜你这类产品/服务时用的核心关键词", min_n=3)
    if not p_.get("differentiators"):
        p_["differentiators"] = _ask_list("差异化卖点", min_n=2)
    if not t.get("buyer_titles"):
        t["buyer_titles"] = _ask_list("目标客户决策角色（如 procurement manager / CTO / HR director）", min_n=1)
    if b.get("offer_type") in ("software", "service") and not t.get("customer_industries"):
        t["customer_industries"] = _ask_list("你的客户自己在哪些行业？（软件/服务按客户行业找人，选填）", min_n=0)
    o["entry_offer"] = _ask("低门槛起步方式（选填：sample / trial / audit / pilot…）", o.get("entry_offer", ""))
    o["cta_question"] = _ask("邮件收尾问句（英文，选填）", o.get("cta_question", ""))
    if not o.get("key_facts"):
        o["key_facts"] = _ask_list("2–4 条可对外的短事实（MOQ/上线周期/认证/交付时效…，选填）", min_n=0)
    ds = data.setdefault("data_sources", {})
    print("—— 数据接入层：本技能不自带客户数据库，需要你声明自己的情况 ——")
    while True:
        ds["customer_db"] = _ask("自有客户库：imported（有 Excel/CSV，马上用 data_import.py 导入）"
                                 " / crm_sync（从 CRM 导出再导入）/ none（暂无，从零开发）",
                                 ds.get("customer_db", ""))
        if ds["customer_db"] in _cfg.CUSTOMER_DB_STATES:
            break
        print("  请从 imported / crm_sync / none 中选一个。")
    ds["mail_route"] = _ask("发信通道：smtp_env（企业邮箱+密钥）/ mailboxes（多邮箱托管预热）/ mcp（连接器）/ not_yet",
                            ds.get("mail_route", ""))
    if ds["mail_route"] in ("smtp_env", "mailboxes"):
        ds["mail_provider"] = _ask("邮箱服务商：tencent_exmail / aliyun_qiye / netease_qiye / gmail / microsoft365 / custom",
                                   ds.get("mail_provider", ""))
    ds["crm"] = _ask("CRM（选填）：hubspot / salesforce / okki / fumeng / other / none", ds.get("crm", ""))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSAVED 已写入 {path}")
    print("运行 python3 scripts/onboarding.py check 校验；填完七件套、回读给用户并获得明确确认后，"
          "运行 python3 scripts/onboarding.py attest 才会激活。")
    print("提示：分层(customer_levels)、排除词、目标市场等可直接编辑 JSON 补全，但改完需重新让用户确认。")


# ---------------- 行业包 ----------------
# 只写入「方法层」字段；公司事实（品牌、联系人、关键词、卖点、offer.*）永远不由行业包填写。
_PACK_TARGETS = [
    ("targeting.buyer_titles", "buyer_titles"),
    ("targeting.channel_keywords", "channel_keywords"),
    ("targeting.customer_levels", "customer_levels"),
    ("targeting.exclude_keywords", "exclude_keyword_examples"),
    ("search.intent_terms", "intent_terms"),
    ("search.channel_site_terms", "channel_site_terms"),
    ("search.channels", "recommended_channels"),
]


def _set_path(d, dotted, value):
    cur = d
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _no_placeholder(v):
    """去掉含 <占位符> 的建议值，避免把模板文字写进档案。"""
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                x = dict(x)
                x["keyword_suffixes"] = [w for w in x.get("keyword_suffixes", []) if "<" not in str(w)]
                if x["keyword_suffixes"]:
                    out.append(x)
            elif "<" not in str(x):
                out.append(x)
        return out
    return v


def cmd_packs():
    packs = _cfg.load_packs()
    print(f"内置行业包 {len(packs)} 个（方法层建议，不含任何公司事实）：")
    for pid, p in packs.items():
        print(f"  {pid:<24} {p.get('name','')}  [{p.get('offer_type','')}]")
        print(f"  {'':<24} 适用：{p.get('suits','')}")
    print("\n查看：python3 scripts/onboarding.py pack <id>    应用：python3 scripts/onboarding.py apply-pack <id>")


def cmd_pack(pid):
    p = _cfg.load_packs().get(pid)
    if not p:
        print(f"UNKNOWN 没有行业包「{pid}」。运行 packs 查看全部。")
        sys.exit(1)
    print(json.dumps(p, ensure_ascii=False, indent=2))


def cmd_apply_pack(pid):
    p = _cfg.load_packs().get(pid)
    if not p:
        print(f"UNKNOWN 没有行业包「{pid}」。运行 packs 查看全部。")
        sys.exit(1)
    path = _cfg.profile_path()
    if not os.path.exists(path):
        print("NOT_CONFIGURED 档案不存在。先运行 init。")
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    filled, kept = [], []
    for dotted, key in _PACK_TARGETS:
        val = _no_placeholder(p.get(key))
        if not val:
            continue
        if _cfg._is_empty(_cfg._get_path(data, dotted)):
            _set_path(data, dotted, val)
            filled.append(dotted)
        else:
            kept.append(dotted)
    biz = data.setdefault("business", {})
    biz["industry_pack"] = pid
    if not (biz.get("offer_type") or "").strip():
        biz["offer_type"] = p.get("offer_type", "")
        filled.append("business.offer_type")
    # 任何改动都要重新经用户确认
    data["user_confirmed"] = False
    data["configured"] = False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"APPLIED 行业包 {pid}（{p.get('name','')}）")
    print("  已写入（原为空）：" + (", ".join(filled) or "无"))
    print("  已保留你的原值：" + (", ".join(kept) or "无"))
    print("  参考但不自动写入（属于公司事实，需用户亲口提供）：entry_offer / cta / key_facts / competitor_markers")
    for k in ("entry_offer_examples", "cta_examples", "key_fact_examples", "competitor_marker_examples"):
        if p.get(k):
            print(f"    - {k}: {', '.join(p[k])}")
    if p.get("compliance_notes"):
        print(f"  合规提示：{p['compliance_notes']}")
    print("NEXT user_confirmed 已重置为 false：把写入内容回读给用户，逐项改成贴合他业务的说法，"
          "确认后再 attest。")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd == "packs":
        return cmd_packs()
    if cmd in ("pack", "apply-pack"):
        if not arg:
            print(f"用法: python3 onboarding.py {cmd} <pack_id>（先运行 packs 查看）")
            sys.exit(1)
        return cmd_pack(arg) if cmd == "pack" else cmd_apply_pack(arg)
    if cmd == "start":
        return cmd_start()
    if cmd == "kit-check":
        return cmd_kit_check()
    if cmd == "init":
        cmd_init()
    elif cmd == "check":
        cmd_check()
    elif cmd == "ask":
        cmd_ask()
    elif cmd == "attest":
        cmd_attest()
    else:
        print(__doc__)
        print("用法: python3 onboarding.py [start|init|check|kit-check|ask|attest|packs|pack <id>|apply-pack <id>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
