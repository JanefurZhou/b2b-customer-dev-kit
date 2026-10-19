# CHANGELOG

## v3.1 — 四维轮换 + 数据接入层 + 数据触发口

### 四维轮换（高度 / 广度 / 深度 / 远度）
- `search_customers.py replenish` 改为四维轮换：深度 d1 公司 → d2 决策人 → d3 存量深挖（转得最快）；远度 地区由近到远；高度 客户层级由高到低；广度 core → wide → max（转得最慢）。旧状态文件自动迁移。d3 种子来自成功案例、参考品牌、已发未回客户；没有种子时回退 d2 并提示。
- `--pool` 默认读 `$B2B_DATA_DIR/customer_db.csv`；可发数排除老客户 / 禁联 / 已发过的邮箱。

### 数据接入层（安装时马上配）
- 档案新增 `data_sources` 段；`data_sources.customer_db` 改为安装必填（imported / crm_sync / none），本技能不自带客户数据库。
- 新增 `scripts/data_import.py`：自有客户库与外贸 SaaS / 海关 / CRM 导出的 Excel/CSV 统一导入 `customer_db.csv`（inspect / import / stats / fields；中英文列名自动识别；禁联同步进黑名单）。
- 新增 `scripts/mail_setup.py` 与 `references/mail_setup.md`：腾讯 / 阿里 / 网易企业邮、Gmail、Microsoft 365 预设（每行带官方出处）；客户端密钥只走环境变量；多邮箱托管 + 预热爬坡（档位是可调默认值）+ 退信率超阈值自动暂停；`mcp-export` / `mcp-writeback` 走 MCP 连接器建草稿。
- 新增 `scripts/crm_sync.py`：导出 HubSpot / Salesforce / OKKI / 富通 / 通用 CSV；`pull` 回读；`push-hubspot` 默认演练，真推需 `CRM_PUSH=1` + `HUBSPOT_TOKEN` 且过安装门禁；`mcp-payload` 给 CRM MCP 用。
- 新增 `references/外贸SaaS对接指引.md`：各类外贸 SaaS 的对接方式与已查证的官方 API/MCP，厂商自报数字标明来源。

### 数据触发口
- 新增 `scripts/triggers.py` 与 `references/数据接入与触发口.md`：池低 / 新导入文件 / 到期跟进 / 新回复 / 退信异常 / WA 线索 / 预热升档 / 邮箱暂停 / CRM 待同步 / 周复盘 → `reports/trigger_queue.json`；唯一自动动作是退信异常时暂停邮箱，其余外发动作人工拍板。

### 发信合规
- `batch_sender.py` / `decision_maker_sender.py` 每封自动加 `List-Unsubscribe` 头与正文退订提示（`rules.opt_out_line`，"off" 关闭）。

### 去掉无出处数字
- 删除「纯文本进箱率 60–70%」「退信率 99.5%」等无出处说法，改为 Google 发件人指南原文要点并附链接；LinkedIn 指标标为内部阈值。

### 流程图与审计
- 流程图 v3.1：门禁下方新增「② 数据接入层」，自循环引擎改为四维轮换。
- `consistency_audit.py` 新增 O 节（数据接入层与四维轮换），并解析 4 个新脚本的子命令与参数。

## v3.0 — 融合版：安装门禁 + 10 平台社媒 + 证据分级 + 全闭环流程图

把「灵魂七件套」（soul-seven-kit）、「10 大海外社媒跨境获客」方法与用户评测里的建议并入通用版；新装的人装好后马上就知道要补什么，流程每个环节都有出口和回路。

### 安装门禁（新装第一件事）
- 新增 `onboarding.py start`：一屏列出「装好后马上要补的信息」——第 1 关公司档案必填、第 2 关灵魂七件套、第 3 关用户本人确认，加上建议马上补的目标市场、竞品、key_facts、发信窗口、社媒平台、SMTP 环境变量，并给出下一步命令（只读）。
- 新增 `onboarding.py kit-check`：七件套内容体检（规则来自 soul-seven-kit）——缺件 / 空壳（真内容 <3 条）/ 未替换的「（例…）」示例 / 缺关键段（每份 3 个关键词）/ 残留占位符。`check`、`attest` 与所有业务脚本的门禁都改用体检结果，只把 `filled` 改成 true 不再能过关。
- **确认后改动自动失效**：`attest` 记录档案 + 七件套的内容指纹（`confirmed_fingerprint`）；确认后任何改动，`check` 返回 `CHANGED_AFTER_CONFIRM`，业务脚本拒绝运行，必须重新回读确认。
- 新增 `references/soul_kit/填写参考_客户开发岗.md`（客户开发岗方法层写法，公司事实由用户提供）与 `references/soul_kit/周复盘写回.md`（错在哪就写回哪份档案）。

### 获客渠道
- 新增 `search_customers.py social`：10 大海外社媒（LinkedIn / Instagram / Facebook / YouTube / TikTok / Pinterest / X / Threads / WhatsApp / Lemon8）**免登录公开搜索式**生成器——只输出 Google / Bing 可用的 site: 搜索式；需要注册/登录的动作（连接请求、DM、进群、看粉丝列表）一律标为「人工 · 需登录」，脚本不执行。支持 `--platforms` / `--all` / `--tier decision|execution|influence|all` / `--titles` / `--urls` / `--out`；档案新增 `search.social_platforms`（空 = 全开）。
- 新增 30 个采购链职位词库（决策层 / 执行层 / 影响层各 10 个），档案 `targeting.buyer_titles` 排在前面。
- Instagram 9 组话题标签、竞品公开 @ 关系挖掘（替代需要登录的粉丝列表）、Facebook 群组五步法、DM 三句话、跨平台协同：`references/social_media_playbooks.md`。
- 新增 `references/海关数据操作指引.md`：HS 编码 → 国家级选市场 → 公司级进口商 → 决策人，免注册路径优先；`channels --ch customs` 增加 `site:importyeti.com` 搜索式。
- 新增第 13 个行业包 `packaging_materials`（包装材料/包装容器，评测建议的「玻璃包装」等归入此包）。

### 背调与跟进
- 新增证据分级 S1 / S2 / S3（`research_guide.md` 五·五）：≥1 条 S1 或 2 条独立 S2 才能定标签；只有 S3 → need_review 交用户拍板；邮件只引用 S1/S2 事实。
- 新增 `scripts/send_window.py`：按收件人当地时间判断能否发信（zoneinfo 实时计算夏令时；周末不发）。`batch_sender.py` / `decision_maker_sender.py` 对带 `region`/`tz` 的联系人强制执行 `rules.local_send_window`（默认改为 `09:00-11:00,14:00-16:00`），窗口外本轮延后、记入 `deferred_window`、不写发送历史；DRY_RUN 报告逐封标注窗口状态。`SEND_WINDOW` 覆盖窗口，`SEND_WINDOW_ENFORCE=0` 可关闭。之前档案里有这个字段但没有脚本执行。
- 社媒私信 1-3-7-21 节奏与邮件 5 级冷却（3 / 3 / 10 天）分工写清，同一客户同一天只走一个渠道。

### 安全（Skill-Self-Check 发现项）
- `imap_scanner.py`：新增 `DRY_RUN=1`（只列识别到的退信，不写数据）；邮箱改为只读打开（`readonly=True`）。
- `dns_validator.py`：新增 `DRY_RUN=1`（只列将要查询的域名，不发网络请求）。
- `wa_bulk_guide.md`：两处 `../csv_ops.py` 错误路径改为 `scripts/csv_ops.py`。
- SKILL.md：description 改为「Use when…」触发写法并补中文触发词；新增 Role contract（`references/role-contract.json`，single_context / single_role）与 Workflow prompt 不适用声明；三份 PowerShell 发送路径的人工审查记录见 `references/ship_safety_review.md`。

### 最终收口（脱敏 · 版本 · 流程图一致性）
- 最终脱敏复查：邮箱全部为 `.example` 保留域名；德国示例公司名改为 Musterfirma GmbH、示例号码改为明显虚构的号码；CHANGELOG 历史条目去掉对原始行业的具体描述；流程图 PDF 元数据标题改为流程图名称。
- 版本统一为 v3.0：SOP.md、SOP_客户搜索详细流程.md 表头/页脚，search_customers.py / csv_ops.py / email_dashboard.py 文件头去掉各自的旧模块版本号（v2.0 / v4.0 / v5.0 / v5.1），统一标注技能版本 v3.0；「12 渠道」改为实际的 15 种方法。
- 九个步骤名在流程图、SKILL.md、SOP.md、sop_flowchart.md 四处统一：第零步 全渠道复盘 · 第一步 搜索候选 · 第二步 背景调查 · 第三步 需求定位 · 第四步 撰写内容 · 第五步 发送执行 · 第六步 跟进管理 · 第七步 WhatsApp 触发 · 第八步 成单复盘 + 七件套写回。SOP.md 补上缺失的「第八步」章节，总览图从 0–6 步补全到 0–8 步。
- 冷却口径更正：流程图与 SKILL.md 原写「3 封停通用邮箱 / ≥4 封全停」，与脚本不符；统一为 `followup_count`（= 已发封数 − 1）：已发 4 封停通用邮箱，已发 5 封及以上邮件全停。WA 触发信号同步改为「邮件已发 ≥3 封无回」。
- WhatsApp 防封节奏由脚本执行：`send` 两条之间自动随机等 8–15 秒、每满 5 条冷却 30–60 秒（`wa_pacing.json`），之前只写在文档里。
- `decision_maker_sender.py` 每日上限与 `batch_sender.py` 一致：`DAILY_LIMIT` > 档案 `rules.daily_limit` > 200。
- 新增 `references/assets/sop_flowchart.json`（流程图机器可读规格）与 `consistency_audit.py` 第 N 节「流程图一致性」：步骤名四处一致、节点命令真实存在、13 个关键数字等于脚本常量（渠道数、平台数、职位数、补池红线、漏斗阈值、冷却天数、停发封数、每日上限、发信间隔、WA 节奏与上限）。

### 流程图
- 重画 `references/assets/sop_flowchart.png/.pdf`（v3.0）：顶部安装门禁三关、自循环引擎、三类发现源、搜索三铁律、证据分级分支、当地窗口延后回路、四分支跟进、WhatsApp 子流程、成单复盘 + 七件套周复盘写回 → 回到第零步。
- `references/sop_flowchart.md` 新增第四节「闭环核对表」：每个节点的正常出口与异常/循环回路逐条列出。

## v2.2 — 脚本与文档术语一致性审计

- 新增 `scripts/consistency_audit.py`（只读、标准库、`--json`，有 FAIL 时退出码 1）：核对 CLI 子命令与参数、档案字段路径、11 个 solution_tag、旧标签残留、发现渠道、行业包、文件引用、环境变量、CSV 表头、数量与版本、冷却期规则、状态取值。
- CLI 文档修正：删掉不存在的 `csv_ops.py confirm_success` 与 `list_success --pending`（成功痛点只在用户确认后经 `add_success` 写入）；`schedule --time` → `--at`；`preview/validate --dry-run` → `preview`（本身只读）；`queries --limit` → `queries --regions <国> | head -20`。
- 实现文档里写了但不存在的 `wa_bulk_sender.py convert <csv|xlsx|wa_targets.json> [out.json]`（CSV 零依赖；xlsx 需可选的 openpyxl；只转换不发送）。
- WhatsApp 环境变量统一：Python 读 `WA_MESSAGE_DIR`（旧名 `WA_MSG_DIR` 兼容）与 `WA_PROGRESS_FILE`，与 PowerShell 一致。
- 实现文档里写了但没有执行的 WhatsApp 每日上限：`wa_daily_count.json` 计数，`WA_DAILY_LIMIT`（默认 200，只能下调），到上限 `send` 返回 STOP（退出码 3）。
- `validate` 增加未填占位符检查（与邮件发信同一规则）。
- 冷却期：SOP 伪代码改为与 `COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}` 一致；csv_guide FAQ 的「cooldown_rules 默认 14 天」改正；status 取值删掉不落库的 `cooldown`。
- 字段：fb_strategy 的 `targeting.regions` → `targeting.target_regions`；search_customers 不再读未定义的 `targeting.competitor_brands`。
- 数据模板表头与 csv_ops 字段完全一致，补 success_cases / pipeline 模板，删除无用的 sent_history_updated.csv；行业包字段顺序统一。

## v2.1 — 行业残留审计

逐文件、逐脚本、含流程图 PNG/PDF 复查，清掉 v2.0 遗留的原始行业痕迹：
- **流程图**：第 3 步「定 need_tag + variant_tag → 产品线策略」改为「定 need_tag + solution_tag → 推哪条线 · 用哪个钩子」（PNG 与 PDF 同步）。
- **成功复盘痛点示例**（SOP.md 两处）：「环保材料 / 独家设计」改为「合规资质 / 更快交付上线 / 定制方案」，并标出对应 solution_tag。
- **csv_guide 的 need_tag 枚举**：删掉沿用旧版结构的 compliance-only / prefer / regulated 示例，改为自定义产品线 + multi/review/unknown。
- **背调信息表**：materials「材质/工艺」、style「风格」改为主营产品/服务、规模/预算、在用方案、定位。
- **通用邮箱识别**：三个脚本各自维护、偏批发的前缀表，统一为 `config.GENERIC_MAILBOX_PREFIXES`，新增 partners / procurement / projects / tenders / hr / careers / billing / legal 等跨行业职能邮箱。
- **礼品渠道**：改为需 `--ch gift` 手动指定，不再进入实体商品默认渠道。
- **竞品字段**：`has_own_factory` 改为通用的 `is_competitor`（旧字段仍兼容）。
- **话术示例**：LinkedIn 的 range/brands/sample/MOQ、工厂参观，Facebook 群组词，SOP 搜索式里的 wholesale/shop store/sourcing，SOUL.md 的「老外贸」与「MOQ、交期」铁律，全部改为行业中性写法，并补充软件/服务/项目的布尔式与搜索式示例。
- **术语**：「订单金额」改为「成交金额」；「库存旧标签」改为「库内旧标签」（避免与库存混淆）。
- 新增说明：名录/招标/评测页是线索来源页，不会被当作客户入池。

## v2.0 — 全行业通用版（Universal）

在 v1.1 通用脱敏模板基础上，去掉残留的原始行业偏向与话术，改成任何 B2B 行业都能用的结构。

### 新增
- **行业包** `references/industry_packs.json`：12 个（实体外贸、工业品、品牌分销、SaaS、专业服务、物流、医疗实验室、食品农产品、建材工程、新能源、培训教育、自定义）。只含方法层建议（分层、角色、渠道、意图词、信号、合规提示），不含任何公司事实。
- `onboarding.py packs | pack <id> | apply-pack <id>`：只写入仍为空的方法层字段，并自动把 `user_confirmed` 重置为 false。
- 档案新段落：`business`（行业、交付形态 offer_type、行业包）、`offer`（entry_offer / cta_question / key_facts / proof_points / repeat_hook）、`positioning`（自定义 need_tags、互斥组、库内规则、钩子覆盖）、`targeting.customer_industries`、`search.query_anchor`。
- 必填项新增 `business.industry`、`business.offer_type`。
- **占位符门禁**：档案里残留 `<...>` / `{...}` 不能 attest；外发邮件残留占位符时直接拦截，不发送。
- **客户锚点搜索**：软件/服务业务按「客户所在行业」生成搜索式，避免搜到同行。
- 6 个新发现渠道：tender 招标、hiring 招聘信号、directory 行业目录/协会、review 评测站、partners 生态伙伴、events 会议名录（共 15 个）；按 offer_type 自动挑默认渠道。
- `references/行业适配指南.md`：三步接入、术语对照表、4 个行业示例。
- `examples/profiles/`：3 份虚构演示档案（工业零部件 / HR SaaS / SEO 咨询），不能直接激活。

### 改动
- 决策驱动标签 `solution_tag` 统一为 11 个跨行业取值；旧标签（eco_only / traditional / low_moq / seasonal 等）自动映射，历史数据不用改。
- `need_tag` 改为使用者自定义的产品/服务线；`conflict-check` 不再内置任何行业的互斥规则，改读 `positioning.conflict_groups` / `tag_rules`。
- 邮件与 WhatsApp 的事实行、收尾问句改读 `offer.*`（旧 `product.moq` / 打样周期保留兼容）；去掉写死的 "Worth sending you a sample?"、"new collection / lookbook"。
- 重写 `industry_playbooks.md`、`email_templates.md`、`product_knowledge.md`、`解决方案能力.md`；研究、搜索、SOP、LinkedIn、Facebook、WhatsApp 文档去掉原始行业示例与原行业专属的 L1–L6 客户光谱。
- `search_customers.py` 删除重复定义的冲突校正/漏斗/调度/参数解析代码块（旧版有两份，后一份覆盖前一份）。

### 脱敏
- 复查：无真实公司名、人名、邮箱、电话、域名、客户数据；演示数据一律使用 `.example` 域名与虚构名称。
