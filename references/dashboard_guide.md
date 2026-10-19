# 邮件追踪看板使用指南

> 生成可视化HTML看板，追踪客户池、发信进度、退信、回复、成功案例、需求标签、跟进阶段，并汇总 WhatsApp 触达清单。

## 生成看板

```bash
python3 scripts/email_dashboard.py <data.json> [output.html] [title]
```

运行后除生成 HTML 看板外，还会在同目录导出 **`wa_targets.json`**（WhatsApp 触达清单），供后续 WhatsApp 开发信流程直接调用。

## 看板包含的模块

1. **客户池概览条** — 客户池总量（唯一）、已触达/覆盖率、备用池储备、已转WA、黑名单，并带开发进度条
2. **成功案例卡片墙**（永远置顶）— ✅已确认 / ⏳待确认痛点，点击展开完整客户档案；带 WhatsApp 号的老客户卡片头部有可点击「📱 WhatsApp」徽章，展开后有绿色「打开 WhatsApp 跟进（已预填复购话术）」按钮，直接调用 wa.me
3. **复盘摘要** — 成功案例数、已/待确认痛点、累计成交金额、地区/钩子分布、关键词、Top5案例
4. **发信漏斗** — 发送 → 送达 → 打开 → 回复 转化
5. **需求标签分布**（need_tag）— 调研先行的核心资产，横条图
6. **跟进阶段分布** — 5级冷却期（第1/2/3封 → 已停止 → 转WhatsApp）
7. **WhatsApp 触达清单** — 有WA号的客户，区分「📩待发WA / ✅已转WA」，可筛选、一键复制待发号码；号码本身是可点击的 wa.me 链接，最右侧「一键调用」列——待发客户显示「📩 发开发信」（预填首次开发话术 first），已转客户显示「💬 跟进」（预填复购话术 repeat）

> **WhatsApp 调用逻辑连贯统一**：卡片墙与触达清单共用脚本顶部同一个 `wa_link(num, contact, brand, stage)` 函数生成 wa.me 链接与预填话术。`stage="first"` 首次开发、`stage="repeat"` 老客户复购/跟进，全看板行为一致。
8. **发信趋势** — 按日期发送/退信柱状图
9. **地区分布** — 按地区横向柱状图
10. **通用邮箱 vs 决策人具名邮箱 送达率对比**

## 输入 JSON 格式

```json
{
  "pool": {
    "total_unique": 11148,
    "pipeline_reserve": 320,
    "blacklist": 45,
    "wa_contacts": 12
  },
  "records": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "title": "Buyer",
      "region": "Europe",
      "status": "sent",
      "email_type": "named",
      "sent_date": "2026-06-15",
      "batch": "Batch 1",
      "need_tag": "line_a",
      "hook_type": "compliance",
      "subject": "Email subject",
      "whatsapp": "+46 70 123 4567"
    }
  ],
  "followups": [
    {"stage": 1},
    {"stage": 2},
    {"stage": 5}
  ],
  "milestones": [
    {"date": "6/15", "event": "首批发信", "result": "90封送达 / 10退信", "color": "#3b82f6"}
  ],
  "success_cases": [
    {
      "email": "john@example.com",
      "brand": "Brand Name",
      "contact": "John Doe",
      "title": "Buyer",
      "region": "Europe",
      "order_amount": 15000,
      "success_points": "1.个性化钩子 2.决策人具名发信",
      "hook_type": "personalized_hook",
      "need_tag": "line_b",
      "language": "EN",
      "confirmed": true,
      "ai_analysis": "可能痛点：现供应商交付周期不稳定",
      "first_sent_date": "2026-06-15",
      "reply_date": "2026-06-18",
      "order_date": "2026-07-01",
      "whatsapp": "+39 300 000 0001"
    }
  ]
}
```

## 字段说明

### records（每封发信记录）
- `status` 状态值：`sent`已发送 / `bounced`退信 / `opened`已打开 / `replied`已回复 / `wa_only`已转WA渠道
- `email_type`：`named`决策人具名 / `generic`通用邮箱（不填则按邮箱前缀自动判断）
- `need_tag`：你在 `positioning.need_tags` 自定义的产品/服务线（如 `line_a` / `line_b`），保留值 `multi` / `unknown` / `review`；看板原样显示
- `hook_type`（= solution_tag）：11 个通用决策驱动之一，看板显示中文名——`compliance`合规优先 / `sustainability`可持续 / `quality_upgrade`品质升级 / `cost`成本 / `speed`时效 / `low_commitment`低门槛 / `innovation`新方向 / `exclusive_custom`定制独家 / `one_stop`一站式 / `dedicated_service`专属服务 / `strategic_scale`规模战略
- `whatsapp`：**填了 WA 号才会进入 WhatsApp 触达清单**。号码里的空格/括号会自动清理

### followups（跟进阶段分布）
- `stage`：`1`第1封跟进 / `2`第2封 / `3`第3封 / `4`已停止 / `5`转WhatsApp

### success_cases（成功案例，脚本用的是这套新字段）
- `confirmed`：`true`=用户已确认痛点，`false`=AI初步分析待确认
- `ai_analysis`：AI初步痛点分析（confirmed=false 时展示）
- `success_points`：用户确认后的成功要点
- `order_amount`：成交金额（数字）
- `first_sent_date` / `reply_date` / `order_date`：时间线
- `whatsapp`：成交客户的 WA 号也会进入触达清单（默认标记为「已沟通」）

## WhatsApp 触达闭环（邮件 → WA）

看板会自动汇总所有带 `whatsapp` 号的客户，并分为两组：

- **待发 WA（pending）**：有 WA 号，但邮件 status 不是 `wa_only`、也没标记 `wa_status:"sent"` —— 即还没用 WhatsApp 触达过。**这批就是可以直接发 WhatsApp 开发信的目标。**
- **已转 WA（done）**：status=`wa_only` 或已标记发过 WA 的客户。

导出的 `wa_targets.json` 结构：
```json
{
  "pending": [ {"whatsapp": "...", "brand": "...", "contact": "...", "region": "...", "need_tag": "...", "email": "..."} ],
  "done": [ ... ],
  "all": [ ... ]
}
```

**后续调用**：把 `wa_targets.json` 的 `pending` 列表喂给 WhatsApp 开发信流程，按 `need_tag` 匹配对应话术钩子，逐个发送。发送后用 `csv_ops.py mark_wa_only <email> <wa> <brand> <name>` 回写状态，下次生成看板时该客户会自动归入「已转WA」，避免重复触达。

## 每日汇报流程
1. 收集当日发送数据 + 客户池/黑名单计数 → 生成 JSON
2. 运行 `email_dashboard.py` → 生成 HTML 看板 + `wa_targets.json`
3. 提炼 3-5 个关键要点发给用户：
   - 今日开发/发送数量、客户池剩余覆盖率
   - 退信率/回复率
   - 备用池剩余储备
   - 待发 WA 客户数（可安排 WhatsApp 触达）
   - 成功案例进展、异常或需关注事项
