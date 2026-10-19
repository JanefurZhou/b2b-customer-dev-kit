# B2B客户开发标准作业流程（SOP）

**版本**：v3.1 | **更新日期**：2026-10-19  
**适用范围**：所有B2B外贸冷邮件客户开发任务

---

## 📋 总览：安装门禁 + 第零步 + 七步法主流程（v3.1）

> 安装后第一件事：`python3 scripts/onboarding.py start`（新装必做清单）→ 三关全过（公司档案必填 → 灵魂七件套体检 7/7 → 用户本人确认 attest）才进入下面的流程。
> 每一步的「出口 / 回路」见 `references/sop_flowchart.md` 的闭环核对表——没有出口的步骤视为未完成。

```
安装门禁（start → init → 档案必填 → kit-check 7/7 → check → attest = READY）
  ↓
第零步 全渠道复盘 ─→ 第一步 搜索候选 ─→ 第二步 背景调查 ─→ 第三步 需求定位 ─→ 第四步 撰写内容
 success_cases      queries/channels   research_guide      need_tag +           email_templates
 wa_review          social · filter    S1/S2/S3            solution_tag         只引用 S1/S2
 MEMORY 本周结论     funnel             只有 S3→need_review  conflict-check
  ↑                                                                               ↓
第八步 成单复盘 + 七件套写回 ←─ 第七步 WhatsApp 触发 ←─ 第六步 跟进管理 ←─ 第五步 发送执行
 add_success → review_success   convert→validate→preview   imap_scanner(DRY_RUN)   三道关 → DRY_RUN
 周复盘写回 → kit-check          →harness→send→audit        cooldown · 1-3-7-21     → 用户批准
 → 回到第零步                    200 条/天 STOP             退信/回复/成交/无回复     → 当地窗口内发
```

---

## 🔄 详细SOP（含决策逻辑）

### 第零步：全渠道复盘（成功案例 + WA 复盘 + 七件套本周结论，每次启动开发前必做）

> v3.0：每周复盘同时做「七件套写回」——本周的错写回对应档案（`references/soul_kit/周复盘写回.md`），再跑 `onboarding.py kit-check`。复盘结论写进 `soul_seven_kit/MEMORY.md`，运行数据写进 `HEARTBEAT.md`。

**输入**：success_cases.csv  
**输出**：成功要点提炼 + 本轮开发策略参考

**⚠️ 核心原则：痛点分析必须由用户确认后才生效，AI只做初步分析建议，不做最终判定。**

```python
# 伪代码逻辑
review = csv_ops.review_success()

IF review.total_cases == 0:
    PRINT "暂无成功案例，正常启动开发流程"
ELSE:
    # === 痛点确认状态检查 ===
    pending_cases = [c for c in review.cases if not c.confirmed]
    
    IF pending_cases:
        # 有未确认的痛点 → 必须先反馈给用户确认
        PRINT "⚠️ 以下案例的痛点分析待您确认："
        FOR case IN pending_cases:
            # AI列出候选痛点供用户选择，不自动判定
            PRINT f"""
品牌: {case.brand}
客户: {case.contact} ({case.region})
AI初步分析可能是以下痛点之一：
  1. 合规/资质要求（客户提到 certification / compliance）→ compliance
  2. 需要更快交付/上线（客户提到 urgent / deadline / go-live）→ speed
  3. 需要定制方案（客户提到 custom / tailored / exclusive）→ exclusive_custom
请确认是哪个痛点？（回复数字或补充说明）
"""
        # ⏸️ 暂停等待用户确认
        # 用户确认后 → 才把用户确认过的痛点写入 success_cases.csv 的 success_points 字段
        # csv_ops.py add_success <email> <brand> <contact> <amount> "<confirmed_points>" --hook_type <solution_tag>
        WAIT_FOR_USER_CONFIRMATION()
    
    # === 按目标市场筛选相关案例 ===
    relevant = [c for c in review.cases if c.region == target_region AND c.confirmed]
    
    IF relevant:
        # 有同地区已确认案例 → 复制打法
        best_hook = most_common_hook(relevant)
        best_language = most_common_language(relevant)
        best_channel = most_common_channel(relevant)  # ⭐ 最有效获客渠道
        PRINT f"同地区成功案例{len(relevant)}个（已确认），最有效钩子: {best_hook}"
        PRINT f"最有效获客渠道: {best_channel} ({count_by_channel(relevant, best_channel)}单)"
    ELSE:
        # 无同地区案例 → 参考全局最佳（仅使用已确认的案例）
        confirmed_cases = [c for c in review.cases if c.confirmed]
        IF confirmed_cases:
            best_hook = review.top_patterns[0]
            best_channel = review.by_source_channel[0]  # ⭐ 全局最有效渠道
            PRINT f"无同地区案例，全局最佳钩子: {best_hook}"
            PRINT f"全局最有效获客渠道: {best_channel}"
        ELSE:
            PRINT "无已确认的成功案例，使用通用策略启动开发"
    
    # === 提炼的要点必须应用到本轮开发中 ===
    success_patterns = extract_patterns(confirmed_cases)
    FOR candidate in new_candidates:
        candidate.apply_lessons(success_patterns)
```

**痛点确认流程详解**：

```
客户回复/下单 → 检测成功事件
    ↓
AI初步分析可能解决的痛点（列出3-5个候选项）
    ↓
反馈给用户确认：
  "这个客户回复了，我分析可能是以下痛点之一：
   1. 合规/资质要求（客户提到 certification / compliance）→ compliance
   2. 需要更快交付/上线（客户提到 urgent / deadline / go-live）→ speed
   3. 需要定制方案（客户提到 custom / tailored / exclusive）→ exclusive_custom
   请确认是哪个痛点？"
    ↓
用户确认 → 正式写入success_cases.csv
    confirmed=true, success_points=用户确认的痛点
    ↓
⚠️ 未经用户确认的 → 不写入success_cases.csv
    仅记录ai_analysis字段，confirmed=false
    在看板中显示为 ⏳待确认
```

**命令**：
- AI 先在对话里给出痛点分析，**不写库**；用户确认后再写入：`csv_ops.py add_success <email> <brand> <contact> <amount> "<用户确认的痛点>" [--hook_type <solution_tag>] [--won_channel email|wa]`
- 列出成功案例：`csv_ops.py list_success [--region XX] [--need_tag XX] [--channel XX]`
- 复盘成功案例：`csv_ops.py review_success`

---

### 第一步：搜索候选（关键词矩阵 · 15 个发现渠道 · 10 平台社媒公开搜索）

**输入**：目标市场 + 行业关键词  
**输出**：候选客户清单（JSON/CSV）

**三类发现源，一个出口**（都只生成公开搜索式，不登录、不注册）：
- 关键词矩阵：`search_customers.py queries`
- 15 个发现渠道（含海关/展会/招标/招聘/竞品逆向…）：`search_customers.py channels`；海关免注册路径见 `references/海关数据操作指引.md`
- 10 大社媒公开搜索 + 30 个采购链职位：`search_customers.py social`，打法见 `references/social_media_playbooks.md`
- 出口统一：结果 → `search_customers.py filter results.json --against <客户库.csv>`（查库去重 + 漏斗诊断 + 待验证入池）

```python
# 伪代码逻辑
candidates = []

for source in [Google, LinkedIn, 展会名单, 竞品客户]:
    results = search(source, keywords, market)
    for brand in results:
        # IF 已在黑名单 → 跳过
        IF csv_ops.check(brand.email) == "blacklisted":
            CONTINUE
        
        # IF 已确认停业 → 跳过
        IF 公司状态 == "已关闭":
            CONTINUE
        
        # IF 纯C2C/个人卖家 → 跳过
        IF 业务类型 == "C2C":
            CONTINUE
        
        # ⚠️ 不因公司名/品类名做排除！
        # 名字看着不相关的公司可能有未被发现的需求
        
        candidates.append({
            "brand": brand.name,
            "website": brand.website,
            "email": brand.email,
            "region": brand.region,
            "contact_person": brand.contact_name,  # 如有
            "title": brand.contact_title,          # 如有
            "whatsapp": brand.wa_number            # 如有
        })

# 输出候选清单
save(candidates, "candidates.json")
```

**必采字段**：
- ✅ 公司名、官网URL、国家/地区
- ✅ 联系邮箱（优先级：具名个人 > 职能邮箱如 purchasing@/partners@ > info@）
- ✅ WhatsApp号（如有）
- ✅ 决策人姓名+职位（如有，用于后续邮箱猜测）

**搜索关键词模板**：
- 通用：`{market} {product} {customer_type}`（customer_type 取 `targeting.channel_keywords`，如 distributor / contractor / startup / clinic chain）
- 行业特定：见 `references/industry_playbooks.md`
- 详细搜索渠道和流程：见 `references/SOP_客户搜索详细流程.md`

---

### 第二步：背景调查（⭐核心，不可跳过）

**输入**：候选客户清单  
**输出**：每家客户的调研结论 + need_tag + solution_tag

```python
# 伪代码逻辑
for candidate in candidates:
    
    # === 数据层查重（背调前同步完成）===
    check_result = csv_ops.check(candidate.email)
    
    IF check_result == "blacklisted":
        SKIP  # 已在黑名单，不开发
    ELIF check_result == "in_cooldown":
        SKIP  # 在冷却期，暂不开发
    ELIF check_result == "wa_only":
        SKIP  # 已转WA渠道，不发邮件
    
    # IF 跨品牌排重不通过 → 跳过
    IF csv_ops.cross_brand_check(candidate.domain) == "duplicate":
        SKIP
    
    # === 开始背调（5个信息源）===
    research = {}
    
    # 1. 官网首页
    research["homepage"] = fetch(candidate.website)
    research["brand_positioning"] = extract_positioning(research["homepage"])
    research["main_categories"] = extract_categories(research["homepage"])
    
    # 2. 产品/服务/解决方案页（先过范围门禁）
    research["products"] = fetch(candidate.website + "/products|/services|/solutions")
    research["categories"] = extract_target_categories(research["products"], profile.targeting)  # need_tag 取值 = positioning.need_tags
    research["solution_fit"] = detect_solution_fit(research["products"], profile.product)  # 现有方案与 differentiators 的关系
    IF NOT is_within_targeting(research["main_categories"], research["categories"], profile.targeting):
        REJECT(candidate, reason="不在建档 targeting 范围（命中建档配置的相邻无关业务）")
    
    # 3. 采购/合规页（wholesale · vendor · partners · procurement · RFP · sustainability · compliance · careers）
    IF has_buying_or_policy_page(candidate.website):
        research["policy"] = fetch(candidate.website + "/sustainability|/compliance|/procurement")
        research["certifications"] = extract_certifications(research["policy"])  # 你行业真实通行的认证（建档时列出）
        research["buying_signal"] = extract_buying_signal(candidate.website)  # vendor application / partner program / RFP / 招聘
    ELSE:
        research["policy"] = None
    
    # 4. 新闻/社媒
    research["news"] = search_news(candidate.brand_name)
    research["recent_moves"] = extract_recent_strategy(research["news"])  # 新产品/扩张/融资/新项目/招聘
    
    # === 调研结论三问 ===
    conclusion = {
        "Q1_what_they_sell": research["categories"] + [research["solution_fit"]],
        "Q2_channel_and_stance": research["buying_signal"] or "未声明",
        "Q3_what_they_might_need": derive_need(research)
    }
    
    # === 确定双标签 ===
    need_tag = determine_need_tag(conclusion)
    candidate["need_tag"] = need_tag
    candidate["solution_tag"] = determine_solution_tag(conclusion)   # 11 个通用决策驱动，见 industry_playbooks §一
    candidate["research_notes"] = conclusion
    
    # 保存调研结论
    csv_ops.add_note(candidate.email, f"背调完成: {need_tag}")
```

**need_tag判定规则**：

```python
def determine_need_tag(conclusion):
    cats = conclusion["Q1_what_they_sell"]      # positioning.need_tags 中的取值 <line_a>/<line_b>
    
    # 范围门禁优先：不在建档 targeting 范围不进入
    IF not is_within_targeting(cats, profile.targeting):
        RETURN None  # 已在背调阶段拦截
    
    # 按主营品类定 need_tag（可多品类）
    IF len(cats) >= 2:
        base = "multi"
    ELSE:
        base = cats[0] if cats else "unknown"
    RETURN base


def determine_solution_tag(conclusion):
    fit     = conclusion.get("solution_fit", "")   # 现有方案与我方 differentiators 的关系
    signals = conclusion.get("Q3_signals", [])     # 背调信号：认证页/比价/小团队/节点/新方向/定制...
    tags = []
    IF "compliance_page" in signals or "tender_requires_cert" in signals: tags.append("compliance")
    IF fit == "uses_lower_grade_alternative":     tags.append("quality_upgrade")
    IF "small_or_first_time" in signals:          tags.append("low_commitment")
    IF "deadline" in signals:                     tags.append("speed")
    IF "new_initiative" in signals:               tags.append("innovation")
    IF "wants_custom" in signals:                 tags.append("exclusive_custom")
    # 只保留你档案里真实具备对应能力的标签（解决方案能力.md §二）
    tags = [t for t in tags if capability_exists(t, profile)]
    RETURN "+".join(tags) or "unknown"
```

**背调工具**：
- `csv_ops.check <email>` — 查重+黑名单+冷却期
- `csv_ops.cross_brand_check <domain>` — 跨品牌排重
- `research_guide.md` — 详细调研方法论

---

### 第三步：需求定位（need_tag → 推什么；solution_tag → 用什么钩子）

**输入**：need_tag + solution_tag  
**输出**：推荐线 + 邮件模板选择

```python
# 伪代码逻辑
for candidate in candidates:
    need_tag = candidate["need_tag"]
    
    # === need_tag → 推哪条线（取值与说明来自 positioning.need_tags / product_knowledge.md §一）===
    line_map = {
        "<line_a>": "主推<offer-line-A>，强调<differentiator>",
        "<line_b>": "主推<offer-line-B>",
        "multi":    "推整体方案/多线组合（仅当真实具备）",
        "unknown":  "保守通用切入，跟进中确认需求",
    }
    # === solution_tag → 邮件模板（email_templates.md §一，全行业通用）===
    template_map = {
        "compliance": "1.1", "sustainability": "1.1",
        "quality_upgrade": "1.2", "exclusive_custom": "1.2",
        "low_commitment": "1.3", "cost": "1.3",
        "speed": "1.4", "innovation": "1.5", "one_stop": "1.5",
        "dedicated_service": "1.6", "strategic_scale": "1.6",
        "open": "1.7", "unknown": "1.7",
    }
    main_driver = candidate["solution_tag"].split("+")[0]
    candidate["product_strategy"] = line_map.get(need_tag, line_map["unknown"])
    candidate["template"] = template_map.get(main_driver, "1.7")
```

**输出**：每家客户的 `product_strategy` + `template` 已确定

---

### 第四步：撰写内容（邮件）

**输入**：候选客户 + product_strategy + template  
**输出**：个性化邮件（标题+正文）

```python
# ========== 第4.0步：产品信息确认（if/else决策逻辑）==========
# 在使用钩子模板前，必须先确认产品信息

# ⭐ 唯一事实来源：首次建档生成的 config/company_profile.json（见 SKILL.md 首次建档门禁）
profile = config.load_profile(require_complete=True)   # 档案不完整则退出，不允许用占位词发信
# 产品知识库 references/product_knowledge.md 是这些字段的人工展开版，供查阅话术素材
product_info = {
    "keywords":       profile["product"]["primary_keywords"],      # 核心产品/服务词（建档填写）
    "one_liner":      profile["product"]["one_liner_en"],           # 一句话定位
    "entry_offer":    profile["offer"]["entry_offer"],              # 低门槛起步：样品/试用/诊断/试点…
    "key_facts":      config.offer_facts(profile),                  # 真实短事实（MOQ/上线周期/认证/时效…）
    "cta":            config.cta_question(profile),                 # 收尾问句
    "usp":            profile["product"]["differentiators"],        # 可验证差异化卖点列表
    "certifications": profile["product"].get("certifications", [])  # 真实持有证书，无则空
}
# 密钥不进档案：SMTP/IMAP 凭据只走环境变量 SMTP_* / IMAP_*

IF 档案缺失或关键字段为空:
    → 停止并引导完成首次建档（onboarding_questions.md），不得自行编造产品事实/联系方式

# === 第4.1步：选择模板 + 填入产品信息 ===
for candidate in candidates:
    
    # === 选择模板 ===
    template = load_template(candidate["template"])
    
    # === 个性化变量（从product_info提取） ===
    variables = {
        "brand_name": candidate["brand"],
        "contact_name": candidate.get("contact_person", "there"),
        "region": candidate["region"],
        "product": product_info["keywords"][0],  # 主推产品关键词
        "product_hook": get_product_hook(candidate["solution_tag"], product_info),
        "entry_offer": product_info["entry_offer"],   # 无默认值：必须来自建档真实事实
        "key_facts": product_info["key_facts"],
        "cta": product_info["cta"],
        "usp": product_info.get("usp", ""),
        "website": candidate.get("website", "")
    }
    
    # === 多语种本地化问候 ===
    # 核心原则：按收件人母语撰写整封邮件，不是只改问候语！
    language_map = {
        "IT": "italian",
        "DE": "german", 
        "FR": "french",
        "ES": "spanish",
        "JP": "japanese",
        "NL": "dutch",
        "PT": "portuguese"
    }
    
    IF candidate["region"] in language_map:
        language = language_map[candidate["region"]]
        # 使用完整母语模板（见email_templates.md §6.x）
        email_body = load_localized_template(language, variables)
    ELSE:
        # 默认英文
        email_body = f"Hi {variables['contact_name']},\n\n{template.format(**variables)}"
    
    # === 标题生成 ===
    subject = f"{variables['product']} for {variables['brand_name']}"   # 或按模板主题骨架
    
    # === 合规检查 ===
    IF len(email_body) > 120 words:
        WARN "邮件超长，需精简"
    
    IF any(word in subject.lower() for word in ["partnership", "collaboration", "free", "discount", "oem"]):
        ERROR "标题含禁用词，需替换"
    
    IF any(word in email_body.lower() for word in ["competitive pricing", "partner", "oem", "factory direct"]):
        ERROR "正文含禁用词，需替换"
    
    # === 输出邮件 ===
    candidate["email_subject"] = subject
    candidate["email_body"] = email_body
```

**禁用词表**：
- **标题禁**：Partnership / Collaboration / Free / Discount / OEM / ODM
- **正文禁**：competitive pricing / partner / OEM / factory direct / world-class / guaranteed / 任何无法证明的绝对化承诺
- **行业专属禁用词**（如医疗疗效、食品健康功效、金融收益承诺、你的品类里容易被误解的工艺词）写进 `rules.notes` 与 `soul_seven_kit/SOUL.md`，按同样规则拦截

**模板库**：`references/email_templates.md`

---

### 第五步：发送执行

**输入**：候选客户 + 邮件内容  
**输出**：发送记录 + 数据回写

**按收件人当地时间发（脚本强制）**：联系人带 `region`（或 `tz`）时，`batch_sender.py` / `decision_maker_sender.py` 只在收件人当地**工作日** `rules.local_send_window`（默认 `09:00-11:00,14:00-16:00`）内发送，窗口外本轮延后（报告 `deferred_window`，不写发送历史）。

| 市场 | 当地窗口 | 怎么换算成你本地时间 |
|---|---|---|
| 美国东部 / 加拿大东部 | 09:00-11:00, 14:00-16:00 | `python3 scripts/send_window.py table --me <你的时区>` 实时换算（含夏令时） |
| 英国 / 爱尔兰 / 葡萄牙 | 同上 | 同上 |
| 德法意西荷等欧洲大陆 | 同上 | 同上 |
| 中东（阿联酋/沙特） | 同上（注意周五/周六周末习惯，必要时用 `SEND_WINDOW` 调整） | 同上 |
| 澳大利亚 / 新西兰 | 同上 | 同上 |
| 日本 / 韩国 / 东南亚 | 同上 | 同上 |

> 不再写死「北京时间几点发哪国」：夏令时会让固定时差表每年错两次。以 `send_window.py table` 的实时结果为准；`send_window.py check DE` 返回单个市场当前是否可发。

```python
# === 发送前最后三道关（缺一不可）===

for candidate in candidates:
    
    # ========== 第一道：邮箱验证 ==========
    
    # IF 通用邮箱（info@/contact@等）→ 拦截
    IF is_generic_email(candidate["email"]):
        # 通用邮箱不对应具体决策人：本技能规则是不发冷邮件（经验规则，非统计数字）
        # 必须找决策人具名邮箱
        IF candidate.get("contact_person"):
            # 用邮箱猜测工具推导具名邮箱
            guessed = email_guesser.guess(candidate["contact_person"], candidate["domain"])
            candidate["email"] = guessed
        ELSE:
            SKIP "无决策人信息，先通过LinkedIn找人"
    
    # DNS/MX验证
    mx_valid = dns_validator.validate(candidate["email"])
    IF not mx_valid:
        SKIP "邮箱域名MX无效"
    
    # ========== 第二道：查重 ==========
    
    check_result = csv_ops.check(candidate["email"])
    
    IF check_result == "blacklisted":
        SKIP "已在黑名单"
    ELIF check_result == "in_cooldown":
        SKIP "在冷却期"
    ELIF check_result == "wa_only":
        SKIP "已转WA渠道"
    ELIF check_result == "duplicate":
        SKIP "重复发送"
    
    # 跨品牌排重
    IF csv_ops.cross_brand_check(candidate["domain"]) == "duplicate":
        SKIP "跨品牌重复"
    
    # ========== 第三道：检查备注信息 ==========
    
    notes = csv_ops.get_notes(candidate["email"])
    
    IF notes:
        # IF 有历史备注，按备注调整策略
        IF "客户说Q3再联系" in notes:
            IF current_month < 7:  # Q3=7-9月
                SKIP "等到Q3再联系"
        IF "客户对价格敏感" in notes:
            adjust_pricing_hook(candidate)
        IF "退信原因：邮箱不存在" in notes:
            SKIP "邮箱已失效"
    
    # IF 背调未完成 → 不发送
    IF not candidate.get("need_tag"):
        SKIP "背调未完成"
    
    # IF 邮件内容不合规 → 不发送
    IF not is_compliant(candidate["email_body"]):
        SKIP "邮件内容不合规"
    
    # === 最终确认 ===
    IF len(candidate["email_body"]) > 120 words:
        ERROR "邮件超长"
    IF same_day_sent_count(candidate["email"]) >= 1:
        SKIP "同客户同天已发过"
    
    # === 开始发送 ===
    
    # 方式A：手动发送（小批量）
    IF batch_size < 50:
        send_email_manual(candidate)
        csv_ops.add_sent(candidate["email"], candidate["brand"], candidate["subject"], candidate["need_tag"])
    
    # 方式B：SMTP批量发信（大批量）
    ELSE:
        # 决策人具名发信（推荐）
        IF candidate.get("contact_person"):
            decision_maker_sender.send([candidate])
        ELSE:
            batch_sender.send([candidate])
        
        # 发信铁律：
        # - 30秒间隔防风控
        # - 每日限额200封
        # - **按收件人当地时间发送**（当地时间9:00-11:00或14:00-16:00，见全球时区表）
        # - 禁止统一按发件人时区批量发送
    
    # === 发后必写 ===
    csv_ops.add_sent(candidate["email"], candidate["brand"], candidate["subject"], candidate["need_tag"])
```

**发信时间建议**（按收件人当地时间）：
- US：北京21:00-23:00
- UK：北京16:00-18:00
- IT/DE/FR：北京15:00-17:00
- JP：北京08:00-10:00

**⚠️ 发信时间铁律**：所有开发信必须以收件人所在国家的工作时间为准（当地时间9:00-11:00或14:00-16:00），禁止统一按发件人时区发送。具体时区对照见下方。

**全球时区发送时间对照表**（北京时间→当地时间）：
| 地区 | 时差 | 最佳发送时段（北京时间） | 当地时间 |
|------|------|------------------------|---------|
| US（美西） | -16h | 次日01:00-03:00 | 9:00-11:00 |
| US（美东） | -13h | 22:00-00:00 | 9:00-11:00 |
| UK | -8h | 17:00-19:00 | 9:00-11:00 |
| EU（IT/DE/FR/ES/NL/PT） | -7h | 16:00-18:00 | 9:00-11:00 |
| JP/KR | +1h | 08:00-10:00 | 9:00-11:00 |
| AU（东澳） | +2h | 07:00-09:00 | 9:00-11:00 |
| 中东（UAE/SA） | -4h | 13:00-15:00 | 9:00-11:00 |
| 东南亚（TH/ID/MY） | -1h | 09:00-11:00 | 10:00-12:00 |
| LATAM（BR/MX） | -11h | 20:00-22:00 | 9:00-11:00 |

**发送工具**：
- `dns_validator.py` — MX验证
- `email_guesser.py` — 邮箱格式猜测
- `decision_maker_sender.py` — 决策人具名发信（推荐）
- `batch_sender.py` — 批量发信

---

### 第六步：跟进管理

**输入**：已发送客户清单  
**输出**：跟进邮件 + 数据更新

**两套节奏分工，不叠加**：邮件按下面的 5 级冷却（`csv_ops.py cooldown` 计算）；社媒私信（人工）按 **1-3-7-21**（Day1 破冰 → Day3 价值 → Day7 案例 → Day21 换渠道），见 `references/social_media_playbooks.md` 第六节。同一客户同一天只走一个渠道。

```python
# === 每日执行 ===

# 1. 扫描退信/回复（IMAP自动）
imap_scanner.scan()  # 自动更新黑名单 + 标记bounced/replied

# 2. 检查冷却期
for email in sent_history:
    record = csv_ops.check(email)
    
    IF record["status"] == "bounced":
        # 退信=永久拉黑，不跟进
        CONTINUE
    
    IF record["status"] == "replied":
        # 收到回复 → 人工跟进
        NOTIFY "收到回复，请人工处理"
        CONTINUE
    
    IF record["status"] == "wa_only":
        # 已转WA → 不发邮件
        CONTINUE
    
    # === 冷却期判断 ===
    followup_count = record["followup_count"]
    days_since_last = days_since(record["last_followup_date"])
    
    # 5级递进冷却期规则（以 csv_ops.py 的 COOLDOWN_RULES / MAX_GENERIC_FOLLOWUP /
    # MAX_TOTAL_FOLLOWUP 为准；followup_count 从 0 计 = 最近一封是第 N+1 封）
    # 实际判断一律调用：csv_ops.py cooldown <email>，读返回的 action / can_followup
    IF followup_count == 0:          # 已发第1封
        cooldown_days = 3            # COOLDOWN_RULES[0]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="different_angle")
    ELIF followup_count == 1:        # 已发第2封
        cooldown_days = 3            # COOLDOWN_RULES[1]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="new_information")
    ELIF followup_count == 2:        # 已发第3封
        cooldown_days = 10           # COOLDOWN_RULES[2]
        IF days_since_last >= cooldown_days:
            send_followup(email, hook="last_attempt")
    ELIF followup_count == 3:        # 已发4封 → action = stop_generic
        # 停通用邮箱 → 仅 LinkedIn/个人邮箱
        IF has_linkedin(email):
            reach_via_linkedin(email)
    ELIF followup_count >= 4:        # 已发5封及以上 → action = stop_all
        # 邮件永久停发 → 仅 WA/个人邮箱；用 csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact> 记录
        IF has_whatsapp(email):
            reach_via_whatsapp(email)
    
    # === 跟进内容必须差异化 ===
    IF sending_followup:
        IF content == previous_content:
            ERROR "跟进内容必须完全差异化"
        IF not has_new_information(content):
            ERROR "跟进必须带新信息"
```

**跟进铁律**：
- ✅ 每封跟进必须带新信息（新案例/新数据/新版本/新角度/行业动态）
- ✅ 完全差异化，不复用之前措辞
- ✅ 4封无回复 → 转LinkedIn/个人邮箱
- ✅ 5封无回复 → 转WA
- ❌ 退信不再跟进（永久拉黑）

---

### 客户成交时：收集完整客户档案

**触发条件**：客户确认下单/付款  
**输出**：完整的客户背景信息档案

```python
# === 客户成交后，收集完整背景信息 ===

# 1. 基础信息（已有）
basic_info = {
    "email": contact.email,
    "brand": contact.brand,
    "contact": contact.contact_name,
    "region": contact.region,
    "order_amount": order.amount,
    "order_date": today,
    "source_channel": contact.source_channel  # 这个客户是从哪个渠道找到的
}

# 2. 公司背景信息（需调研补充）
company_info = {
    "company_name": "",  # 公司全称
    "founded_year": "",  # 成立年份
    "company_size": "",  # 员工规模/年营业额
    "main_business": "",  # 主营业务描述
    "business_model": "",  # B2B/B2C/混合
    "target_market": ""  # 目标市场（他们卖给谁）
}

# 3. 联系方式（需补充完整）
contact_info = {
    "contact_phone": "",  # 决策人电话
    "company_address": "",  # 公司地址
    "whatsapp": "",  # WhatsApp号码
    "wechat": "",  # 微信号（如有）
    "other_contact": ""  # 其他联系方式
}

# 4. 社媒账号（需搜索补充）
social_media = {
    "website": "",  # 官网
    "social_linkedin": "",  # LinkedIn公司页/个人主页
    "social_instagram": "",  # Instagram
    "social_facebook": "",  # Facebook
    "social_twitter": "",  # Twitter/X
    "social_pinterest": "",  # Pinterest
    "social_youtube": "",  # YouTube
    "social_tiktok": ""  # TikTok
}

# 5. 业务信息（需调研）
products_info = {
    "main_offerings": "",  # 主营产品/服务
    "size_or_budget": "",  # 规模/价位段/预算信号
    "current_solution": "",  # 目前在用的方案或供应方（与你 differentiators 的关系）
    "positioning": "",  # 定位（高端/中端/大众；企业/中小）
    "key_categories": ""  # 核心业务线
}

# === 收集方式 ===
# 方式1：背调时已收集（第二步背调时补充完整）
IF research_complete:
    company_info = extract_from_research(research_data)
    social_media = extract_social_from_website(candidate.website)

# 方式2：成交后补充（客户主动提供或进一步调研）
IF customer_confirmed_order:
    # 主动询问客户
    ASK customer: "方便提供公司官网、地址、WhatsApp吗？方便后续沟通"
    # 或自行搜索补充
    social_media = search_social_media(brand_name)

# === 写入成功案例档案 ===
csv_ops.add_success(
    email=email,
    brand=brand,
    contact=contact_name,
    order_amount=amount,
    success_points=confirmed_pain_points,  # 用户确认的痛点
    company_info=json.dumps(company_info),
    contact_phone=contact_phone,
    company_address=company_address,
    website=website,
    social_linkedin=social_linkedin,
    social_instagram=social_instagram,
    whatsapp=whatsapp,
    products_info=json.dumps(products_info),
    source_channel=source_channel,
    notes=notes
)
```

**客户档案用途**：
1. **复盘学习**：分析成功客户的共同特征
2. **二次开发**：同一公司不同品牌/联系人
3. **转介绍**：客户推荐新客户时，有完整背景
4. **长期跟进**：分享行业动态、新版本/新案例时，知道对方背景

> ⭐ **成交时必标成单渠道**：`add_success` 务必带 `--won_channel email` 或 `--won_channel wa`。这是 WA 复盘（下方第七步）区分“邮件成的”还是“WA 成的”的唯一依据；不标就无法算 WA 渠道贡献。

---

### 第七步：WhatsApp 触发 + 群发 + 专属复盘（邮件链的收口与自循环）⭐

**定位**：邮件链负责“广播触达”，WA 链负责“邮件未回的难客收口”，两链共用一个客户表，形成闭环。完整方法论见 `references/wa_bulk_guide.md`（七·二 模板库 / 七·三 触发链 / 十五 复盘闭环）。

```python
# === WA 触发：看板命中任一信号 → 进 WA 名单 ===
FOR record IN dashboard:
    IF (record.followup_count >= 2 AND record.status != "replied")   # ① 邮件多轮未回
       OR record.status == "bounced"                                 # ② 退信/邮箱无效
       OR (record.high_value AND record.public_wa)                   # ③ 高价值+有公开WA
       OR record.wa_from_expo:                                       # ④ 展会/主动留号
        SUGGEST add_to_wa_targets(record)     # 只建议，你拍板（元需求 2）；信号不足标 need_review

# === 触发链（五步）===
# ① 导出 WA 名单: email_dashboard.py 筛 pending/未回 → wa_targets.json
# ② 套模板:     七·二 7钩子 WA 版，{intro} 逐家生成（防封核心）→ Format B contacts.json
# ③ 群发:       wa_bulk_sender.py validate → preview → send（逐条截图验证，200/天防封）
# ④ 回写:       csv_ops.py mark_wa_only ；客户回复→ wa_contacts.csv status 回写 replied
# ⑤ 复盘:       wa_review.py review --html --compare-email（只读不改，14 铁律）

# === 自循环：复盘反哺下一轮触发 ===
review = wa_review.review()
#   哪个 region / hook_type / need_tag 在 WA 上成单多 → 下轮 WA 名单向它加权
#   wa_review --compare-email 告诉你：邮件 vs WA 哪条渠道更值得加预算
```

**WA 闭环铁律**：
- ✅ 触发信号命中只是“建议进名单”，真发/发多少/先发谁由你拍板（元需求 2）
- ✅ 每人 `{intro}` 不同（防封核心）；只用小号；禁 wa.me 进正文
- ✅ 成交必带 `--won_channel wa`，否则复盘口径不准
- ✅ wa_review 只读不改客户数据（符合 14 铁律）；结论仅供参考
- ❌ 不得因为“想发 WA”就绕过 4 个触发信号拍脑袋群发

---

### 第八步：成单复盘 + 七件套写回（闭环收口 · 每周）

**输入**：成交客户（邮件或 WA）、本周发送/退信/回复数据、本周 AI 出错记录
**输出**：成功案例入库、全渠道归因结论、七件套规则更新 → 下一轮第零步的起点

```python
# 1. 成交入库：AI 只给带证据的痛点候选，用户确认后才写入（见上文「客户成交时：收集完整客户档案」）
csv_ops.add_success(..., won_channel="email" | "wa")
# 2. 全渠道复盘（只读）
csv_ops.review_success()                 # 按地区 / need_tag / hook_type 拆解
email_dashboard.py                       # 邮件漏斗 + 成功案例模块
wa_review.py review --compare-email      # 邮件 vs WA 哪条渠道成单多
# 3. 七件套周复盘写回（references/soul_kit/周复盘写回.md）
#    答错 / 漏做 / 越界 → 归因到唯一一份档案 → 改规则（不只改这一句）→ 更新 HEARTBEAT
onboarding.py kit-check                  # 必须 7/7；改过档案后需重新回读确认 → attest
# 4. 结论写进 soul_seven_kit/MEMORY.md「本周结论」→ 回到第零步开始下一轮
```

---

## 📊 每日/每周例行任务

### 每日任务（发信时间由收件人当地窗口决定，先跑 send_window.py table 看哪些市场可发）

```python
# 1. 批量发信（日目标默认 100 封，硬上限 200 封；脚本自动跳过当地窗口外的收件人，下一轮再发）
batch_sender.send(max_count=100)

# 2. IMAP扫描退信（24-48小时后）
imap_scanner.scan()

# 3. 更新数据看板
email_dashboard.generate(sent_history, blacklist)

# 4. 检查冷却期 + 发跟进邮件
followup_manager.check_and_send()

# 5. ⭐ 每日汇报（任务完成后必做）
# 生成邮件追踪看板 + 提炼3-5个要点，向用户汇报当日工作成果
daily_report()
```

**每日汇报流程**：

```python
def daily_report():
    """任务完成后生成邮件看板 + 提炼3-5个要点"""
    
    # 1. 生成当日邮件追踪看板
    dashboard = email_dashboard.generate(sent_history, blacklist, title="每日发信追踪")
    
    # 2. 汇总当日数据
    today_data = {
        "sent_count": count_sent_today(),
        "bounced_count": count_bounced_today(),
        "replied_count": count_replied_today(),
        "blacklist_added": count_new_blacklist_today(),
        "pipeline_ready": csv_ops.pipeline_check()["ready_count"]
    }
    
    # 3. 提炼3-5个关键要点
    key_points = []
    key_points.append(f"今日发送: {today_data['sent_count']}封")
    
    IF today_data['bounced_count'] > 0:
        key_points.append(f"退信: {today_data['bounced_count']}封（已自动加入黑名单）")
    
    IF today_data['replied_count'] > 0:
        key_points.append(f"收到回复: {today_data['replied_count']}封（需人工跟进）")
    
    # 从成功案例/背调中提炼业务洞察
    insights = extract_daily_insights(today_data)
    FOR insight IN insights[:2]:  # 最多2条业务洞察
        key_points.append(insight)
    
    IF today_data['pipeline_ready'] < 100:
        key_points.append(f"⚠️ 备用池不足：当前{today_data['pipeline_ready']}家，建议补充")
    
    # 4. 向用户汇报
    REPORT_TO_USER(
        dashboard=dashboard,
        summary="📊 今日客户开发工作汇报",
        key_points=key_points[:5]  # 确保3-5个要点
    )
```

### 每周任务

```python
# 1. 复盘成功案例（检查待确认痛点）
csv_ops.review_success()

# 1.5 ⭐ 灵魂七件套周复盘写回（references/soul_kit/周复盘写回.md）
#     答错/漏做/越界 → 归因到唯一一份档案 → 改规则 → 更新 HEARTBEAT → onboarding.py kit-check

# 2. 生成邮件追踪看板（含成功案例复盘模块）
email_dashboard.generate(weekly_data)

# 3. 审查黑名单 + 清理过期数据
blacklist_review()

# 4. ⭐ 检查备用池储备量（每周日/周一）
pipeline_status = csv_ops.pipeline_check()
IF pipeline_status["ready_count"] < 100:  # 最低100家（7天储备）
    shortage = 100 - pipeline_status["ready_count"]
    PRINT f"⚠️ 备用池不足！当前{pipeline_status['ready_count']}家，需补充{shortage}家"
    # 启动补充任务：搜索+背调+需求定位
    create_supplement_task(count=shortage)
```

### ⭐ 备用池管理（v5新增）

**最低储备量**：100家（7天储备），建议储备300-500家（月度储备）

**检查频率**：
- 每周日 22:00 — 全面检查备用池
- 每日发送前 — 确认可用客户充足
- 储备低于50%时 — 立即补充

**备用池命令**：
```bash
# 检查备用池状态
python3 scripts/csv_ops.py pipeline_check

# 添加到备用池（已完成背调）
python3 scripts/csv_ops.py add_pipeline <email> <brand> <region> <need_tag> [priority]

# 列出备用池
python3 scripts/csv_ops.py list_pipeline [--status ready] [--region US]

# 从备用池取出发送
python3 scripts/csv_ops.py use_pipeline <email>
```

**备用池与发送协同**：
```
备用池储备（100家）→ 每日发送消耗（100家/天）→ 储备降至0 → 补充任务启动
     ↑                                                        ↓
     └──────────────── 补充完成 ────────────────────────────────┘
```

---

## 🚫 绝对禁令（14条铁律）

1. **公司名/品牌名不决定需求，调研才决定** — 不做粗筛
2. **不推客户明确不能用的东西** — solution_tag=compliance 的客户只推有对应资质的线；`positioning.tag_rules` 里的禁配组合一律不发
3. **WA专属客户绝不发邮件** — wa_only状态禁发邮件
4. **发前必查数据层+必做背调** — 不查就发=违规
5. **发后必写数据层** — 不发不写=数据断层
6. **不替客户判断大小** — 只展示能力，不主观判断
7. **付款提醒绝不自动发邮件** — 需人工确认
8. **跨品牌绝不重复触达** — 同一老板多品牌不重复
9. **暂停/停/不用了=立即停止一切操作** — 用户指令优先
10. **CSV操作必须用csv_ops.py脚本** — 禁止手动编辑
11. **删除技能/文件必须老板同意** — 不可擅自删除
12. **通用邮箱（info@/contact@等）绝不发冷邮件** — 不对应具体决策人，冷邮件进这类邮箱通常无人跟进（本技能经验规则，非统计数字）
13. **退信=永久拉黑，绝不重试** — bounced=永不触达
14. **发纯文本、不加追踪像素、带退订方式** — 本技能不引用无出处的「进箱率」数字；可核实的硬条件是 Gmail 发件人要求：所有发件人至少配 SPF 或 DKIM、垃圾邮件率保持在 0.3% 以下；每天给 Gmail 发约 5000 封以上的批量发件人需 SPF+DKIM+DMARC 且营销邮件支持一键退订（[Google 发件人指南](https://support.google.com/mail/answer/81126?hl=en)）。脚本已自动加 `List-Unsubscribe` 头和正文退订提示，详见 `references/mail_setup.md`

---

## 🛠️ 工具速查表

| 步骤 | 工具 | 命令 |
|------|------|------|
| 查重+黑名单 | csv_ops.py | `check <email>` |
| 跨品牌排重 | csv_ops.py | `cross_brand_check <domain>` |
| 追加发送 | csv_ops.py | `add_sent <email> <brand> <subject> <need_tag>` |
| 追加备注 | csv_ops.py | `add_note <email> <note>` |
| 标记退信 | csv_ops.py | `mark_bounced <email>` |
| 标记回复 | csv_ops.py | `mark_replied <email>` |
| 转WA渠道 | csv_ops.py | `mark_wa_only <email> <wa> <brand> <name>` |
| ⭐WA 专属复盘 | wa_review.py | `review [--html out.html] [--compare-email]` / `funnel`（只读不改） |
| ⭐WA 开发触发 | 方法论 | 看板命中 4 信号→进 WA 名单（wa_bulk_guide 七·三） |
| 冷却期查询 | csv_ops.py | `cooldown <email>` |
| 数据统计 | csv_ops.py | `stats` |
| 添加成功案例 | csv_ops.py | `add_success <email> <brand> <contact> <amount> <success_points> [--won_channel email\|wa --region --need_tag --hook_type --whatsapp --website ...]` |
| 列出成功案例 | csv_ops.py | `list_success [--region XX] [--need_tag XX] [--channel XX]` |
| 复盘成功案例 | csv_ops.py | `review_success` |
| MX验证 | dns_validator.py | `<input.json> [output.json]` |
| 邮箱猜测 | email_guesser.py | `<input.json> [output.json]` |
| 决策人发信 | decision_maker_sender.py | `<contacts.json> [report_dir]` |
| 批量发信 | batch_sender.py | `[max] [input.json] [report_dir]` |
| IMAP扫描 | imap_scanner.py | `[max_scan]` |
| 邮件追踪看板 | email_dashboard.py | `<data.json> [output.html] [title]` |

---

## 📚 参考文档

- `references/product_knowledge.md` — ⭐ 你自己的产品库建档模板（品类详情 + 核心卖点，首次建档后即成为开发前必读事实源）
- `references/research_guide.md` — 背调方法论详细指南
- `references/email_templates.md` — 邮件模板库（占位符模板，按 need_tag/solution_tag 分类；发送前用建档事实替换占位符）
- `references/industry_playbooks.md` — 通用B2B行业话术手册（7种钩子类型+8地区策略+产品信息确认流程）
- `references/SOP_客户搜索详细流程.md` — 15 种方法客户搜索详细SOP
- `references/csv_guide.md` — CSV字段和脚本参数说明
- `references/dashboard_guide.md` — 看板使用指南

---

**SOP版本**：v3.1  
**最后更新**：2026-10-19  
**更新内容**：安装门禁三关（kit-check + 内容指纹）、第一步三类发现源（含 10 平台社媒公开搜索）、S1/S2/S3 证据分级、收件人当地窗口发信、1-3-7-21 与 3/3/10 分工、第八步七件套周复盘写回；v3.1 新增数据接入层（data_import / mail_setup / crm_sync）、数据触发口（triggers）与四维轮换补池（详见 CHANGELOG v3.1）  
**维护者**：B2B客户开发AI业务搭子
