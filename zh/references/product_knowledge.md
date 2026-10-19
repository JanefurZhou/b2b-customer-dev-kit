# 产品/服务知识库模板（由你填写，全行业通用）

> 这是一份**空白模板**。本 Skill 不内置任何公司或行业的产品事实。
> 请把 `<...>` 替换为你自己的真实信息；不适用的小节直接删除。
> 「产品」在本 Skill 里泛指你卖的东西：实体商品、零部件、软件、专业服务、物流方案、工程项目能力都算。
> AI 起草邮件、提炼钩子时只引用这里和 `config/company_profile.json` 的内容，不得自行编造。

---

## 一、你卖什么（产品/服务线）

> 每条线一行。`need_tag` 列就是背调时给客户打的「要你哪条线」标签，
> 同步填进 `positioning.need_tags`。

| need_tag | 名称 | 交付形态 | 一句话说明（英文，可直接进邮件） | 典型客户 |
|---|---|---|---|---|
| `line_a` | <offer-line-1> | <physical / software / service / project> | <one-liner> | <customer-type> |
| `line_b` | <offer-line-2> | <...> | <one-liner> | <customer-type> |

---

## 二、可验证的核心卖点（差异化）

> 每条卖点都要能被客户验证（证书、数据、案例、样品、试用、演示）。
> 前两条同步填入 `product.differentiators`。

### 2.1 核心差异
- <与常见替代方案相比的真实差异，写可测量的点>

### 2.2 质量与合规
- <认证名称原文 / 检测报告 / 安全与数据合规 / 行业资质——只写真实持有的>

### 2.3 交付能力
- <起步门槛 min_commitment：MOQ / 最低合同额 / 最短订阅期>
- <交付周期 delivery_time：打样+大货 / 上线周期 / 项目工期 / 运输时效>
- <产能或服务容量：月产能 / 同时服务客户数 / 团队规模>

### 2.4 定制与研发
- <是否支持定制、私牌、私有化部署、专属方案；流程与周期>

### 2.5 服务与支持
- <售后、SLA、驻场、培训、本地化支持、账期——按实际填写>

---

## 三、成交入口（offer 层，填进 profile.offer）

| 字段 | 你的真实值 | 说明 |
|---|---|---|
| `entry_offer` | <free sample / 14-day trial / free audit / pilot / site visit> | 客户零风险或低风险起步的方式 |
| `cta_question` | <Open to a 20-minute demo next week?> | 邮件最后一句问句 |
| `key_facts` | <2–4 条短事实> | 例：MOQ 50 pcs · setup in 2 days · ISO 9001 certified |
| `proof_points` | <可公开案例> | 须客户授权或已脱敏 |
| `repeat_hook` | <our 2027 range is ready / v3 is live> | 老客户复购跟进用 |

---

## 四、产品/服务 × 客户类型匹配

> 列出你最想开发的 3–7 类客户，对每类写清「推哪条线 + 用哪个卖点 + 首选钩子」。

| 客户类型 | 推荐线（need_tag） | 切入卖点 | 首选钩子（industry_playbooks §二） |
|---|---|---|---|
| <customer-type-1> | <line_a> | <differentiator> | <2.x> |
| <customer-type-2> | <line_b> | <differentiator> | <2.x> |

---

## 五、时间窗口（如适用）

> 季节、财年预算、招标周期、展会、法规生效日、产品发布节奏……有就写，没有就删本节。
- 关键窗口：<window>
- 倒推节奏：<from first contact → trial/sample → decision → delivery>

---

## 六、差异化话术库（英文，必须基于第二节事实）

| 钩子类型 | 英文话术 |
|---|---|
| 核心差异 | <your measurable difference> |
| 起步门槛 | <min_commitment fact> |
| 交付时效 | <delivery_time fact> |
| 定制能力 | <customisation fact> |
| 合规/资质 | <certification fact，须有证书> |
| 案例 | <proof point，须授权> |

> 这些是 AI 起草邮件的**事实素材**；最终是否使用、怎么措辞，由你审核草稿后决定。

---

## 七、禁用词与行业合规补充

通用基线见 `industry_playbooks.md` §五。在此补充你所在行业的禁用/必披露表述，例如：
- 医疗/健康：不得做疗效或诊断宣称
- 食品：不得做健康功效宣称；过敏原与标签按进口国法规
- 金融/投资：不得承诺收益
- 软件：安全认证只写已获得的；涉及个人数据须说明合规依据
- <your-industry-specific rule>
