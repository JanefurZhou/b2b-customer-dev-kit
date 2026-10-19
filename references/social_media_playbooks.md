# 10 大海外社媒获客手册（全行业通用 · 免登录公开搜索优先）

> 平台：LinkedIn / Instagram / Facebook / YouTube / TikTok / Pinterest / X / Threads / WhatsApp / Lemon8
> 核心理念：**社媒是获客工具，不是运营平台。** 不追粉丝量、不追点赞，80% 时间花在搜索+触达，20% 花在内容辅助。
> 本技能的执行边界：**脚本只做免登录的公开搜索**（把 site: 搜索式交给 Google / Bing），从已被搜索引擎公开索引的页面里提取公司与决策人线索；
> **凡是需要注册/登录才能做的动作**（连接请求、DM、进群、看粉丝列表、点赞评论）一律标为「人工 · 需登录」，由用户本人决定是否做，本技能不自动执行。
> 社媒产出的每条线索，仍要走：官网 → 具名邮箱 → `filter --against` 查库去重 → 背调（S1/S2 证据）→ 定位 → 三道关，才能进入发信。

---

## 一、一条命令生成 10 平台公开搜索式

```bash
python3 scripts/search_customers.py social                 # 看 10 个平台：定位 / 公开搜索式 / 取什么 / 哪些动作需登录
python3 scripts/search_customers.py social --titles        # 30 个采购链职位词库（决策层 / 执行层 / 影响层）
python3 scripts/search_customers.py social --all --regions UK,DE --out social.txt
python3 scripts/search_customers.py social --platforms linkedin instagram --tier decision
python3 scripts/search_customers.py social --platforms youtube --urls   # 附 YouTube 站内搜索链接（公开页，无需登录）
```

- 词从哪来：品类/客户行业词 = `product.primary_keywords`（软件/服务业务按 `targeting.customer_industries` 改用客户锚点）；角色词 = `targeting.channel_keywords`；职位 = `targeting.buyer_titles` 优先，词库补位；竞品 = `targeting.reference_brands`。
- 平台开关：`search.social_platforms`（空 = 10 个全开）。
- 结果怎么用：搜索结果页 → 打开公开主页/公司页 → 取官网 → 回到主流程「第 1 步 搜索候选」的结果文件，统一走 `filter --against`。

## 二、平台定位速查

| 平台 | 星级 | 在闭环里的位置 | 免登录公开搜索能拿到 | 人工 · 需登录（本技能不执行） |
|---|---|---|---|---|
| LinkedIn | ⭐⭐⭐⭐⭐ | 找决策人 | 姓名、职位、公司页、官网；帖子里的采购/招标信号 | 连接请求、InMail、Sales Navigator |
| Instagram | ⭐⭐⭐⭐ | 找品牌/门店 | 简介官网链接、城市、stockist/wholesale 标注；竞品被 @ 的零售商 | 粉丝/关注列表、话题页滚动、DM |
| Facebook | ⭐⭐⭐ | 找群组/商家页 | 公开群组名与主题、商家页 About 的官网/邮箱/地址 | 进群、发帖、Messenger |
| YouTube | ⭐⭐⭐ | 评论区/频道挖买家 | 频道「商务合作」邮箱、外链官网、评论区自报身份的买家 | 评论、订阅 |
| TikTok | ⭐⭐⭐ | 短视频/评论区信号 | 简介官网、品牌名、评论区「哪里进货」账号 | 评论、私信 |
| Pinterest | ⭐⭐⭐ | 图版/长尾找品牌 | Pin 外链指向的品牌/店铺官网 | 收藏、私信 |
| X (Twitter) | ⭐⭐ | 需求对话监听 | 「looking for / recommend a supplier」需求帖账号 | 回复、私信 |
| Threads | ⭐⭐ | 与 IG 联动 | 同名账号 → 回 IG 公开页取官网 | 回复、私信 |
| WhatsApp | ⭐⭐⭐⭐ | **转化/跟进主场**（不是搜索源） | 官网/目录公开的 WhatsApp 商务号（只记录） | 所有发送都走第七步 wa_bulk 引擎 + 防封铁律 |
| Lemon8 | ⭐⭐ | 图文种草/新锐品牌 | 帖子提到的品牌名 → 回搜官网 | 评论、私信 |

## 三、采购链职位词库（30 个，三档）

`social --titles` 打印；LinkedIn 布尔式按 `--tier` 选档。档案里的 `targeting.buyer_titles` 永远排在词库前面。

| 档 | 作用 | 职位 |
|---|---|---|
| 决策层 decision | 拍板、批预算 | Owner · Founder · CEO · Managing Director · General Manager · Head of Purchasing · Procurement Director · VP Operations · Commercial Director · Category Director |
| 执行层 execution | 找供应商、比价、下单 | Buyer · Senior Buyer · Purchasing Manager · Procurement Manager · Sourcing Manager · Category Manager · Supply Chain Manager · Product Manager · Merchandiser · Vendor Manager |
| 影响层 influence | 提需求、做评估、影响选型 | Operations Manager · Quality Manager · Technical Director · Engineering Manager · Project Manager · Product Development Manager · Brand Manager · Marketing Manager · IT Manager · Office Manager |

触达顺序：先执行层（最懂需求、回复率高）→ 同时点名决策层（拍板）→ 影响层只用于补充证据（比如质量/技术要求）。软件/服务业务把「Head of Purchasing」类换成业务负责人（CTO、HR Director、Head of Marketing 等），写进 `buyer_titles` 即可。

LinkedIn 的 21 条布尔搜索式见 `references/linkedin_strategy.md`；`social` 子命令生成的是它们的「免登录 site: 版本」。

## 四、各平台打法（公开搜索 → 人工动作）

### 4.1 LinkedIn（找决策人）
1. `site:linkedin.com/in ("Buyer" OR "Purchasing Manager" OR "Owner") "<品类>" "<地区>"` → 列出决策人公开主页。
2. `site:linkedin.com/company "<品类>" <角色词> "<地区>"` → 公司页 → About 里的官网。
3. `site:linkedin.com/posts "<品类>" ("looking for" OR sourcing OR RFQ)` → 带采购信号的帖子 = **S2 证据**（见 research_guide 证据分级）。
4. 人工 · 需登录：连接请求（≤300 字符，先价值后请求，模板见 linkedin_strategy.md）。

### 4.2 Instagram（找品牌/门店）
1. **9 组话题标签**（由品类词自动生成；人工浏览话题页需登录，所以脚本只生成 `site:instagram.com "#标签"` 版）：`#<品类>` · `#<品类>wholesale` · `#<品类>supplier` · `#<品类>b2b` · `#<品类>store` · `#<品类>brand` · `#<地区><品类>` · `#<品类>design` · `#<品类>trade`。
2. **竞品粉丝挖掘（公开版）**：看竞品粉丝列表需要登录 → 不做；改用 `site:instagram.com "<竞品>" (stockist OR retailer OR "available at")` 找**公开 @ 竞品的零售商/经销商** —— 他们已经在卖同类产品，是最精准的买家。
3. 取：简介官网、城市、是否标 stockist/wholesale。
4. 人工 · 需登录：**DM 三句话**——①我是谁 + 为什么找你（引用你公开主页的一个具体事实）②一个可验证的事实（来自 `offer.key_facts`）③一个低门槛问题（`offer.cta_question`）。

### 4.3 Facebook（群组渗透五步法）
1. 找群：`site:facebook.com/groups "<品类>" (buyers OR wholesale OR B2B OR procurement)`。
2. 判群：公开群名/简介里有买家角色、近期活跃 → 记入候选群清单（不进群也能先判断）。
3. 人工 · 需登录：进群后**先给价值**（行业数据、规格对比、避坑清单），不发硬广。
4. 人工 · 需登录：对主动提问的买家私信，用 DM 三句话。
5. 回主流程：拿到公司名 → 官网 → 具名邮箱 → 查库。

### 4.4 YouTube（评论区挖买家）
- `site:youtube.com "<品类>" (review OR unboxing OR "how to choose" OR "factory tour")`；`--urls` 额外给站内搜索链接（公开页，无需登录）。
- 取：频道简介里的商务邮箱、外链官网；评论区里自报「我是某店/某公司采购」的人（**S2**，需回官网核实成 S1）。

### 4.5 TikTok / Pinterest / X / Threads / Lemon8
- TikTok：`site:tiktok.com "<品类>" (wholesale OR supplier OR "small business")`；评论区问「哪里进货」= 需求信号。
- Pinterest：Pin 的外链域名就是品牌/店铺官网，直接进候选。
- X：`site:x.com "<品类>" ("looking for" OR "recommend a" OR supplier OR RFQ)` 监听需求帖。
- Threads：账号多与 IG 同名，回 IG 公开页取官网。
- Lemon8：适合找新锐/年轻品牌，帖子里的品牌名 → 回搜官网。

### 4.6 WhatsApp（转化主场，不是搜索源）
- 公开搜索只用于**记录**官网上公开的商务号：`"<品类>" <角色词> "<地区>" ("wa.me" OR "WhatsApp Business")`。
- 何时真正发：按第七步 WhatsApp 触发条件（邮件已发 ≥3 封无回且未退信 / 退信无替代邮箱 / 高价值且公开 WA / 客户主动留号），并经 `wa_bulk_sender.py convert → validate → preview → harness` 与每日 200 条上限。

## 五、跨平台协同（同一客户，多渠道交叉触达）

一个客户最多 3 个渠道，按这个顺序，**每一步都要有上一步的结果才进行**：

1. 邮件（主渠道，具名决策人）→ 2. LinkedIn 连接（人工，同一决策人）→ 3. WhatsApp（只在触发条件命中时）。
Instagram / Facebook / YouTube 等主要用于**找到**客户和**补证据**，不作为同一客户的第四、第五条打扰渠道。
同一客户的任一渠道收到明确拒绝 → `csv_ops.py add_blacklist` → 全渠道停。

## 六、跟进节奏：社媒 1-3-7-21 与邮件 5 级冷却的分工

| 渠道 | 节奏 | 由谁计算 |
|---|---|---|
| 社媒（LinkedIn / IG / FB 私信，人工） | Day 1 破冰 → Day 3 价值（行业信息/规格对比）→ Day 7 案例（只用用户确认过的案例）→ Day 21 换渠道（邮件或 WA） | 人工记录在 notes：`social=li d1 2026-10-19` |
| 邮件（脚本） | 第 1 封 → 3 天 → 第 2 封 → 3 天 → 第 3 封 → 10 天 → 第 4 封 → 停通用邮箱（只走 LinkedIn / 个人邮箱）→ 第 5 封后邮件全停 | `csv_ops.py cooldown <email>`（`COOLDOWN_RULES = {0: 3, 1: 3, 2: 10}`） |
| WhatsApp（脚本 + 人工） | 首条 → 有回复才继续；无回复不追发第二条同类消息 | `wa_review.py` / `wa_contacts.csv` |

两套节奏**不叠加轰炸**：同一客户同一天只走一个渠道（`rules.same_contact_cooldown_hours`）。

## 七、证据分级（S1 / S2 / S3）——社媒线索尤其要分级

| 级 | 定义 | 社媒例子 | 能做什么 |
|---|---|---|---|
| S1 一手 | 客户自己官方渠道明确写的 | 官网写「wholesale enquiries」、公司 LinkedIn 页写明业务、官方账号发布的招标/采购帖 | 可直接作为 need_tag / solution_tag 依据 |
| S2 二手可信 | 第三方或员工个人公开信息，可交叉验证 | 员工个人帖说在找供应商、行业媒体报道、展会名录 | 可用，但要在 notes 记来源；最好再找一条 S1 |
| S3 弱信号 | 推测、评论区片言只语、无法核实 | 评论区一句话、相似账号推断、话题标签命中 | **不下结论** → 标 `need_review`，交用户拍板 |

写进 notes：`evidence=S1:https://...;S2:https://...`。详细规则见 `references/research_guide.md` 的「证据分级」。

## 八、合规与边界

- 只看公开页面，不绕过登录墙，不用自动化工具批量读取平台页面，不自动关注/加好友/私信。
- 平台条款与当地隐私法规（如 GDPR 合法利益评估、退订权）优先于本手册。
- 个人账号信息只取与业务联系相关的部分（姓名、职位、公司），不收集私人信息。
