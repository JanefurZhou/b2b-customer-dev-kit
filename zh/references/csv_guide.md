# CSV数据层详细指南

> 本文档是SKILL.md的补充，包含CSV字段定义、脚本参数详解和常见问题。

> **编码**：所有 CSV 以 UTF-8（带 BOM）写出，Excel 可直接双击打开；读取时有无 BOM 都兼容，GB18030 的旧表请先用 `data_import.py` 导入。

## 一、文件结构

```
data/
├── sent_history.csv   — 发送记录（发后必写）
├── blacklist.csv      — 死邮箱/禁发名单
├── wa_contacts.csv    — WhatsApp联系人
├── success_cases.csv  — 成功案例（含完整客户档案+痛点确认+获客渠道）
└── pipeline.csv       — 备用池（已完成背调的客户储备，v5新增）
scripts/
├── csv_ops.py         — CSV操作脚本（增删查改+冷却期+排重+备用池管理）
└── email_dashboard.py — 邮件追踪看板（含成功案例复盘模块）
```

## 二、CSV字段定义

### 2.1 sent_history.csv

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| email | string | 收件邮箱（小写） | buyer@brand.example |
| brand | string | 客户公司/品牌名 | BrandName |
| send_date | date | 发送日期 | 2026-06-07 |
| subject | string | 邮件标题 | <your one-line value angle> for <Brand> |
| need_tag | enum | 需求标签（由背调决定；品类标签集合在建档时按自己行业自定义） | <line_a> / <line_b> / multi / unknown |
| followup_count | int | 跟进次数（0=首次） | 0 |
| last_followup_date | date | 最近跟进日期 | 2026-06-07 |
| status | enum | 当前状态 | sent / bounced / replied / permanent_stop（冷却期不落库，由 `cooldown` 命令按日期实时计算） |
| notes | string | 备注信息（背调发现/客户反馈/特殊要求） | 客户说Q3再联系; 需要ISO 9001证书 |

**need_tag 取值说明**：
> need_tag = 客户要你**哪条**产品/服务线，取值由你在 `positioning.need_tags` 自定义（与 `product_knowledge.md` §一一致）。
- `<line_a>` / `<line_b>` …：你自己的产品/服务线
- `multi`：要多条线/整体方案
- `review`：信号矛盾，待人工复核
- `unknown`：背调信息不足，保守推通用方案

客户「最在意什么」不写在 need_tag 里，而是 `solution_tag`（11 个通用决策驱动，见 `industry_playbooks.md` §一），
存放在发信 JSON 的 `solution_tag` 字段或 notes 里。

**notes字段说明**：
- 记录背调发现、客户反馈、特殊要求、跟进约定等
- 多条备注用`; `分隔
- `csv_ops.py check <email>` 会返回所有历史备注
- 发信前必须检查notes，按备注调整策略

**status流转**：
```
sent → bounced（退信）/ replied（回复）
sent → permanent_stop（转WA/永久停发）
（"冷却中"不是存储状态：用 `csv_ops.py cooldown <email>` 实时计算 in_cooldown / action）
bounced → 自动加入blacklist
```

### 2.2 blacklist.csv

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| email | string | 禁发邮箱 | dead@brand.example |
| brand | string | 客户公司/品牌名 | BrandName |
| reason | string | 原因 | 退信 / 域名失效 / 停业 / wa_only / 非目标 |
| date | date | 确认日期 | 2026-06-07 |

**reason取值说明**：
- `退信`：邮件被退回（邮箱不存在/已满）
- `域名失效`：客户官网已下线
- `停业`：客户已关闭
- `wa_only`：客户转WA渠道，停用邮件
- `非目标`：不属于目标客户群

### 2.3 wa_contacts.csv

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| wa_number | string | WhatsApp号码 | +<country-code-number>（E.164 格式） |
| brand | string | 客户公司/品牌名 | BrandName |
| contact_name | string | 联系人 | John |
| source_date | date | 录入日期 | 2026-06-07 |
| status | enum | 状态 | pending / wa_only / replied / self |

**status取值说明**：
- `pending`：已获取WA号，尚未联系
- `wa_only`：已确认WA渠道，邮件停发
- `replied`：WA上已获回复
- `self`：客户主动添加

## 三、csv_ops.py 命令详解

### 3.1 环境设置

```bash
# 设置数据目录（默认data/）
export B2B_DATA_DIR=data
```

### 3.2 check — 发前必查（最常用）

**语法**：`python3 scripts/csv_ops.py check <email>`

**返回JSON字段**：
| 字段 | 说明 |
|------|------|
| email | 查询的邮箱 |
| sent | 该邮箱的发送记录列表 |
| sent_count | 已发次数 |
| blacklisted | 是否在黑名单 |
| blacklist_reason | 黑名单原因 |
| wa_only | 是否为WA专属 |
| can_send | 当前是否可发送 |
| in_cooldown | 是否在冷却期 |
| cooldown_remaining | 冷却剩余天数 |
| **notes** | **该邮箱的所有历史备注（按时间排列）** |

**使用场景**：每次发信前必须运行，一条命令完成查重+查备注。

### 3.3 add_sent — 追加发送记录

**语法**：`python3 scripts/csv_ops.py add_sent <email> <brand> <subject> <need_tag> [notes]`

**参数**：
- `email`：收件邮箱
- `brand`：客户公司/品牌名
- `subject`：邮件标题（含空格用引号包裹）
- `need_tag`：需求标签（由背调决定；枚举在建档时按自己行业定义）
- `notes`：可选，备注信息（背调发现/特殊要求等）

**自动计算**：
- `send_date`：自动取当天日期
- `followup_count`：自动根据已有记录计算（0=首次，1=第2封...）

### 3.3.5 add_note — 追加备注

**语法**：`python3 scripts/csv_ops.py add_note <email> <note>`

**用途**：给该邮箱最新一条发送记录追加备注。多条备注用`; `分隔。

**使用场景**：
- 背调发现特殊信息，需要下次发信时注意
- 客户回复中提到特殊要求（如"Q3再联系""需要资质文件"）
- 记录退信原因、跟进约定等

### 3.4 add_blacklist — 加入黑名单

**语法**：`python3 scripts/csv_ops.py add_blacklist <email> <brand> <reason>`

### 3.5 add_wa — 追加WA联系人

**语法**：`python3 scripts/csv_ops.py add_wa <wa_number> <brand> <contact_name> [status]`

**参数**：`status`可选，默认`pending`

### 3.6 mark_bounced — 标记退信

**语法**：`python3 scripts/csv_ops.py mark_bounced <email>`

**自动操作**：
1. sent_history.csv中该邮箱status改为`bounced`
2. 自动添加到blacklist.csv（reason=bounce）

### 3.7 mark_replied — 标记回复

**语法**：`python3 scripts/csv_ops.py mark_replied <email>`

### 3.8 mark_wa_only — 转WA渠道

**语法**：`python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>`

**自动操作**：
1. sent_history.csv中该邮箱status改为`permanent_stop`
2. wa_contacts.csv中添加记录（status=wa_only）

### 3.9 cooldown — 冷却期检查

**语法**：`python3 scripts/csv_ops.py cooldown <email>`

**冷却期规则**：
| followup_count | 冷却天数 | 说明 |
|----------------|---------|------|
| 0 | 3 | 第1封后等3天 |
| 1 | 3 | 第2封后等3天 |
| 2 | 10 | 第3封后等10天 |
| 3 | 永久停通用邮箱 | 第4封起仅LinkedIn/个人邮箱 |
| ≥4 | 永久停发 | 第5封起仅WA/个人邮箱 |

**返回字段**：
| 字段 | 说明 |
|------|------|
| can_followup | 是否可跟进 |
| in_cooldown | 是否在冷却期 |
| cooldown_remaining | 冷却剩余天数 |
| next_eligible_date | 下次可发日期 |

### 3.10 cross_brand_check — 跨品牌排重

**语法**：`python3 scripts/csv_ops.py cross_brand_check <domain>`

**参数**：`domain`可以是`brand.example`或`@brand.example`格式

**返回字段**：
| 字段 | 说明 |
|------|------|
| found | 是否找到匹配 |
| matches | 匹配记录数 |
| brands | 已发送的品牌列表 |

### 3.11 stats — 数据统计

**语法**：`python3 scripts/csv_ops.py stats`

**返回字段**：sent_total, sent_by_status, blacklist_total, wa_contacts_total, unique_brands, unique_emails

### 3.12 success_cases.csv — 成功案例管理（v5新增）

**字段定义**：
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| email | string | 客户邮箱 | john@brand.example |
| brand | string | 客户公司/品牌名 | BrandName |
| contact | string | 联系人姓名 | John Doe |
| region | string | 地区/国家 | US |
| need_tag | string | 需求标签（你自定义的产品/服务线） | line_a |
| first_sent_date | date | 首次发送日期 | 2026-06-15 |
| reply_date | date | 回复日期 | 2026-06-18 |
| order_date | date | 下单日期 | 2026-07-01 |
| order_amount | float | 成交金额(USD) | 15000 |
| success_points | string | 成功要点（用户确认的痛点） | 1.个性化钩子 2.决策人具名发信 |
| email_subject | string | 邮件标题 | Documented valves for BrandName |
| hook_type | string | 钩子类型（= solution_tag，11 个通用决策驱动之一） | compliance |
| language | string | 邮件语言 | EN/IT/DE/FR/ES/JP/NL/PT |
| source_channel | string | 获客渠道 | LinkedIn/展会/招标/竞品逆向 |
| won_channel | string | 成单渠道（email / wa；空=未标，wa_review 按 brand 关联兜底） | email |
| company_info | json | 公司背景信息 | {"founded":"1990","size":"50-100"} |
| contact_phone | string | 联系人电话 | +1-555-1234 |
| company_address | string | 公司地址 | 123 Main St, NY |
| website | string | 官网 | https://brand.example |
| social_linkedin | string | LinkedIn | https://linkedin.com/company/brand |
| social_instagram | string | Instagram | @brand |
| social_facebook | string | Facebook | facebook.com/brand |
| social_twitter | string | Twitter/X | @brand |
| whatsapp | string | WhatsApp号 | +1-555-1234 |
| products_info | json | 客户业务信息（背调结论） | {"main_offerings":"...","current_solution":"...","need_tag":"line_a"} |
| notes | string | 备注 | |

**相关命令**：
```bash
# 添加成功案例（含完整客户档案）
python3 scripts/csv_ops.py add_success <email> <brand> <contact> <order_amount> <success_points> \
  --region US --need_tag line_a --source_channel LinkedIn \
  --company_info '{"founded":"1990"}' --whatsapp "+1-555-1234"

# 列出成功案例（可按地区/需求标签/渠道筛选）
python3 scripts/csv_ops.py list_success [--region US] [--need_tag line_a] [--channel LinkedIn]

# 复盘成功案例（提炼成功要点，供启动开发前学习）
python3 scripts/csv_ops.py review_success
```

### 3.13 pipeline.csv — 备用池管理（v5新增 ⭐）

**字段定义**：
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| email | string | 客户邮箱 | buyer@brand.example |
| brand | string | 客户公司/品牌名 | BrandName |
| region | string | 地区/国家 | US |
| need_tag | string | 需求标签（已完成背调，取值见 positioning.need_tags） | line_a |
| status | enum | 状态 | ready / pending / disqualified / used |
| priority | enum | 优先级 | HIGH / MEDIUM / LOW |
| research_done | bool | 是否完成背调 | true |
| added_date | date | 加入备用池日期 | 2026-07-09 |
| notes | string | 备注 | 背调完成，需要资质文件 |

**status取值说明**：
- `ready`：已完成搜索+背调+需求定位，可直接发送
- `pending`：仅完成搜索，待背调和需求定位
- `disqualified`：不合格（未通过验证/黑名单/已关闭）
- `used`：已从备用池取出发送

**相关命令**：
```bash
# 检查备用池状态（储备量是否充足）
python3 scripts/csv_ops.py pipeline_check
# 返回：ready_count, pending_count, shortage, need_supplement

# 添加到备用池（已完成背调）
python3 scripts/csv_ops.py add_pipeline <email> <brand> <region> <need_tag> [priority] [notes]

# 列出备用池（可按状态/地区筛选）
python3 scripts/csv_ops.py list_pipeline [--status ready] [--region US]

# 从备用池取出发送（标记为used）
python3 scripts/csv_ops.py use_pipeline <email>
```

**备用池管理规则**：
- 最低储备量：100家（7天储备），建议300-500家（月度储备）
- 检查频率：每周日22:00全面检查，每日发送前确认可用
- 补充触发：储备低于50%时立即补充
- 协同逻辑：备用池储备→每日消耗→储备降至0→补充任务启动→补充完成

## 四、常见问题

**Q：CSV文件不存在怎么办？**
A：脚本会自动创建。首次运行时如果data/目录为空，add_sent/add_blacklist/add_wa会自动创建带header的CSV文件。

**Q：同一品牌多个邮箱怎么处理？**
A：check命令按邮箱维度查询。同一品牌不同邮箱是独立记录，但cross_brand_check按域名维度查重，能捕获同域名下不同邮箱。

**Q：冷却期天数可以调整吗？**
A：可以。修改 csv_ops.py 中的 `COOLDOWN_RULES` 常量（默认 `{0: 3, 1: 3, 2: 10}` 天）；停通用邮箱/全部停发的封数分别由 `MAX_GENERIC_FOLLOWUP`（默认 3）和 `MAX_TOTAL_FOLLOWUP`（默认 4）控制。改完后 §3.9 的表格要同步更新。

**Q：LLM直接读写CSV行不行？**
A：不行。LLM解析CSV容易出错（引号/逗号/换行），且Coze会话间状态不持久。必须用脚本操作。
