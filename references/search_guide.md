# 客户搜索脚本指南（search_customers.py · 通用版）

> 本文件说明 `scripts/search_customers.py` 的搜索逻辑。配合
> `SOP_客户搜索详细流程.md`（方法论）与 `自循环引擎.md`（客户池不枯竭的核心）使用。
> **产品边界、品类词库、排除词全部来自你首次建档时填写的 `config/company_profile.json`**
> （`product.primary_keywords` / `product.one_liner_en` / `targeting.*`），
> 本技能不预置任何具体行业的词表作为默认值。见 SKILL.md 首次建档门禁与 `onboarding_questions.md`。

## 产品边界（搜索前必读）

先在建档时明确三件事：

1. **你卖什么**：用 `product.primary_keywords` 表达（核心产品词 + 常见关联词/同义词，英文）。
2. **你的目标客户是谁**：用 `targeting` 表达（客户类型、地区、决策角色）。
3. **谁不是你的客户**：建档时列出"相邻但无关的品类/角色"作为排除词；竞品判定按
   "同行语义 + 竞品地区"双条件，不用公司名或地区一刀切。

以上缺失时，脚本应拒绝运行（首次建档门禁），避免用占位词盲搜。

## ♻️ 自循环引擎（客户池不枯竭 · 核心跃迁）

把"一次性扩面搜索"升级为"长期自运转的客户获取引擎"（四维轮换：高度 / 广度 / 深度 / 远度，不一次打光）：

1. **客户池保底**：客户库（`data_import.py` 导入的自有客户 + SaaS 导出 + 搜索入库）里可发冷开发候选 < 硬红线**100** 或 可发天数 < 提前量**30 天** → 自动补池+预警（三个数都是可调默认值）。
2. **四维轮换**：深度 d1 公司 → d2 决策人 → d3 存量深挖（最快）→ 远度 地区由近到远 → 高度 客户层级由高到低 → 广度 core/wide/max（最慢），状态记在 `search_state.json`，走遍不重打。详见 `references/自循环引擎.md`。
3. **内置调度器**：`schedule` 常驻每日自动跑闭环，脱离搜索引擎也能独立产出搜索词。

```bash
# 全自动：起常驻调度器（每日 09:00 自动检查池→补池→轮换）
python3 scripts/search_customers.py schedule --at 09:00 --floor 100 --ahead-days 30
# 手动补池：看池位 + 产出今日搜索词
python3 scripts/search_customers.py replenish --emit queries_today.txt
# 看轮换进度
python3 scripts/search_customers.py status
```

> 完整方法论、长期运转 SOP、参数详解 → `references/自循环引擎.md`。

## 为什么分级入库（旧脚本瓶颈）

| 瓶颈 | 旧做法 | 后果 |
|------|--------|------|
| 取数上限太低 | 只取前 80 条 | 大量结果没被处理 |
| 品类口径混杂 | 混进建档范围外的相邻品类 | 非目标客户污染候选池 |
| 邮箱门槛太高 | 必须非通用邮箱才入库 | 大量只有 info@ 的优质客户被丢弃 |

## 核心机制

1. **全量域名去重后处理**：`filter_and_grade()` 按【域名】去重（同站多页只算 1 个），不设截断上限。
2. **范围门禁**：标题/正文命中建档时配置的无关品类词 → 自动拦截（可配置的非目标关键词表）。
3. **竞品判定收窄**：仅当**同时命中竞品地区（建档定义）+ 同行语义（`competitor_markers`，如 manufacturer / agency / software vendor）**才排除；目标市场公司默认是客户。
4. **分级入库 A/B**：
   - **A 级**：有具名邮箱（如 first.last@）→ 直发
   - **B 级**：只有 info@/contact@/sales@ 等通用邮箱 → 入库标记「需 LinkedIn 找决策人 / email_guesser 补具名邮箱」
   - **none**：无邮箱 → 入库标记「需官网/LinkedIn 补邮箱」

## 客户光谱（高度：由高价值到长尾 · 层级名按你的行业改）

客户光谱 = `targeting.customer_levels`，每层 `{name, desc, keyword_suffixes}`。行业包（`onboarding.py apply-pack <id>`）可预填一套起点，
再由你改成真实客户类型。下面是同一骨架在不同行业的样子：

| 行业 | L1（最近、最易成交） | L2 | L3 | L4（更远、需要培育） |
|---|---|---|---|---|
| 实体商品出口 | 进口商/分销商 `importer, distributor` | 品牌方 `brand, private label` | 零售 `retailer, store chain` | 电商/项目采购 |
| 工业品 | OEM `OEM, machine builder` | 工业分销 `industrial distributor` | 集成/工程商 `system integrator` | 终端工厂 `plant` |
| SaaS/软件 | ICP 公司 `<industry> company` | 在用竞品 `"<competitor> customer"` | 增长信号 `hiring, raised funding` | 实施伙伴 `implementation partner` |
| 专业服务 | 中小企业 `SME` | 扩张期 `expanding to, new office` | 中大型职能负责人 `head of` | 转介伙伴 `partner agency` |
| 物流 | 进口/贸易商 `importer` | 电商卖家 `Amazon seller` | 出口制造商 `exporter` | 项目物流 `project cargo` |
| 项目型 | 总包 `general contractor` | 设计方 `architect` | 业主 `developer` | 分销/安装 `installer` |

> 「我们能提供什么」写在 `product_knowledge.md` §四，每层对一个真实能力 + 首选钩子，不在这里写死。

> 用 `--levels` 只跑部分层级：`python3 search_customers.py queries --levels L1_core,L2_growth   # 层名 = 你 customer_levels 里的 name`

## 5 个正交轴（--breadth wide/max 启用）

这些轴**不**与「客户×品类×地区」全组合（会爆炸），而是限定采样挂载到代表品类上：

| 轴 | 搜什么 | 要找的客户 |
|----|--------|-----------|
| **① scene 场景/用途** | `<use-scene-keyword>`：你的产品/服务被使用的场景词 | 按场景采购的客户 |
| **② intent 采购意图** | 通用：looking for vendor / RFP / alternative to ...；行业包追加：low MOQ / free trial / tender ... | 正在找供应方的活跃客户 |
| **③ channel 渠道/平台** | site:linkedin / g2 / clutch / 行业 B2B 平台 ...（按行业包或自填） | 藏在特定平台的客户 |
| **④ niche 细分定位** | `<niche-keyword>`：你行业的细分/定位词 | 垂直定位的客户 |
| **⑤ cert 认证/合规** | `<cert-keyword>`：你行业真实通行的认证/合规词 | 合规敏感的客户 |

## 品类词库（从档案生成，不要硬编码）

品类词库不是固定的，按 `product.primary_keywords` 展开，每个核心词至少配：

- **核心词**：`<your-core-term>`
- **同义词/口语叫法**：买家实际会搜的词
- **关联词**：相邻但仍在你目标范围内的品类词
- **场景词**：`<use-scene-keyword>`
- **时间窗口词**（如适用）：`<peak-season / budget-cycle / tender-season keyword>`

> 展开原则：同义词宁多勿漏；相邻但你不做的业务放进**排除词**而不是搜索词。

## 渠道配方（channels 子命令）

`python3 search_customers.py channels` 列出 15 个发现渠道，▶ 标记的是按你的行业包 / `business.offer_type`
默认会生成的渠道。directory / tender / review / events 搜到的是**名录页、招标页、评测页**——它们是线索来源，
要先从页面里取出公司名、再反查官网，`filter` 不会把这些页面本身当客户入池：

| 渠道 | 适合 | 渠道 | 适合 |
|---|---|---|---|
| social 社媒/职业网络 | 全行业 | tender 公开招标 | 全行业（项目/机构尤佳） |
| hiring 招聘信号 | 全行业（软件/服务尤佳） | directory 行业目录/协会 | 全行业 |
| events 会议名录 | 全行业 | media 新闻/融资/扩张 | 全行业 |
| competitor 竞品逆向 | 全行业 | maps 地图/本地目录 | 实体/服务/项目 |
| customs 海关数据 | 实体商品/物流 | rfq 采购平台买家端 | 实体/项目 |
| exhibition 展会名录 | 实体/项目 | review 评测站 | 软件/服务 |
| partners 生态伙伴 | 软件/服务/项目 | ecommerce 独立站卖家 | 实体商品 |
| gift 礼品渠道 | 实体商品（需 `--ch gift` 手动指定，不进默认） | | |

指定渠道：`channels --ch tender hiring --regions UK,Germany --out ch.txt`；
固定默认渠道：在 profile 写 `search.channels`。

## 使用方法

### A. 生成搜索词（交给搜索引擎/浏览器工具逐条查询）
```bash
# 按地区分批跑（推荐，避免一次太多）
python3 search_customers.py queries --regions USA --breadth max --out q_usa.txt
python3 search_customers.py queries --regions UK,Germany --breadth wide --out q_eu.txt

# 按层级 + 地区聚焦
python3 search_customers.py queries --regions USA --levels L1_core --breadth max --out q.txt
```
搜索时排除平台（alibaba/made-in-china/globalsources/etsy 等集市与社媒平台，脚本内置 PLATFORM_BLOCKLIST，可按需要增补）。

### B. 渠道发现式（社媒/地图/海关/RFQ/行业媒体/垂直渠道）
```bash
python3 search_customers.py channels --ch <channel-key> --regions USA --out ch.txt
python3 search_customers.py channels            # 列出全部渠道说明
```

### C. 过滤 + 库增量去重 + 范围门禁 + 分级
```bash
# 强烈建议带 --against 查库，避免重复开发已有客户
python3 search_customers.py filter results.json --against <main-customer-db.csv> --out candidates.csv
```
`results.json` 每条结构（字段可缺省）：
```json
[{"url":"...","title":"...","snippet":"...","emails":["..."],
  "is_competitor":false,"customer_type_hint":"","region_hint":""}]
```
输出 `candidates.csv` 字段：domain, url, brand, **email_grade(A/B/none)**, best_email, all_emails, region_hint, customer_type_hint, **next_action**, note

### D. 非目标复核
```bash
python3 search_customers.py audit-category candidates.csv
```
挑出疑似建档范围外的记录，**只标不改**，人工背调确认后再处理。

## 与主流程对接（闭环）

搜索候选 → **范围门禁**（不在 targeting 范围直接拦）→ **背调**（research_guide.md）→ 确定 **need_tag** → **查重**（`csv_ops.py check` / cross_brand_check）→ 通过后入备用池 → 撰写发信。

- **A 级**候选：背调后可直接进撰写发信。
- **B 级**候选：先用 `email_guesser.py` + LinkedIn 补具名邮箱，再发信（避开通用邮箱高退信率）。

## 排除规则速查（平台部分通用；品类部分按你的行业配置）

| 类别 | 命中即排除 |
|------|-----------|
| 平台/集市 | alibaba/aliexpress/made-in-china/1688/globalsources/dhgate/amazon/ebay/temu/shein/etsy/faire/indiamart ...（按实际增补） |
| 目录/博客/无效页 | /blog/ /news/ /category/ /tag/，blog./news./wiki. 子域，pinterest/youtube/reddit/wikipedia/yellowpages/yelp |
| 非目标品类 | **建档时自定义**：把相邻但无关的品类英文词写进非目标关键词表（不要在本文件里固化任何行业的清单） |
| 同行/竞品 | 同时命中建档定义的竞品地区（如相应 TLD/国家词）+ `competitor_markers`（如 manufacturer / agency / software vendor） |
| 域名重复 | 同一域名只保留第 1 条 |
