# 自动运转接入说明（Automation Setup）

本技能自带「客户池不枯竭」的判定与补池调度逻辑，但要在真实环境里**无人值守
每天自动跑**，需要由宿主（AI 平台日程 / cron / 常驻进程）定时唤起。本文说明
哪些已内置、边界在哪、以及三种挂载方式。

## 一、技能已内置的自动化逻辑（不用自己写）

`scripts/search_customers.py` 内含自循环引擎：

- **保底红线**：A 级可发候选池低于红线（`--floor`，默认 100）→ 判定池将触底，
  自动触发补池轮换并写预警。
- **补池轮换**：每次补池按四维（高度 / 广度 / 深度 / 远度）轮换搜索组合（客户分层 × 产品词 ×
  5 个正交轴 × 地区），避免每天重复挖同一批。
- **状态记忆**：轮换历史、上次运行时间落盘，断点后接着转，不重复。
- **相关命令**：
  - `replenish`：检查一次池子，低于线就产出今天该搜的词。
  - `status` / 轮换查看：看池位、可发天数、已转到哪个渠道层级。
  - `schedule`：常驻进程模式，每日定点自动执行「检查池→不足补池→轮换」。

发信时间：`batch_sender.py` / `decision_maker_sender.py` 对带 `region`/`tz` 的联系人按收件人当地
`rules.local_send_window` 判断（`scripts/send_window.py`，含夏令时、周末不发），窗口外本轮延后不发——
定时任务可以一天跑多次，每次只发正处在当地窗口内的人。

数据管线（`filter` / `dns_validator` / `email_guesser` / `batch_sender` /
`imap_scanner` / `email_dashboard`）负责去重、邮箱校验、发送、退信回写、看板，
可被定时任务串成闭环。

## 二、必须说清的能力边界

脚本是**确定性工具**，下列动作脚本本身不做，需要 AI agent（或浏览器/搜索工具）
在被唤起时完成：

1. **真正的联网搜索与读页面**：脚本产出布尔搜索词；执行搜索、打开官网/LinkedIn、
   抽取真实联系邮箱，由 AI 用搜索/浏览器工具完成。禁止用脚本编造邮箱。
2. **逐家背调与个性化文案**：每家是否对口、需求定位、邮件个性化，由 AI 依据
   research_guide 完成，而不是脚本套模板群发。
3. **发送前人工确认**：按 AGENTS.md 的刹车节点，外发邮件前必须经老板确认
   （可用平台日程产出"待审草稿"，老板批了再发）。

因此"全自动"的准确含义是：**定时自动检查池位、自动产出该搜的词、自动整理候选
与看板、自动提醒**；而"查邮箱—背调—定稿—发送"这一段保留 AI 执行 + 关键节点
人工确认，以保证质量与合规。

## 三、三种挂载方式（任选其一）

### 方式 A：AI 平台日程/工作流（推荐，免运维）

在 AI 平台建一个每日定时任务（如每个工作日早上），任务内容指向：

1. 先确认 `onboarding.py check` 为 READY（未完成建档则当天只提醒建档，不跑业务）。
2. 运行 `python3 scripts/triggers.py scan --apply-safe`，按 `reports/trigger_queue.json` 的优先级处理
   （池低 / 新导入文件 / 到期跟进 / 新回复 / 退信异常 / WhatsApp 线索 / CRM 待同步 / 周复盘；
   见 `references/数据接入与触发口.md`）。
3. 运行 `python3 scripts/search_customers.py replenish`（默认读 `$B2B_DATA_DIR/customer_db.csv`）。
4. 若输出"低于红线"：把产出的今日搜索词交给 AI 用搜索/浏览器工具执行，
   按流程找真实邮箱 → `filter` 入库 → `dns_validator` 校验。
5. 产出当日待发草稿清单（DRY_RUN），提交老板确认；确认后 `batch_sender` 发送
   （单邮箱密钥 / 多邮箱托管按预热限量 / MCP 连接器三条路，见 `references/mail_setup.md`）。
6. `imap_scanner` 回写退信与回复；`email_dashboard` 汇总，HEARTBEAT 报健康项；
   每周 `crm_sync.py export/pull` 与 CRM 对齐一次。

时区按 `rules.local_send_window` 与目标市场换算，确保在客户当地上班时段发。

### 方式 B：系统 cron（有常驻机器时）

```cron
# 每个工作日 08:20 扫数据触发口，08:30 检查池位并补池（路径/解释器按实际改）
20 8 * * 1-5  cd /path/to/skill && B2B_DATA_DIR=/path/to/data \
    /usr/bin/python3 scripts/triggers.py scan --apply-safe >> data/triggers.log 2>&1
30 8 * * 1-5  cd /path/to/skill && B2B_DATA_DIR=/path/to/data \
    /usr/bin/python3 scripts/search_customers.py replenish --emit queries_today.txt \
    >> data/replenish.log 2>&1
```

SMTP/IMAP 密钥通过环境变量提供，不要写进 cron 文件或档案。找到候选后的
背调与发送仍交给 AI/人工确认环节。

### 方式 C：内置常驻调度器（单机长开）

```bash
# 需要一台一直开机的环境；装有 apscheduler 用 cron 精度，否则用内置 sleep 循环
python3 scripts/search_customers.py schedule --at 09:00   # 默认读 $B2B_DATA_DIR/customer_db.csv
```

适合本地服务器/容器；注意进程重启、日志与密钥注入。

## 四、建议的每日闭环（挂定时器时照此编排）

1. 健康检查（HEARTBEAT）：池位、昨日发信数、退信率、是否有客户回复待跟。
2. 池位低于红线 → 自动补池轮换，覆盖多渠道（见 `channels` 子命令：
   通用网页 / 社媒 / Maps / 海关 / RFQ / 行业媒体 / 展会 / 竞品逆向 / 独立站）。
3. 候选过滤去重 → DNS 校验 → 逐家背调 → 个性化草稿。
4. 草稿送审 → 老板确认 → 当地上班时段发送 → 退信回写。
5. 有客户回复：按规则双渠道提醒老板跟进，不静默。
