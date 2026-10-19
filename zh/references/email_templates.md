# 冷邮件模板库（短平快风格 · 全行业通用骨架）

> 按 `solution_tag`（背调后确定的「客户最在意什么」）选模板。每个模板 ≤60 词（不含签名）。
>
> 本文件是**行业无关骨架**：产品/服务定位、卖点、起步方式、关键事实、联系方式全部来自
> 首次建档的 `config/company_profile.json`，AI 起草时替换；**禁止照抄示例，禁止编造档案里没有的数字或卖点**。
>
> **占位约定**
> | 占位 | 来源 | 实体商品示例 | SaaS 示例 | 服务示例 |
> |---|---|---|---|---|
> | `[公司名]` | 客户事实 | | | |
> | `[品类]` | `product.primary_keywords[0]` | stainless valves | HR software | SEO audits |
> | `[定位]` | `product.one_liner_en` | | | |
> | `[卖点N]` | `product.differentiators` | | | |
> | `[起步]` | `offer.entry_offer` | free sample | 14-day trial | free audit |
> | `[事实N]` | `offer.key_facts` | MOQ 50 pcs | setup in 2 days | fixed fee from €900 |
> | `[收尾]` | `offer.cta_question` | Worth a sample? | Open to a demo? | Want the audit? |
> | `[案例]` | `offer.proof_points` | （须授权或脱敏） | | |
> | `[WA号]` | `contact.whatsapp` | 未填则不放 WhatsApp 行 | | |

## 使用规则

1. **先背调，定 need_tag（要哪条线）+ solution_tag（最在意什么），再选模板**（见 research_guide.md）。
2. `[方括号]` 内容必须来自客户事实或已确认的 profile，缺了就问，不编。
3. 跟进邮件必须带新信息，禁止复制首封只改名字。
4. 仅当 profile 里有 WhatsApp 号时才放 WhatsApp CTA。
5. **禁用句式**：I came across / I thought / I'd love to / we specialize in / could be a great fit / happy to。
6. 语言匹配客户所在国当地语言；德/法/意称呼与结尾由脚本按地区自动本地化。

---

## 一、首次触达模板（按 solution_tag）

### 1.1 合规/资质优先 · `compliance` / `sustainability`

**主题**：Documented [品类] for [公司名]

> Hi [Name],
>
> [公司名]'s [合规/ESG 关注点] — noted. [卖点1：对应其关切的证书/资质原文]。
>
> • [事实1]
> • Documentation before any commitment
>
> [收尾] [WhatsApp 行，仅在有号时]

### 1.2 品质/差异优先 · `quality_upgrade` / `exclusive_custom`

**主题**：[卖点1 的短版] — for [公司名]

> Hi [Name],
>
> Why teams like [公司名]'s switch to us:
>
> • [卖点1]
> • [卖点2]
> • [事实1] · [事实2]
>
> [起步] available. [收尾]

### 1.3 低门槛起步 · `low_commitment` / `cost`

**主题**：An easy way to test [品类] — [公司名]

> Hi [Name],
>
> No big commitment needed to try us:
>
> • [起步]
> • [事实1] · [事实2]
> • [卖点1]
>
> [收尾]

### 1.4 时效/节点 · `speed`

**主题**：Ready before [客户的节点]

> Hi [Name],
>
> Planning for [客户的节点：旺季/上线日/工期/预算窗口]? Starting now → [交付/上线周期] → ready by [日期]。
>
> • [卖点1]
> • [事实1]
>
> [收尾]

### 1.5 新方向/扩展 · `innovation` / `one_stop`

**主题**：For [公司名]'s [新动作]

> Hi [Name],
>
> Saw [公司名] is [新动作：新产品线/新市场/融资/新项目]。[定位]，and [卖点1]。
>
> Easy start: [起步]。[收尾]

### 1.6 专属/规模 · `dedicated_service` / `strategic_scale`

**主题**：[品类] support built for [公司名]

> Hi [Name],
>
> [卖点1]. One named contact from first call to delivery; [事实1].
>
> [收尾]

### 1.7 通用探索 · `open` / `unknown`（背调信号不足时）

**主题**：[品类] for [公司名]

> Hi [Name],
>
> [定位]。What clients value:
>
> • [卖点1]
> • [卖点2]
> • [事实1]
>
> [收尾]

---

## 二、跟进邮件（差异化递进）

> ⚠️ 每封必须带新信息（新案例/新角度/新版本/新数据），禁止复制首封只换名字；遵守冷却期与单联系人频次规则。

### 2.1 第 1 封跟进（首封后按设定冷却天数）

**主题**：Re: [新信息关键词]

> Hi [Name],
>
> Quick follow-up. Recently [案例：须真实且可公开] for a [地区/行业] client — [结果]。
>
> [起步] still open. [WhatsApp 行]

### 2.2 第 2 封跟进（换新角度）

**主题**：[不同角度关键词]

> Hi [Name],
>
> Different angle: [新角度，如试点规模/定制方案/时间节点]。Helped a [客户类型] get [结果] starting with [起步]。
>
> Worth 5 minutes?

### 2.3 第 3 封跟进（轻量退出）

**主题**：Last note — [公司名]

> Hi [Name],
>
> Won't follow up again. If [品类] comes up on your side — we're here. [事实1]。
>
> [WhatsApp 行]

---

## 三、WhatsApp 首条消息（仅在有号时）

**首次触达**：
> Hi [Name], [一句针对对方的具体观察]. We provide [定位] — [事实1]. Want me to send a short overview?

**跟进/复购**：
> Hi [Name], quick update: [offer.repeat_hook]. Want me to send the details?

---

## 四、发出前自检

- [ ] 没有 "I came across / I thought / I'd love to / great fit" 这类废话？
- [ ] 正文 ≤60 词（不含签名）？
- [ ] 每个 bullet 都是事实/数字，且全部来自 profile，不是编的？
- [ ] 模板里的 `[...]` 已全部替换，没有残留占位？
- [ ] 行业合规（医疗/食品/金融等宣称限制）已核对？
- [ ] 联系方式只用建档确认过的；没有 WhatsApp 号就没硬放？
- [ ] 语言匹配客户国家、在客户当地上班时段发送？
- [ ] 签名与建档完全一致，未增减字段？
