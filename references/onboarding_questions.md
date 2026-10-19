# 首次建档采访问题清单（Onboarding Interview）

本技能是**全行业通用的脱敏模板**，不含任何真实公司信息，也不预设任何行业。AI 第一次加载时，必须用这份清单
逐项向使用者采集，写入 `config/company_profile.json`，再跑
`python3 scripts/onboarding.py check` 直到 `READY`。**严禁替用户编造任何值**；
使用者暂时答不上来的可选项先留空，但"必填"项必须拿到。

## 怎么用

0. `python3 scripts/onboarding.py start` 先看「装好后马上要补的信息」清单（三关 + 建议项，只读）。
1. `python3 scripts/onboarding.py init` 生成空白档案（不覆盖已有档案）。
   可选：先问用户属于哪类业务，`onboarding.py packs` 列出 13 个行业包，选中后
   `apply-pack <id>` 预填方法层建议（分层/角色/渠道/意图词），再逐项和用户改成他的说法。
   详见 `行业适配指南.md`。
2. 按下面顺序提问；能从用户一句话里拆出多个字段就一次问清，减少往返。
3. 直接编辑 JSON 写入，或用 `python3 scripts/onboarding.py ask` 走引导式提问。
4. 七件套写完跑 `python3 scripts/onboarding.py kit-check`（7/7 才算过）；全部完成后 `python3 scripts/onboarding.py check`，
   回读给用户、用户确认后 `attest`，出现 `READY` 才能做后续任务。确认后再改档案或七件套，需要重新回读确认再 `attest`。

## 必填字段（check 会卡这些）

| 字段 | 要问的问题 | 用在哪 |
| --- | --- | --- |
| `business.industry` | 一句话说说你所在的行业/赛道？（例："工业阀门出口""HR SaaS""跨境货代"） | 选行业包、复盘口径 |
| `business.offer_type` | 你卖的是有形产品、软件、人力服务、还是按项目成交？（physical_product / software / service / project / other） | 决定默认搜索渠道 |
| `company.brand_display` | 你邮件落款用的公司/品牌名是什么？ | 签名、主题 |
| `contact.founder_name` | 对外发件人姓名（署名）？ | 签名 |
| `contact.email` | 对外发件邮箱是哪个？ | 发件身份、回复 |
| `product.one_liner_en` | 用一句英文说清你卖的是什么？（例：`<your one-line positioning>`） | 邮件首句、定位 |
| `product.primary_keywords` | 客户会用哪 ≥3 个英文词搜你这类产品/服务？ | 搜索词矩阵核心 |
| `product.differentiators` | 你和别家最硬的 ≥2 个可验证差异？（性能/工艺/结果/时效/资质/服务…） | 邮件证据段 |
| `targeting.buyer_titles` | 你想触达的 ≥1 个决策角色？（procurement manager / CTO / HR director / owner…） | 角色词、词矩阵 |

## 强烈建议补全（不补也能激活，但定位会粗）

- `company.website` / `product_site`：主站与产品站（不同则分开填）。
- `contact.whatsapp`：WhatsApp 国际格式；`contact.signature_lines`：签名附加行。
- `product.alt_keywords`：近义/品类扩展词。
- **`offer.*`（成交入口层，所有邮件/WhatsApp 脚本都从这里取，强烈建议填）**：
  - `entry_offer`：客户低风险起步方式？（免费样品 / 14 天试用 / 免费诊断 / 试点 / 试走一票 / 样板）
  - `cta_question`：邮件最后一句英文问句？（例："Open to a 20-minute demo next week?"）
  - `key_facts`：2–4 条可对外的短事实（MOQ / 上线周期 / 认证名 / 交付时效 / 客户数——填事实，别写形容词）
  - `proof_points`：可公开的案例（须客户授权或已脱敏）；`repeat_hook`：老客户复购跟进一句话
  - 实体商品可继续用旧字段 `product.moq` / `sample_lead_time` / `bulk_lead_time`，`key_facts` 为空时自动兜底。
- `targeting.channel_keywords`：客户类型词（distributor / contractor / startup /
  clinic chain / importer / agency…）。
- `targeting.customer_levels`：自定义客户分层数组，每层
  `{name, desc, keyword_suffixes}`，搜索脚本据此生成各层词表。
- `targeting.target_regions`：目标市场（ISO 国家码，如 USA/GB/DE）。
- `targeting.languages`：发信语言（en/fr/de/es/it…），用于本地化。
- `targeting.exclude_keywords`：你的行业里**明确不是客户**的词（如个人消费者、
  维修、二手、教程、招聘站、某不做的品类），搜索与门禁都会排除。
- `targeting.competitor_markers`：同行/竞品的识别特征词（manufacturer / agency /
  software vendor…），防止把竞品当客户。
- `positioning.need_tags`：你的产品/服务线标签（背调时 need_tag 的取值）；
  需要"某线与某类客户互斥"之类规则时，写 `conflict_groups` / `tag_rules`。
- `rules.*`：`daily_limit`、`local_send_window`（收件人当地时间窗口，默认 `09:00-11:00,14:00-16:00`，
  `send_window.py table --me <你的时区>` 可查各市场对应的北京时间）、`same_contact_cooldown_hours`、
  `require_confirmed_email`、`notes`（自定义红线）。
- `search.social_platforms`：要用哪些社媒平台做免登录公开搜索（linkedin / instagram / facebook / youtube /
  tiktok / pinterest / x / threads / whatsapp / lemon8；留空 = 10 个全开），见 `social_media_playbooks.md`。

## Part B：灵魂七件套（`soul_seven_kit/`，7 份，全部必填）

`onboarding.py init` 已把 `references/soul_kit/` 下 7 份模板复制到
`soul_seven_kit/`。每份填 3–5 条具体内容（把「（例…）」示例换成你的真实做法），填完把文件顶部
`filled: false` 改成 `filled: true`，再跑 `onboarding.py kit-check`——只改 filled 不写真内容过不了。
填写参考：`soul_kit/填写参考_客户开发岗.md`。这 7 份定义「干活的这个 AI」本身，
和 Part A 的业务事实互补：

| 文件 | 要问用户填什么 |
|---|---|
| IDENTITY.md | 岗位一句话、服务谁、交付目标、明确边界、红线 |
| SOUL.md | 沟通语气、做事优先级、决策原则（不编造/留痕/不越权等） |
| AGENTS.md | 标准 SOP、**必须停下来找老板确认的刹车节点**、禁做事项、异常上报 |
| TOOLS.md | 每件工具/脚本/渠道何时用、怎么用、坏了用什么替代 |
| MEMORY.md | 活页工作笔记（客户库指针、重要决策、未决事项、踩坑） |
| USER.md | 老板的汇报频率/渠道/格式、审批粒度、沟通偏好 |
| HEARTBEAT.md | 每日/每周健康检查项（池子、发信量、退信、回复跟进、卡点） |

重点采访 IDENTITY 的边界红线、AGENTS 的人工刹车节点、USER 的汇报与
审批偏好——这三处最容易被泛泛填过，务必让老板给具体规则。

## 凭证（不进档案）

SMTP/IMAP 密码、授权码属于密钥，运行时用环境变量提供，**不要**写进
company_profile.json、脚本或对话记录：

```bash
export SMTP_HOST=...   SMTP_PORT=465   SMTP_USER=...   SMTP_PASS=...
# 退信扫描需要时：
export IMAP_HOST=...   IMAP_USER=...   IMAP_PASS=...
```

## 采访示例（仅演示问法，值为虚构占位）

**示例 A：工业零部件**
> AI：先帮你建档才能开始。你在什么行业、卖的是产品、软件、服务还是项目？
> 用户：做精密机加工零件出口，是产品。
> AI：落款的公司名、发件人姓名、邮箱是？
> 用户：Northwind Precision，Sam Lee，sam@northwind.example。
> AI：用一句英文描述你卖的东西？客户搜哪几个词？最硬的两个差异？
> 用户：CNC machined parts for automation OEMs；cnc machining / precision parts / machined components；
>       全检报告、ISO 9001。
> AI：客户怎么低风险起步？邮件结尾想问什么？
> 用户：按图免费打 3 件样；"Send a drawing and I'll quote within 48h?"

**示例 B：SaaS**
> AI：你在什么行业、什么交付形态？
> 用户：HR 入职软件，SaaS。
> AI：想找哪类决策人、哪些国家？客户怎么开始用？
> 用户：HR director 和 People Ops，先做英国和德国；可以免费试点一个团队 14 天。

填完后 AI 写入档案并运行 check，**逐项回读**给用户确认，用户明确同意后 `attest`，
`READY` 后再进入搜索/背调/发信流程。
