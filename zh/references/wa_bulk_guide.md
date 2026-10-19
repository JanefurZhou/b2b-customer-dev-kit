# WhatsApp 群发执行详细指南（邮件 → WA 闭环的最后一环）

> 本指南是 SKILL.md「九·五、WhatsApp 群发执行」的展开细节。
> 上游：看板 `email_dashboard.py` 导出的 `wa_targets.json`（pending 名单）。
> 执行引擎：`scripts/wa_bulk/wa_bulk_sender.py` + 3 个 PowerShell 脚本。
> 运行环境：**Windows 桌面 + WhatsApp Desktop（Store 版）+ 一台已登录的本地设备（设备名在首次建档/执行时由你指定，记作 <local-device>）**。

---

## 一、整条闭环怎么串起来

```
① 邮件开发（六步法）→ 客户没回 / 明确说加 WA
② csv_ops.py mark_wa_only <email> <wa> <brand> <name>  → 回写"转WA"状态
③ email_dashboard.py 生成看板 → 自动导出 wa_targets.json（pending / done / all）
④ wa_bulk_sender.py convert wa_targets.json → 群发输入（Format B 模板+变量，见下）
⑤ wa_bulk_sender.py validate → preview（只读预览）→ harness（发给自己测试号）
⑥ 确认无误 → 正式群发（每条：开聊天→popup检测→截图验证→发送→checkpoint）
⑦ 发完 audit 复查截图 → 回写 wa_status="sent" → 下次看板归入"已转WA"
```

**关键**：看板的 pending 名单和群发引擎是天然上下游。名单里的 `whatsapp` 号 + `brand` + `contact` 可直接映射成群发模板的 `phone` / `brand` / `intro` 变量。

---

## 二、双号体系（通用配置）

| 角色 | 号码 | 用途 |
|------|------|------|
| **小号（开发号）** | `<wa-outreach-number>`（E.164，使用前由你确认填入） | WA 桌面版登录、用来发消息。被封只损失开发号 |
| **大号（客户对接号）** | 建档 `contact.whatsapp`，即 `WhatsApp: +<country-code-number>` | 邮件/WA 签名里引导客户加的号，长期对接、不群发 |

**铁律**：群发只用小号；harness 测试号也用小号自己发给自己看。绝不用大号群发。开发号未经用户确认不得自行填写或编造。

---

## 三、Store版WA 特性（必读，否则脚本失效）

| 特性 | Store版 | 影响 |
|------|---------|------|
| 进程名 | `WhatsApp.Root.exe` | `Get-Process` 必须用 `WhatsApp.Root`，不能用 `WhatsApp` |
| 窗口标题 | **始终是"WhatsApp"不变** | 不能靠 title 判断当前聊天对象 |
| 号码注册判断 | popup 白屏检测 | 屏幕中心 3×3 采样 9 点，≥6 白 → 未注册 |
| 协议注册 | AppxManifest.xml 声明 | HKCU 残缺键会覆盖正确注册，需清理 |

## 四、whatsapp:// 协议修复

Store版可能存在 `HKCU:\SOFTWARE\Classes\whatsapp` 残缺注册表键（只有协议名、没有 `shell\open\command`），导致 `whatsapp://send?phone=xxx` 不生效。

```powershell
# 1. 备份
reg export "HKCU\SOFTWARE\Classes\whatsapp" "<your-local-folder>\whatsapp_reg_backup.reg" /y
# 2. 删除残缺键（让系统回退到 AppxManifest 正确注册）
Remove-Item -Path 'HKCU:\SOFTWARE\Classes\whatsapp' -Recurse -Force
# 3. 验证
Start-Process 'whatsapp://send?phone=<phone-E164>'
```

## 五、本地目录结构

```
<your-local-folder>\  （例如 %TEMP% 或你自建的 WA 工作目录，可用环境变量 WA_WORK_DIR / WA_SCREENSHOT_DIR / WA_MESSAGE_DIR / WA_LOG_DIR / WA_PROGRESS_FILE 指定）
├── 脚本\          ← PowerShell脚本(.ps1)
├── 截图\          ← WA截图验证(自动生成)
├── 消息\          ← 消息临时文件 + 联系人JSON
└── 日志\          ← 发送进度 wa_progress.json
```

截图先存 `$env:TEMP` → `Copy-Item` 到中文路径（GDI+ 对中文路径有限制）。

---

## 六、发送前检查清单（缺一不可）

- [ ] WhatsApp Desktop（Store版）已打开并登录（小号）
- [ ] 本地设备 <local-device> 在线
- [ ] `whatsapp://` 协议可用（不行先修复注册表）
- [ ] 联系人数据已就绪（CSV/Excel 先转 JSON，或直接 JSON）
- [ ] `validate` 显示 ✅ All passed（无格式错误、无重复号码）
- [ ] 模板已 `preview` 预览并确认（preview 只读，不会发送）
- [ ] 今日发送数 < 200（`progress` 查看）

任一项没打勾，不许开始。

---

## 七、Step 0 — 数据准备（CSV/Excel → JSON）

已是 JSON 可跳过。

```bash
python wa_bulk_sender.py convert customers.csv contacts_wa.json   # 零依赖
python wa_bulk_sender.py convert customers.xlsx                   # 需 openpyxl；没有就先另存为 CSV
python wa_bulk_sender.py convert wa_targets.json                  # 看板导出的 pending 名单
```

列名识别（大小写不敏感）：

| 识别的表头 | 字段 | 必需 |
|------------|------|------|
| phone / 电话 / 手机 / 号码 / whatsapp / wa / wa_number / mobile | `phone` | ✅ |
| brand / 品牌 / 公司 / company / name / 客户名 / customer | `brand` | 可选 |
| intro / 开场 / 开场白 | `intro` | 可选（Format B 的 {intro}） |
| message / 消息 / 内容 / 开发信 / msg | `message` | 可选 |

号码自动清洗（去掉 `+`、空格、连字符）。

**Format A – 扁平列表**：
```json
[
  {"brand": "Acme Corp", "phone": "12125551234", "message": "Hi Acme team!\n\n..."},
  {"brand": "Musterfirma GmbH", "phone": "4915100000001", "message": "Hallo Musterfirma GmbH!\n\n..."}
]
```

**Format B – 模板 + 变量（推荐，天然对接看板 pending 名单）**：
```json
{
  "template": "Hi {brand} team!\n\n{intro}\n\nWe're {company} — {product}. {fact}. More: {website}\n\nWorth a quick chat?",
  "company": "<your-brand>", "product": "<your one_liner_en>",
  "fact": "<one item from offer.key_facts>", "website": "<your-domain>",
  "contacts": [
    {"brand": "<example-customer>", "phone": "<phone-E164>", "intro": "Congrats on the new <project/office/launch>!"},
    {"brand": "<example-customer-2>", "phone": "<phone-E164>", "intro": "Read your post on <topic> — spot on."}
  ]
}
```
> `intro`（每人不同的开场白）就是防封的核心 —— 从看板的 `need_tag` / 背调记录里生成差异化开场，绝不千人一面。


## 七·二、WhatsApp 开发信模板库（7 钩子 WA 版）⭐

> WhatsApp 开发信不能照搬邮件。邮件可以长、可以正式；WhatsApp 要**短、口语、像真人聊天**，
> 每条都必须有**差异化开场 `{intro}`**（防封核心 + 提回复率）。下面 7 个模板对应邮件的 7 钩子，
> 但都压到 3～5 行、去正式抬头、加一句轻互动收尾。发送时填进 Format B 的 `template` 字段，
> `{intro}` 按每家 `need_tag`/`solution_tag`/背调结论单独生成，绝不千人一面。

**WhatsApp 开发信骨架（区别于邮件）：**

```
[差异化开场 {intro}] → [一句身份+能帮到什么] → [一个具体钩子] → [轻互动提问收尾]
```

- 先讲**对方**（提近况/接痛点/夸成果），不先讲自己 —— 差异化 + 防封。
- 全文不超过 5 行；结尾用低门槛问题（要不要发目录？方便聊两句吗？），不硬推销。
- 先背调定业务与现有方案水平（与你 `differentiators` 的关系）+ `need_tag`/`solution_tag`，再选钩子 —— 推错方向=白发。

### 7 个钩子的 WhatsApp 模板（`{intro}` 每人不同）

> 下表是**结构骨架**，全行业通用；正文里的事实（定位、起步方式、关键事实、认证、定制能力）必须替换为
> `config/company_profile.json` 中的真实值（`product.*` / `offer.*`），没有的能力就删掉那一行。

| 钩子 | solution_tag 场景 | WhatsApp 模板骨架（占位符必须替换为真实事实） |
|------|----------------|-------------------------------------------|
| ① 方案升级 | `quality_upgrade`：在用低一档方案 | `Hi {brand} team! {intro} We're <your-brand> — <your verifiable differentiator>. Want to compare side by side?` |
| ② 低门槛起步 | `low_commitment` / `cost`：小团队、首次尝试 | `Hi {brand}! {intro} Easy way to test us: <offer.entry_offer>. <offer.key_facts[0]>. Shall I set it up?` |
| ③ 时效/节点 | `speed`：有明确档期/上线日/工期 | `Hi {brand} team! {intro} <offer.delivery_time> for <your-core-term> — ready before <their deadline>. What's your timeline?` |
| ④ 定制/专属 | `exclusive_custom` / `dedicated_service` | `Hi {brand}! {intro} We build <your-core-term> to your spec — <custom capability fact>. Want to see how?` |
| ⑤ 合规/可持续 | `compliance` / `sustainability`（仅写真实资质） | `Hi {brand} team! {intro} <your-core-term> with <exact certification name>. Want the documentation?` |
| ⑥ 一站式 | `one_stop`：供应商/工具分散 | `Hi {brand}! {intro} We cover <scope A> and <scope B> from one team. Would that simplify things?` |
| ⑦ 新方向 | `innovation`：新产品线/新市场/融资 | `Hi {brand} team! {intro} For your <new initiative>: <your one_liner_en>. Worth a quick chat?` |

> **{intro} 生成**：从背调/`need_tag`/`solution_tag` 提一句只对这家成立的话。例：刚中标新项目 → intro=`Congrats on winning the <project>`；
> 在招相关岗位 → intro=`Saw you're hiring a <role> — sounds like <topic> is a priority`。**绝不复用同一句**。
>
> **信号不足**：业务/需求看不清时标 `need_review`，交你拍板，不自动下结论、不硬推。

### 与邮件开发信的差别（一句话记住）

- 邮件：可长、可正式、带附件与签名档；WhatsApp：**短、口语、先夸对方、一个钩子、一个轻问题**。
- 邮件靠标题抓人；WhatsApp 靠**第一行差异化开场**抓人 + 防封。
- 两者共用同一套 7 钩子 + `need_tag`/`material_tag` 映射，只是**载体不同、语气不同**。

---

## 七·三、WhatsApp 开发触发（明确方向：什么时候、对谁、怎么启动）⭐

> 你问“WhatsApp 开发什么时候触发”——不是凭感觉想起来才发，而是 **看板一出现下面 4 个信号之一，就自动进 WA 名单**。这样 WA 不再是“拍脑袋”，而是邮件链路的自然延伸。

### （一）四个触发信号（命中任一 → 进 WA 名单）

| 触发信号 | 判断依据（看板/数据） | 为什么转 WA |
|---------|------------------|------------|
| **① 邮件多轮未回** | `followup_count >= 2` 且 `status != replied`（已发 3 封以上无回） | 邮箱可能没人看/进垃圾箱，WA 直达本人，回复率高 |
| **② 邮箱退信/无效** | `status == bounced` 或只有通用邮箱无个人邮箱 | 邮件路已断，WA 是唯一剩下的直达渠道 |
| **③ 高价值目标 + 有公开 WA** | 高粉丝定位/大客户，官网或领英有 WhatsApp 号 | 大单值得用更重的直达方式去抓 |
| **④ 展会/主动留号** | 客户主动给了 WA（展会、询盘、往来） | 客户已表态愿意用 WA，优先级最高 |

> ①② 是**邮件链自动履带的**（看 `email_dashboard.py` 的 pending/未回名单）；③④ 是背调/人工发现，手动标进名单。

### （二）触发链（完整五步，与邮件闭环衔接）

```
① 看板列 pending/未回名单          ② 导出 WA 目标            ③ 套模板生成消息
   email_dashboard.py 筛选  ==→   → wa_targets.json      ==→   七·二 模板库 + {intro}逐家生成
   (①②③④ 信号命中者)              (Format B 结构)         (need_tag/material_tag 定钩子)
                                                              ↓
⑥ 复盘看效果              ⑤ 回写看板/名单            ④ 群发引擎逐个发+截图验证
   wa_review.py review   ←==   mark_wa_only / wa_status  ←==   wa_bulk_sender.py send
   (漏斗+钩子+成单渠道)         (避免重复触达)             (防封铁律、逐条截图)
        ↓
   复盘结果反哺 ① 下一轮名单（自循环）：哪个地区/钩子/需求 WA 成单多，下轮就向它加权
```

### （三）每步具体命令

```bash
# ① 从看板导出“邮件多轮未回 + 退信”的转 WA 名单（需看板支持；否则人工筛）
python3 scripts/email_dashboard.py --export-wa-targets wa_targets.json   # 若无此参数，按 status/followup_count 手工导

# ②③ 把 wa_targets 套 七·二 模板（逐家生成 {intro}）→ Format B contacts.json（人工/半自动填 template）

# ③ 校验 + 预览
python3 scripts/wa_bulk/wa_bulk_sender.py validate contacts.json
python3 scripts/wa_bulk/wa_bulk_sender.py preview contacts.json

# ④ 群发（逐条截图验证，防封铁律）
python3 scripts/wa_bulk/wa_bulk_sender.py send contacts.json

# ⑤ 回写看板/名单（避免重复触达）
python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>
# 客户回复了 → 把 wa_contacts.csv 该行 status 回写为 replied（复盘回复率靠它）

# ⑥ 复盘（只读不改，看 WA 漏斗 + 哪种钩子/地区成单）
python3 scripts/wa_review.py review --html wa_review.html --compare-email
python3 scripts/wa_review.py funnel
# 成交时务必给 add_success 带上 --won_channel wa，复盘口径才准
```

### （四）与邮件链的衔接点（一体化，不是两套）

- 邮件链负责“广播触达”，WA 链负责“邮件未回的难客收口”——**两链共用一个客户表**（见客户开发表 `stage` 列的“邮件未回→转 WA”状态）。
- 成单时用 `won_channel` 区分是邮件还是 WA 成的，`wa_review --compare-email` 就能告诉你**哪条渠道更值得加预算**。
- **元需求 2（你拍板）**：信号命中只是“建议进 WA 名单”，是否真发、发多少、先发谁，由你定；信号不足的标 `need_review`。

## 八、Step 1 — 校验与试运行

```bash
python wa_bulk_sender.py validate contacts.json
python wa_bulk_sender.py preview contacts.json      # 只读预览，不发送
```

**号码格式规则**（无 `+`、无空格、无连字符）：

| 国家 | 格式 | 示例 |
|------|------|------|
| US/加拿大 | `1` + 10位 | `12125551234` |
| 英国 | `44` + 10–11位 | `447911123456` |
| 法国 | `33` + 9位 | `33612345678` |
| 德国 | `49` + 10–11位 | `4915100000001` |
| 意大利 | `39` + 10位 | `393331234567` |
| 西班牙 | `34` + 9位 | `34612345678` |
| 澳大利亚 | `61` + 9位 | `61412345678` |
| 日本 | `81` + 9–10位 | `819012345678` |
| 中国 | `86` + 11位 | `86<11-digit-mobile>`（示例格式，非真实号码） |

---

## 九、Step 2 — 发送循环（每个联系人按序，不许跳步）

### 2-A 打开聊天
```powershell
Start-Process "whatsapp://send?phone={phone}"
```
等待 5 秒。

### 2-B popup 白屏检测 ⚠ 不许跳过
Store版 title 不变，靠 popup 判断号码是否注册：
```
屏幕中心 3×3 采样 9 个像素点
≥6 个白色(R>240,G>240,B>240) → popup → 号码未注册 → SKIP
<6 个白色 → 无 popup → 聊天已打开 → 继续
```

### 2-C 截图验证
```bash
python wa_bulk_sender.py screenshot   # → $env:TEMP\wa_verify.png
```
**匹配规则 — 去掉非数字，比对尾 8 位**：
```
✅ 匹配 → 进入 2-D
❌ 不匹配 → 重试 2-A+2-B+2-C（最多 2 次）→ 仍不匹配 → SKIP 记录原因
截图失败 → SKIP 记录原因
```

### 2-D 发送消息
**内联法（已验证，最简单，小批量推荐）**：
```powershell
Start-Process "whatsapp://send?phone={phone}"
Start-Sleep -Seconds 5
Add-Type -AssemblyName System.Windows.Forms
Set-Clipboard -Value "{message_text}"
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
```
**临时文件法（消息含特殊字符时）**：
```bash
python wa_bulk_sender.py send "{message_text}"   # 输出 SENT 或 ERROR:WhatsApp_NOT_FOCUSED
```
遇 `ERROR:WhatsApp_NOT_FOCUSED`：重试一次；再失败 → 跳过并记录。

### 2-E Checkpoint 与节奏
1. 更新 `wa_progress.json`
2. 累加 `wa_daily_count.json`（`send` 每生成一条自动 +1，`progress` 可看今日计数）
3. 日计数 = 上限（默认 200，可用环境变量 `WA_DAILY_LIMIT` 下调，不能调高）→ `send` 直接返回 `STOP` 并退出码 3，停止并报告
4. 联系人之间随机停 **8–15 秒**
5. 每 5 个联系人：随机停 **30–60 秒** 冷却
   （第 4、5 条由 `send` 自动执行：距上一条不够时间会先等够再生成下一条，记录在 `wa_pacing.json`）

---

## 十、防封铁律（不可协商）

- 每天最多 **200 条**（计数器强制）
- 每条最少间隔 **8 秒**（随机 8–15 秒）
- 每 5 条后 **30–60 秒** 冷却
- 每人 **不同开场白**（`{intro}` 变量）
- **禁 wa.me 链接**（群发场景 —— 见下方"wa.me 语境澄清"）
- **禁** 对多人发相同消息

### ⚠️ wa.me 语境澄清（与看板不矛盾）
- **群发场景禁 wa.me**：这里指不要在群发的消息正文里塞 `wa.me` 链接、也不要靠 `wa.me` 批量拉起聊天 —— 会被判营销、直接封号。群发一律用 `whatsapp://send?phone=` 协议逐个开聊天。
- **看板一键调用用 wa.me 合理**：看板「触达清单/成功案例卡片」里的 wa.me 链接是给**你本人手动点开单个客户聊天**用的运营工具（一次一个、你自己操作），不是群发、不进消息正文，因此安全。
- 一句话：**wa.me 不能用于"批量/自动/放进消息里"，可以用于"你手动点开一个聊天"**。

---

## 十一、常见偷懒与真相

| 偷懒说法 | 真相 |
|---|---|
| "2-B popup 检测慢，跳过" | Store版 title 永不变，popup 是唯一能判断号码未注册的方法 |
| "号码看着对，跳过截图" | 切换延迟时 WA 可能加载上一个聊天，截图是唯一证据 |
| "200/天太保守，调高" | WhatsApp 对群发封号，200 是安全上限 |
| "dry-run 没问题，跳过 validate" | validate 抓空消息、错号、位数不对和**重复号码**，dry-run 抓不到 |
| "跳过的客户以后再补" | 进度文件里的 skip 记录就是你的待办清单，立即导出 |
| "所有人发一样的" | 相同消息 = 强垃圾信号，永远变开场白 |
| "为了快，不截图直接内联" | 不验证，消息一定会发到错的窗口 |

## 十二、危险信号（出现任一，立即停）

- 跳过了 2-B（popup 检测）或 2-C（截图验证）
- 多个联系人收到相同消息文本
- 发送间隔 < 8 秒
- 日计数 > 200 却没按日期重置
- 发送后没更新 `wa_progress.json`
- 消息里有没替换的 `{变量}`
- 用了 `Get-Process -Name 'WhatsApp'`（应为 `WhatsApp.Root`）
- 试图靠窗口标题判断聊天对象（Store版 title 永不变）

---

## 十三、发后复查 audit

```bash
python wa_bulk_sender.py audit
# 生成 wa_audit.ps1 → 在 <local-device> 上执行 → 逐个打开已发聊天截图 → AI 读图核对号码+内容
```
| 参数 | 默认 | 说明 |
|------|------|------|
| `-ProgressFile` | `$env:TEMP\wa_progress.json`（或用 `WA_PROGRESS_FILE` 指定） | 进度文件路径 |
| `-MessageFile` | `""` | 消息 JSON（品牌交叉引用） |
| `-StartFrom` | `1` | 从第 N 条开始 |

## 十四、发前沙盒测试 harness

```bash
python wa_bulk_sender.py harness contacts.json   # 先自动校验文件，有问题直接拒绝
# 生成 wa_harness.ps1 -TestPhone <country-code><your-own-test-phone> -MessageFile contacts.json -Count 3
```
把前 3 条消息发给**你自己的测试号（小号）**，验证格式/内容/换行是否正确，再决定是否正式群发。

| 参数 | 必需 | 说明 |
|------|------|------|
| `-TestPhone` | ✅ | 你自己的 WhatsApp 号（用小号） |
| `-MessageFile` | ✅ | 消息 JSON 路径 |
| `-Count` | ❌ | 测试条数，默认 3 |

---

## 十五、发后回写看板 + 复盘（闭环收口）

**第一步：回写（避免重复触达）** —— 群发成功后，把已发客户回写为"已转WA"，下次看板自动归入「✅已转WA」：
```bash
python3 scripts/csv_ops.py mark_wa_only <email> <wa_number> <brand> <contact_name>
```
或在看板数据里给该 record 设 `wa_status="sent"`。**客户回复了 → 把 wa_contacts.csv 该行 status 回写为 `replied`**（复盘回复率靠它）。

**第二步：成交标渠道** —— WA 谈成单时，登记成功案例务必带上 `--won_channel wa`：
```bash
python3 scripts/csv_ops.py add_success <email> <brand> <contact> <order_amount> "<success_points>" --won_channel wa --region ... --need_tag ... --hook_type ...
```

**第三步：WA 专属复盘**（只读不改，14 铁律）—— 定期看 WA 这条渠道跑得怎么样，成为下一轮名单的依据（自循环）：
```bash
python3 scripts/wa_review.py review --html wa_review.html --compare-email   # WA 漏斗+钩子/地区/需求分布+邮件vs WA 对比
python3 scripts/wa_review.py funnel                                        # 只看触达→回复→成单漏斗
```
> 复盘结果**反哺触发**：哪个地区/钩子/`need_tag` 在 WA 上成单多，下一轮 七·三 的 WA 名单就向它加权——形成 **触发→发送→回写→复盘→再触发** 的闭环。复盘结论仅供参考，加码/收缩由你拍板（元需求 2）。

---

## 十六、脚本执行方式对照

| 方式 | 可靠性 | 备注 |
|------|--------|------|
| `-File xxx.ps1` | ✅ 最佳 | 脚本推荐 |
| `-EncodedCommand Base64` | ⚠️ 中文乱码 | 中文注释会损坏 |
| `-Command "内联"` | ❌ `$_` 被吃 | 禁用 |
| 直接内联（Set-Clipboard+SendKeys） | ✅ 已验证 | 小批量最简单 |

## 十七、关键约束

1. **只操作 WhatsApp** — 绝不碰其他程序
2. **每条消息都截图验证** — 不验证，不发送
3. PowerShell 脚本里**注释只用 ASCII**
4. 截图：`$env:TEMP` 暂存 → `Copy-Item` 到目标
5. 消息走临时文件，绝不拼接进 PowerShell 字符串
6. 命令执行需用户确认卡
7. 消息里避免 `'"` 等引号

## 十八、脚本清单（scripts/wa_bulk/）

| 文件 | 作用 |
|------|------|
| `wa_bulk_sender.py` | 主控：validate/preview/send/screenshot/progress/template/audit/harness（send/screenshot/harness/audit 需先完成建档；validate 会拦重复号码） |
| `wa_audit.ps1` | 发后逐个打开已发聊天截图，供 AI 核对 |
| `wa_harness.ps1` | 发前把前 N 条发给自己测试号 |
| `wa_phase1_batch3.ps1` | 批次样例：只开聊天+截图不发送（第一阶段验证号码注册状态）；运行前自检，遇到占位符/格式错/重复号码直接拒绝 |
