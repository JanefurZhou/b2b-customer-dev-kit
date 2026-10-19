# 通用 B2B 钩子与话术手册（全行业版）

**版本**：v3.1 | **适用**：实体商品、工业品、软件/SaaS、专业服务、物流、项目型销售等任何 B2B 业务
**配套**：`行业适配指南.md`（先选行业包、建好 offer 层）· `email_templates.md`（成稿骨架）

---

## ⚠️ 使用前必做：确认你的「卖什么 + 怎么起步」

本手册只提供**钩子结构与选择逻辑**。所有事实——你卖什么、差异在哪、客户怎么低门槛试用——
都来自首次建档的 `config/company_profile.json`，AI 不得补写或编造。

```
=== 事实确认流程 ===
IF profile 已 READY:
    {offer}        ← product.one_liner_en           （一句话定位）
    {usp}          ← product.differentiators[0..1]  （可验证差异）
    {entry_offer}  ← offer.entry_offer              （样品 / 试用 / 演示 / 免费诊断 / 试点 / 样板）
    {facts}        ← offer.key_facts                （起订量 / 上线周期 / 认证 / 交付时效 / 客户数）
    {cta}          ← offer.cta_question             （收尾问句）
    {proof}        ← offer.proof_points             （可公开案例，须授权或脱敏）
ELSE:
    → 回到 SKILL.md 首次建档门禁；缺哪项问哪项，不用"看起来合理"的数字顶替
```

**跨行业占位符对照**（写邮件时只换"词"，不换"结构"）：

| 通用占位 | 实体商品 | 工业品 | SaaS/软件 | 专业服务 | 物流 | 项目型 |
|---|---|---|---|---|---|---|
| `{entry_offer}` | 免费样品 | 按图打样 | 免费试用/试点 | 免费诊断/样稿 | 试走一票 | 样板/技术资料 |
| `{min_commitment}` | MOQ | 最小批量 | 最短订阅期 | 起步套餐 | 最低货量 | 最小项目额 |
| `{delivery_time}` | 打样/大货周期 | 交期 | 上线周期 | 交付周期 | 时效 | 工期/供货期 |
| `{proof}` | 合作客户数 | 认证/PPAP | 客户数/案例 | 结果案例 | 线路/仓点 | 参考项目 |

---

## 一、决策驱动（solution_tag）—— 11 个行业通用取值

背调的核心问题是："**这家客户做决定时最在意什么？**"答案就是 `solution_tag`。
它不随行业变化，随客户变化。脚本 `decision_maker_sender.py` 直接按它选开场句。

| solution_tag | 客户在意 | 典型信号（任何行业） |
|---|---|---|
| `compliance` | 合规、资质、可追溯 | 官网列认证/法规页；监管行业；招标要求资质 |
| `sustainability` | ESG、环保、可持续 | 有可持续报告/承诺；ESG 采购政策 |
| `quality_upgrade` | 品质/性能提升 | 在用低端方案；差评集中在质量/稳定性 |
| `cost` | 总成本 | 分销商/大批量采购；公开在比价；预算收紧新闻 |
| `speed` | 时效、上线快 | 有明确档期/上线节点；抱怨现供应商慢 |
| `low_commitment` | 低门槛试水 | 小公司/新品牌/新团队；首次尝试此类方案 |
| `innovation` | 新品、新方向 | 发布新产品线、进入新市场、融资后扩张 |
| `exclusive_custom` | 定制、独家、私有化 | 高端定位；强调 bespoke/私牌/私有部署 |
| `one_stop` | 少对接几家 | 供应链/工具分散；多个供应商在拼 |
| `dedicated_service` | 被重视、有人负责 | 中小客户；抱怨大供应商响应慢 |
| `strategic_scale` | 产能、规划、长期 | 连锁/集团/大项目；年度框架采购 |

> `need_tag` 是另一个维度：客户要的是**你哪条产品/服务线**，取值由你在
> `positioning.need_tags` 自定义（如 `line_a` / `line_b` / `multi` / `unknown`）。
> 两个标签都只能来自背调证据。

---

## 二、7 种通用钩子

每种钩子给出：适用信号 → 标题骨架 → 正文骨架（≤60 词）→ 对应 solution_tag。
骨架里的 `{...}` 必须被 profile 事实或客户事实替换，原样出现在外发邮件里即为事故。

### 2.1 补位扩展型（Expansion）
- **信号**：客户已有相邻产品/服务，但缺你这一块；或正在扩品类/扩功能/进新市场。
- **标题**：`{offer} for [Company]'s {their_new_area}` / `Filling the {gap} at [Company]`
- **正文**：
```
Hi {name},

[Company] now covers {their_current_area} — {offer} is the piece that usually sits next to it.
{usp}. {facts}.

{cta}
```
- **solution_tag**：`one_stop` / `innovation` / `open`

### 2.2 品质升级型（Upgrade）
- **信号**：客户在用低一档的方案；评论/社媒里出现质量、稳定性、效果相关反馈。
- **标题**：`A step up from {their_current_solution}` / `{usp_short} for [Company]`
- **正文**：先肯定客户现状，再给**一个可验证的对比事实**（不贬低现供应商）。
```
Hi {name},

{their_strength} stands out at [Company]. One area we could lift: {usp} — measurable, not a claim.
{entry_offer} available so your team can compare side by side.

{cta}
```
- **solution_tag**：`quality_upgrade`

### 2.3 成本/效率型（Efficiency）
- **信号**：分销商、大批量采购方、预算收紧、公开比价、在找替代供应商。
- **标题**：`{offer} — {fact_1}` / `A second option for {category} at [Company]`
- **正文**：直接给门槛与条款，**不写"competitive pricing"之类空话**。
```
Hi {name},

If [Company] wants a second option for {category}: {facts}.
{usp}.

{cta}
```
- **solution_tag**：`cost` / `low_commitment`

### 2.4 新方向型（New Initiative）
- **信号**：发布新产品线/新服务、融资、进入新市场、换了负责人。
- **标题**：`For [Company]'s {new_initiative}` / `{offer} for the {new_market} launch`
- **正文**：点出对方的新动作（证明做过功课），给一个能马上开始的入口。
```
Hi {name},

Saw [Company] is {new_initiative} — congratulations.
We {offer_short}; {usp}. Easy start: {entry_offer}.

{cta}
```
- **solution_tag**：`innovation` / `low_commitment`

### 2.5 合规/可持续型（Compliance & ESG）
- **信号**：监管行业、招标要求资质、官网有认证/ESG 页、目标市场有准入法规。
- **标题**：`{market}-ready {offer} for [Company]` / `Documented {category} for [Company]`
- **正文**：只列**你真实持有**的认证/资质，原文照写，不缩写不夸大。
```
Hi {name},

[Company]'s {compliance_focus} — noted. {cert_fact}. Documentation available before any commitment.
{facts}.

{cta}
```
- **solution_tag**：`compliance` / `sustainability`

### 2.6 时效/节点型（Timing）
- **信号**：客户有明确档期（旺季、上线日、项目节点、财年预算窗口、法规生效日）。
- **标题**：`Ready before {their_deadline}` / `{offer} — {delivery_time}`
- **正文**：把时间倒推写清（现在开始 → 何时交付/上线 → 赶上哪个节点），只用真实周期。
```
Hi {name},

Planning for {their_deadline}? Starting now means {delivery_time} → ready by {date}.
{usp}.

{cta}
```
- **solution_tag**：`speed`

### 2.7 定制/专属型（Bespoke & Dedicated）
- **信号**：高端定位、强调独家/私牌/私有化部署；或中小客户需要被重视的服务。
- **标题**：`Built around [Company]'s requirements` / `Dedicated {category} support for [Company]`
- **正文**：聚焦能力与流程，高端客户不先谈价格与起订门槛。
```
Hi {name},

[Company]'s {positioning} calls for something built to spec, not off the shelf.
{custom_capability}. One named contact from first call to delivery.

{cta}
```
- **solution_tag**：`exclusive_custom` / `dedicated_service` / `strategic_scale`

---

## 三、按客户类型选钩子（跨行业速查）

| 客户类型（任何行业都能对上号） | 首选钩子 | 话术方向 |
|---|---|---|
| 渠道商：分销商/代理/经销/转售 | 2.3 成本效率 / 2.1 补位 | 毛利空间、起步门槛、区域支持 |
| 品牌方/产品方：自己做产品的公司 | 2.2 品质升级 / 2.7 定制 | 可验证差异、定制能力 |
| 集成商/实施方/工程商 | 2.1 补位 / 2.6 时效 | 交付节点、技术资料、配合度 |
| 终端企业职能部门（IT/HR/采购/运营） | 2.4 新方向 / 2.3 效率 | 业务结果、上线周期、试点 |
| 中小企业/新公司 | 2.3 低门槛 / 2.7 专属 | 免费起步、有人负责 |
| 集团/连锁/大项目方 | 2.7 规模 / 2.5 合规 | 产能、合规文件、年度规划 |
| 强监管行业（医疗/食品/能源/金融） | 2.5 合规 | 证照原文、文件包先行 |
| 有明确档期（旺季/上线/工期） | 2.6 时效 | 倒推时间线 |

---

## 四、地区市场策略（只决定语气、语言和发送时段）

> 地区特点只是起点，**背调证据优先于地区刻板印象**。发信时段按客户当地时间，
> 下表"北京时间"仅为换算参考（夏令时需自行调整）。

| 地区 | 沟通风格 | 常见关注点 | 本地化 | 当地上午≈北京时间 |
|---|---|---|---|---|
| 🇺🇸 美国 | 直接、重效率 | 速度、ROI、灵活起步 | 英文 | 21:00–23:00（东部） |
| 🇬🇧 英国 | 礼貌、克制 | 资质、可靠性、长期合作 | 英文 | 16:00–18:00 |
| 🇩🇪 德国/DACH | 正式、重证据 | 认证、精确交付、数据 | 德语称呼与结尾（脚本自动）；可补 Xing | 15:00–17:00 |
| 🇫🇷 法国 | 正式、重关系 | 品质、独特性 | 法语称呼与结尾（脚本自动） | 15:00–17:00 |
| 🇮🇹 意大利 | 关系导向、家族企业多 | 品质、老板直接决策 | 意语称呼与结尾（脚本自动） | 15:00–17:00 |
| 🇪🇸 西班牙/🇵🇹 葡萄牙 | 关系导向 | 性价比、信任 | 当地语言更佳 | 15:00–17:00 |
| 🇳🇱 荷兰/北欧 | 非常直接 | 可持续、效率 | 英文即可 | 15:00–17:00 |
| 🇯🇵 日本 | 正式、决策慢 | 品质控制、细节、长期 | 日语更佳；先建立信任 | 08:00–10:00 |
| 🇦🇪 中东 | 关系与面谈 | 资质、可靠交付 | 英文；WhatsApp 常用 | 13:00–15:00 |
| 🇧🇷 拉美 | 关系导向 | 价格、本地支持 | 葡/西语；WhatsApp 常用 | 20:00–22:00 |
| 🇨🇳 国内 B2B | 关系与效率并重 | 案例、价格、响应速度 | 中文；微信/电话为主 | 09:00–11:00 |

**多语言搜索词模板**（`{offer}` = 你的核心词，按当地语言翻译后再用）：
```
英语   "{offer} distributor {country}" / "{offer} company {country}"
德语   "{offer} Händler Deutschland" / "{offer} Anbieter"
法语   "{offer} distributeur France" / "{offer} fournisseur"
意语   "{offer} distributore Italia" / "{offer} fornitore"
西语   "{offer} distribuidor España" / "{offer} proveedor"
日语   "{offer} 代理店" / "{offer} 導入事例"
```

---

## 五、禁用词与替代（全行业基线）

**标题禁用**：Partnership · Collaboration · Free!!! · Discount · Cheap · Guaranteed · Best · #1

**正文禁用**：competitive pricing · world-class · leading · revolutionary · guaranteed results ·
any absolute claim you can't prove · I came across · I'd love to · could be a great fit · we specialize in

| 空话 | 换成可验证的事实 |
|---|---|
| competitive pricing | 具体门槛或条款（`{min_commitment}`、付款方式） |
| high quality | 一个可测的指标（公差、良率、SLA、复购率） |
| fast delivery | 具体周期（`{delivery_time}`） |
| experienced team | 具体年限或案例（`{proof}`） |
| leading provider | 客户数、项目数、认证名 |
| partner | work with / support |

> 行业专属禁用词（如医疗的疗效宣称、食品的健康宣称、金融的收益承诺）在 `soul_seven_kit/SOUL.md`
> 与 `rules.notes` 里补充。

---

## 六、边界情况

- **同行/竞品**：命中 `targeting.competitor_markers` 即拦截；目标市场内有同类能力的公司，可按你的策略定位为"产能/交付补充伙伴"，由人工决定是否接触。
- **热线索**：客户已回复或主动询价 → 不自动回信，上报人工；需要身份与信用核验时交由独立的询盘后风控背调流程。
- **撞发**：同一域名同日多次触达 → 跳过并记录；一个老板多个公司 → 只发一封。
- **公司状态**：官网失效先查是否停业；已停业移除，暂停的标记暂停。
- **事实缺失**：profile 没有的数字、认证、案例一律不写，回去问用户。

---

## 七、钩子选择决策树

```
步骤1  profile 已 READY？否 → 回建档门禁
步骤2  背调 → need_tag（要你哪条线）+ solution_tag（最在意什么），各附一条证据
步骤3  选钩子
       compliance / sustainability    → 2.5 合规/可持续型
       quality_upgrade                → 2.2 品质升级型
       cost / low_commitment          → 2.3 成本效率型
       innovation                     → 2.4 新方向型
       speed                          → 2.6 时效/节点型
       exclusive_custom / dedicated_service / strategic_scale → 2.7 定制/专属型
       one_stop / open                → 2.1 补位扩展型
       unknown                        → 2.1 或 2.3 保守试探，跟进中补背调
步骤4  地区（§四）→ 语言、称呼、发送时段
步骤5  替换占位符：{offer}{usp}{entry_offer}{facts}{cta}{proof} 全部来自 profile
步骤6  自检（禁用词/≤60 词/每个数字可溯源）→ 整批交用户批准 → 发送
```
