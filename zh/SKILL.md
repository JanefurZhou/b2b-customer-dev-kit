---
name: b2b-customer-dev-kit
description: >-
  Use when the user wants to find, vet, and contact new B2B customers in any
  industry: lead search (keyword matrix, 15 discovery channels incl. customs
  data, no-login public search across 10 social platforms), background research
  with S1/S2/S3 evidence grades, demand positioning, localized cold email,
  DNS checks, local-time-window sending, bounce scanning, 5-step follow-up,
  WhatsApp hand-off, and win review; plus a data-access layer (own customer DB
  and SaaS/CRM export import, enterprise-mailbox keys or MCP sending, mailbox
  warm-up, CRM sync) and daily data triggers with a 4-axis search rotation.
  Triggers: 找客户, 客户开发, cold email, outreach, 背调, 需求定位, 海关数据,
  社媒获客, 批量发信, 退信处理, WhatsApp 群发, 客户库导入, 企业邮箱, CRM 同步,
  成功案例复盘. Industry-agnostic and de-identified: ships with no
  company, contact, or customer data. A mandatory install gate (company profile
  + Soul Seven-Kit content check + explicit user confirmation) must pass before
  any search or send script runs. Not for consumer marketing, paid ads, or
  market sizing.
license: CC-BY-NC-4.0
compatibility: "Requires Python 3.8+ (standard library only; 3.9+ for daylight-saving-exact send windows). Network access needed for DNS/SMTP/IMAP and web search."
metadata:
  version: "3.2"
  type: "universal-template"
  onboarding: "mandatory-first-run"
---

# B2B Customer Development Kit（全行业通用版 v3.2）

核心理念：**不做粗筛，每家都查背景、定位需求、针对性推对应方案；品牌名不决定需求，调研才决定。** 用数据闭环替代 AI 记忆，用脚本替代人工计算，用证据替代猜测。

## ⛔ 安装门禁 — 新装第一件事（三关不过，所有搜索/发信脚本拒绝运行）

这是一个**通用模板**：不含任何公司名、产品、签名、关键词、客户名单或默认行业。门禁通过之前，只做建档，不做搜索、补充或发送。

### 防编造规则（最高优先级）

- **每一个关键事实都来自用户本人或用户指定的来源**（官网、名片、对话里的原话）：公司名、联系人、邮箱、电话/WhatsApp、网站、产品主张、MOQ/价格/交期/上线时间、认证、案例、关键词。行业包只是方法层建议，不算用户事实。
- 某个字段不知道 → **问用户**。占位域名、猜出来的邮箱格式、"看起来合理"的数字都会导致退信和误发。
- **确认只能由用户本人给出。** `attest` 只在你把每个值原样回读、用户明确回复「确认无误」之后运行。确认后档案或七件套任何改动，内容指纹都会失配，脚本重新拦截，必须再回读、再确认。

### 第一步：运行新装必做清单

```bash
python3 scripts/onboarding.py start      # 一屏列出装好后马上要补的信息 + 每项当前状态（只读）
python3 scripts/onboarding.py init       # 生成空白 config/company_profile.json + soul_seven_kit/（不覆盖已有文件）
```

### 三关

| 关 | 要补什么 | 命令 | 不过时 |
|---|---|---|---|
| 第 1 关 公司档案必填 | `business.industry`、`business.offer_type`、`company.brand_display`、`contact.founder_name`、`contact.email`、`product.one_liner_en`、`product.primary_keywords`（≥3）、`product.differentiators`（≥2）、`targeting.buyer_titles`（≥1）、`data_sources.customer_db`（`imported` / `crm_sync` / `none`，本技能不自带客户数据库） | `ask`（逐项问）或先 `packs` → `pack <id>` → `apply-pack <id>` 套行业方法层（13 个行业包） | 列出缺的字段 |
| 第 2 关 灵魂七件套体检 | `soul_seven_kit/` 七份：IDENTITY（岗位/服务对象/红线）· SOUL（语气/优先级/决策）· AGENTS（SOP/人工确认/禁做）· TOOLS（何时用/怎么用/坏了怎么办）· MEMORY（结论/待办/下一步）· USER（汇报/审批/敏感）· HEARTBEAT（运行/完成率/错误），每份三五条真内容 | `kit-check`（缺件 / 空壳 / 未替换的「（例…）」示例 / 缺关键段 / 占位符，任何一项都不过） | 列出每份的具体问题 |
| 第 3 关 用户本人确认 | AI 把档案与七件套摘要原样回读，用户明确回复「确认无误」 | `check`（返回 `FILLED_NOT_CONFIRMED` 是正常的）→ `attest` | `REFUSED` / `CHANGED_AFTER_CONFIRM` |

七件套的填写参考（客户开发岗，方法层写法，公司事实由用户提供）：`references/soul_kit/填写参考_客户开发岗.md`。首次建档时 MEMORY / HEARTBEAT 照实写「首次建档，尚无数据」即可。

建议马上补（不拦截，但直接影响效果，`start` 会逐项显示）：`targeting.target_regions`、`targeting.reference_brands`、`offer.key_facts`、`offer.entry_offer`、`rules.local_send_window`（默认 `09:00-11:00,14:00-16:00`）、`search.social_platforms`（空 = 10 个全开）、SMTP 环境变量（只在脚本批发时需要）。

**联系方式规则**：只用用户确认过的联系方式。SMTP/IMAP 密码是密钥，只放环境变量（`SMTP_HOST/PORT/USER/PASS`、`IMAP_*`），不进档案、不进消息。完整访谈脚本：`references/onboarding_questions.md`。

### 数据接入层（装好马上配，`start` 逐项显示状态）

| 接什么 | 命令 | 说明 |
|---|---|---|
| 自有客户库（安装必填声明） | `data_import.py inspect <Excel/CSV>` → `import --relation existing_customer\|prospect --source own:excel` | 统一落到 `$B2B_DATA_DIR/customer_db.csv`；中英文列名自动识别，`--map` 可改；老客户/禁联不进冷开发池 |
| 外贸 SaaS / 海关 / CRM 导出 | 放进 `data/inbox/` → `triggers.py scan` 提醒 → 同一入口导入 | 对接方式与已查证的官方 API/MCP：`references/外贸SaaS对接指引.md` |
| 发信通道 | `mail_setup.py providers` → `env <服务商> --user <邮箱>` → `test`（只登录不发信） | 企业邮箱客户端密钥 / 多邮箱托管 + 预热爬坡 + 退信自动暂停 / MCP 连接器建草稿：`references/mail_setup.md` |
| CRM 同步 | `crm_sync.py export --target hubspot\|salesforce\|okki\|fumeng\|generic` · `pull` · `push-hubspot` · `mcp-payload` | CSV 任何 CRM 可用；HubSpot API 与 MCP 默认演练 |
| 数据触发口 | `triggers.py scan [--apply-safe]` | 池低 / 新导入 / 到期跟进 / 新回复 / 退信异常 / WA 线索 / 预热升档 / CRM 待同步 / 周复盘 → `reports/trigger_queue.json`；外发动作一律人工拍板：`references/数据接入与触发口.md` |

## Industry Adaptation（行业适配）

闭环在任何行业都一样，变的只有三件事，全部在档案里，不在代码里：

| 变什么 | 档案区块 | 例：零部件厂 → SaaS → 咨询公司 |
| --- | --- | --- |
| 找谁 | `targeting` | OEM 采购 → CTO → 创始人 |
| 去哪找 | `search` + `business.offer_type` | 海关/展会 → 评测站/招聘 → 招标/名录 |
| 怎么低门槛开始 | `offer` | 样品 → 14 天试用 → 免费诊断 |

背调产出两个标签：`need_tag`（客户需要你的哪条线，取值由用户在 `positioning.need_tags` 定义）与 `solution_tag`（客户的决策驱动，11 个跨行业固定值：`compliance`、`sustainability`、`quality_upgrade`、`cost`、`speed`、`low_commitment`、`innovation`、`exclusive_custom`、`one_stop`、`dedicated_service`、`strategic_scale`）。钩子按 `solution_tag` 选；v1 旧标签自动映射。13 个行业包、术语对照与 4 份虚构示例档案：`references/行业适配指南.md`。

## When to Use

- 任何行业从 0 到 1 成体系做 B2B 获客：找客户、扩渠道（海关数据、展会、招标、招聘信号、竞品逆向、10 大社媒公开搜索）。
- 背调与需求定位：need_tag / solution_tag、证据分级、跨品牌排重、标签冲突校正。
- 写信与发送：多语种本地化冷邮件、DNS/MX 校验、邮箱猜测、按收件人当地时间批量发送。
- 跟进与复盘：退信扫描、5 级冷却跟进、社媒 1-3-7-21、WhatsApp 转化、成功案例与七件套周复盘。

### When NOT to use

- 热线索 / 已回复客户 / 询盘未转化 → 交人工单点跟进，先告知用户。
- 面向消费者的营销、付费广告、SEO、纯市场规模测算；没有合法联系依据的名单。
- 报价、催款、合同条款 → 本技能只做开发与跟进，这些由用户本人处理。
- 门禁未 `READY`，或用户尚未批准本批草稿 → 发送保持锁定。

## Process（安装门禁 + 第零步 + 七步法 + 收口）

完整闭环流程图：`references/assets/sop_flowchart.png`（PDF 同名）；每个节点的出口与回路：`references/sop_flowchart.md` 第四节。

```
安装门禁(start→init→档案→kit-check→check→attest=READY)
  ▸ 数据接入层              → data_import · mail_setup · crm_sync → 客户池 customer_db
  ▸ 数据触发口（每天）      → triggers.py scan → 按队列进对应步骤（外发动作人工拍板）
  ▸ 第零步 全渠道复盘        → 成功打法 + WA 复盘 + 上周七件套写回结论
  ▸ 第一步 搜索候选          → queries · channels(15) · social(10 平台公开搜索)
      └ 搜索三铁律          → filter --against 查库 · funnel 漏斗 · 待验证入池
  ▸ 第二步 背景调查          → 5 信息源 + 背调三问 + S1/S2/S3（只有 S3 → need_review）
  ▸ 第三步 需求定位          → need_tag + solution_tag（tag_rules 冲突 → 人工）
  ▸ 第四步 撰写内容          → 母语整封 · ≤120 词 · 纯文本 · 只引用 S1/S2 事实
  ▸ 第五步 发送执行          → 三道关 → DRY_RUN → 用户批准 → 收件人当地窗口内发
  ▸ 第六步 跟进管理          → 退信/回复/成交/无回复 四分支；邮件 3/3/10 天；社媒 1-3-7-21
  ▸ 第七步 WhatsApp 触发     → convert → validate → preview → harness → send → audit → wa_review
  ▸ 第八步 成单复盘 + 七件套写回 → add_success → review → 周复盘写回 → kit-check → 回第零步
```

1. **门禁 + 数据接入** — `python3 scripts/onboarding.py check` = `READY`；客户库按声明导入，发信通道 `mail_setup.py test` 通过；每天先跑 `triggers.py scan`。
2. **第零步 全渠道复盘** — `csv_ops.py review_success`、`wa_review.py review`；读 `soul_seven_kit/MEMORY.md` 的本周结论作为本轮起点。
3. **第一步 搜索候选** — `search_customers.py queries`（关键词矩阵）· `channels`（15 个发现渠道；海关免注册路径见 `references/海关数据操作指引.md`）· `social`（10 大社媒免登录公开搜索 + 30 个采购链职位，打法见 `references/social_media_playbooks.md`）。脚本只生成公开搜索式；需要登录的动作（连接请求、私信、进群）由用户本人决定是否手动做。结果统一走 `filter --against <客户库.csv>`（查库去重 + 漏斗诊断 + 待验证入池）。自循环补池：`replenish` / `schedule` 按四维轮换——深度 d1 公司 → d2 决策人 → d3 存量深挖（最快）· 远度 地区由近到远 · 高度 客户层级由高到低 · 广度 core → wide → max（最慢）（`references/自循环引擎.md`）。
4. **第二步 背景调查** — 每条结论标证据等级与来源：至少 1 条 S1 或 2 条独立 S2 才定标签；只有 S3 → `need_review` 交用户拍板（`references/research_guide.md` 五·五）。重点客户另写决策链（拍板人 / 对接人 / 影响者）、终端差评痛点候选（用户确认后才用），有海关记录时用 `customs_summary.py` 推断采购窗口（五·六）。询盘到达后的交易风控（身份、制裁、签约主体、付款条件）交给独立的 customer-background-investigation 技能。
5. **第三步 需求定位** — need_tag 决定推哪条线，solution_tag 决定钩子；`conflict-check --against <pool.csv>` 只提示冲突、不改数据。
6. **第四步 撰写内容** — `references/email_templates.md`；占位符只用 `product.*` / `offer.*` 填；发信脚本拦截任何残留 `<...>` / `{...}`。案例、ROI、百分比只引用用户确认过的 `success_cases`；没有就只写能力，不写数字。
7. **第五步 发送执行** — 发前三道关（邮箱 ✓ 查重 `csv_ops.py check` / `cross_brand_check` ✓ 备注 ✓）→ `DRY_RUN=1` 生成逐封报告 → **用户明确批准** → `decision_maker_sender.py`（或 `batch_sender.py`；发信通道三选一：单邮箱密钥 / 多邮箱托管按预热上限轮换 / `mail_setup.py mcp-export` 交连接器建草稿）。每封自动带 `List-Unsubscribe` 头和正文退订提示。联系人带 `region`/`tz` 时只在收件人当地工作日窗口内发，窗口外本轮延后（`send_window.py table --me <你的时区>` 实时换算，含夏令时）。每日 ≤200 封，间隔 30 秒。
8. **第六步 跟进管理** — 发信后 24–48 小时扫一次退信/回复：`DRY_RUN=1 imap_scanner.py` 先看识别结果，再正式回写（邮箱只读打开）；`csv_ops.py cooldown <email>` 计算 5 级冷却（按 `followup_count` = 已发封数 − 1：已发 1 / 2 / 3 封后分别等 3 / 3 / 10 天；已发 4 封 → 停通用邮箱，只走 LinkedIn / 个人邮箱；已发 5 封及以上 → 邮件全停，转第七步）；社媒私信按 1-3-7-21（人工）；同一客户同一天只走一个渠道。
9. **第七步 WhatsApp 触发** — 触发信号命中后：`wa_bulk_sender.py convert → validate → preview → harness → send → audit`（双号隔离；`send` 自动按随机 8–15 秒间隔、每 5 条冷却 30–60 秒出下一条；每日 200 条计数器强制 STOP），细节 `references/wa_bulk_guide.md`。
10. **第八步 成单复盘 + 七件套写回** — 成交 → AI 给出带证据的痛点候选 → 用户确认 → `add_success --won_channel email|wa`；`review_success` / `email_dashboard.py` / `wa_review.py --compare-email` 做全渠道归因；每周按 `references/soul_kit/周复盘写回.md` 把错写回对应档案 → `kit-check` → 回第零步。

**Gate scope（门禁范围）**：会搜索、发送、打开 WhatsApp 或真推 CRM 的命令（`search_customers.py`、`batch_sender.py`、`decision_maker_sender.py`、`wa_bulk_sender.py screenshot/send/harness/audit`、`crm_sync.py push-hubspot` 真推模式）在门禁 `READY` 且内容指纹一致之前全部拒绝运行。只读或本地准备工具（`validate`/`preview`/`template`/`convert`、`dns_validator.py`、`email_guesser.py`、`send_window.py`、看板、`data_import.py`、`mail_setup.py`、`triggers.py`、`crm_sync.py export/pull`）建档前也可用，方便安装时先导入客户库、配好邮箱。门禁拦截时，报错会写明卡在哪一关。

**Safety baseline（安全基线）**：凭证只走环境变量（多邮箱托管文件只存变量名）；推 CRM 默认演练；触发口只读，唯一自动动作是退信异常时暂停邮箱；SMTP 仅 465/587+STARTTLS，IMAP 仅 IMAPS；发信、退信扫描、DNS 校验都支持 `DRY_RUN=1` 演练；退信扫描以只读方式打开邮箱；通用邮箱前缀自动拦截；退信永久拉黑；脚本只读不自改客户数据；社媒只做公开搜索。

数据接入与触发口：`references/数据接入与触发口.md`；数据结构与 CSV 操作：`references/csv_guide.md`；完整 SOP：`references/SOP.md`；无人值守调度与人机边界：`references/automation_setup.md`；版本历史：`CHANGELOG.md`。

### Check axes（每个客户/每批邮件过这 6 个轴）

- **Target fit** — 业务与档案的产品/服务与客户层匹配，未命中任何 exclude_keywords。
- **Reachable contact** — 真实、可溯源的具名决策人邮箱，DNS/MX 通过。
- **Demand hook** — 有具体采购信号，solution_tag 有 S1/S2 证据，钩子由档案的 differentiators 与 offer 支撑。
- **Localization** — 语言、问候、发信时段匹配收件人所在国家。
- **Deliverability** — 每日上限、同联系人冷却、当地窗口全部满足。
- **Approval & signature** — 批次经用户明确批准，签名只含用户确认过的联系方式。

## Common Rationalizations

| 借口 | 真相 |
| --- | --- |
| "先猜一个公司/产品开工。" | 模板故意留空；编造身份或联系方式会毁掉送达率和信任。先过门禁。 |
| "七件套把 filled 改成 true 就行。" | `kit-check` 看真内容：空壳、未替换的「（例…）」示例、缺关键段都过不了。 |
| "确认过一次，后面改档案不用再确认。" | 内容指纹会失配，脚本重新拦截；改动必须回读、再确认。 |
| "`info@`/`sales@` 也算进客户池。" | 通用邮箱大多退信或无人处理；只有可溯源的具名联系人才算池子健康度。 |
| "评论区有人提了一句，就定成这个需求。" | 那是 S3 弱信号，只能标 need_review 交用户拍板。 |
| "为了省时间，批准前先发。" | 外发邮件是高风险对外动作；每一批都要用户明确批准。 |
| "社媒上直接批量加好友/私信更快。" | 本技能只做免登录公开搜索；登录后的动作由用户本人决定，并遵守平台条款。 |
| "什么时间方便就什么时间发。" | 按收件人当地工作日窗口发，脚本会把窗口外的收件人延后。 |
| "退信可能是临时的，再发一次。" | 退信永久拉黑；重发损害发件信誉。 |
| "新邮箱第一天就发满额度。" | 托管邮箱按预热档位爬坡（档位是可调默认值）；一轮退信超阈值自动暂停。 |
| "客户库里有邮箱就能冷开发。" | 老客户、禁联、同行不进冷开发池；SaaS 导出的邮箱同样要过 DNS 校验和背调。 |

## Red Flags

- 档案缺失、`configured=false` 或内容指纹不一致时，有搜索/发送/WhatsApp 发送命令在运行。
- 七件套里还留着「（例…）」示例行，却已经 attest。
- 草稿里出现用户没确认过的邮箱/电话/网站，或残留 `[...]` / `<...>` 占位符。
- 猜出来的 `export@/info@` 被当成已验证线索。
- 只有 S3 证据的客户被定了具体 need_tag 并激进推销。
- 同一个号码在 WhatsApp 名单里出现两次并进入 harness/send；单日超过 200 条。
- 当地窗口外发送，或违反同联系人冷却；同一客户同一天走了两个渠道。
- SMTP/IMAP 密钥写进档案、脚本、日志或 `config/mailboxes.json`。
- 托管邮箱已暂停仍在发信；推 CRM 或 MCP 发信清单里有 `approved=false` 的条目被执行。
- 草稿批次在用户明确批准之前被发出。
- 草稿里出现未经用户确认的案例、ROI 或百分比；用没有出处的"周期比例"决定发信时机。

## Role contract

Workflow prompt audit: N/A — single agent context; the bundled scripts make no model calls and there is no multi-step prompt chain.

- Runtime mode: single_context · Role mode: single_role · Entry role: `b2b-outbound-owner` (machine-readable copy: `references/role-contract.json`)
- Role: B2B outbound customer-development owner
- Purpose: Run one evidence-bounded outbound loop from onboarding gate to search, vetting, positioning, approved sending, follow-up, WhatsApp hand-off, and review for the user's own business.
- Inputs:
  - User-confirmed config/company_profile.json
  - Seven-kit files in soul_seven_kit/ that pass kit-check
  - Public search results and the user's customer CSV files
- Responsibilities:
  - Gate every task on onboarding check = READY before search or sending.
  - Vet each account with S1/S2 evidence and set need_tag and solution_tag from research.
  - Prepare localized drafts and DRY_RUN reports for the user to approve before any send.
  - Write every send, bounce, reply, and WhatsApp result back through csv_ops.py.
- Out of scope:
  - Inventing company facts, contacts, emails, phone numbers, prices, or case studies.
  - Logging in to, registering on, or automating actions inside social platforms.
  - Sending quotes, payment reminders, or contract terms.
- Decision authority:
  - May choose search queries, channels, and candidate order within the confirmed profile.
  - May mark an account need_review when evidence is only S3.
  - May defer a send that falls outside the recipient's local window.
- Outputs:
  - Candidate pool with funnel diagnosis
  - Research notes with evidence grades
  - Approved draft batch and send report
  - Follow-up, WhatsApp, and review summary
- Acceptance tests:
  - onboarding.py check prints READY and kit-check passes 7/7.
  - Every sent address is a named, DNS-validated contact that passed csv_ops.py check.
  - Every tag and email claim maps to an S1 or S2 source recorded in notes.
  - consistency_audit.py reports FAIL 0.
- Stop conditions:
  - Stop and ask the user when a required fact is missing or the gate is not READY.
  - Stop all actions immediately when the user says pause or stop.
  - Stop sending for the day at the daily limit or after a repeated send failure.
- Hand-off to:
  - User approval of each draft batch
  - User handling of replies, quotes, and contracts

## Verification

一轮开发结束前逐项确认：

- [ ] `python3 scripts/onboarding.py check` 打印 `READY`，`kit-check` 为 7/7。
- [ ] `search_customers.py channels` / `social` 的默认渠道与平台贴合用户行业。
- [ ] 每条新线索都有真实、可溯源的具名联系人，背调证据达到 S1 或 2×S2，弱信号已标 need_review；重点客户已写决策链（查不到的角色写"未获取"）。
- [ ] 草稿已本地化、只引用事实，批次经用户明确批准；`DRY_RUN` 报告已逐封核对。
- [ ] 地址通过 DNS/MX；发送发生在收件人当地窗口内，冷却与每日上限得到遵守。
- [ ] 退信已拉黑，发送/黑名单 CSV 已回写；WhatsApp 名单通过 `validate`（无重复、无未填占位符）。
- [ ] 看板/漏斗数字已汇报，并区分目标客户与非目标客户，不只报原始数量。
- [ ] `triggers.py scan` 的人工拍板项已处理并 `ack`；`crm_sync.py` 已与 CRM 对齐（如使用）。
- [ ] 本周七件套写回已完成并重新 `kit-check`；`python3 scripts/consistency_audit.py` 为 FAIL 0。
