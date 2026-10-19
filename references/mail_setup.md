# 发信通道接入（企业邮箱密钥 / 多邮箱托管预热 / MCP）

> 装好技能后按本页走一遍，就能知道用哪条路径、去哪生成密钥、怎么验证、怎么交给脚本用。
> 所有服务器地址、端口、密钥叫法都标了出处；本技能自定的数值（预热档位、退信暂停阈值）都标为「可调默认值」。

---

## 一、先选路径

| 你的情况 | 选 | 一句话 |
|---|---|---|
| 国内企业邮箱（腾讯 / 阿里 / 网易）或 Gmail、单个发件邮箱 | **A1 单邮箱密钥** | 后台生成客户端密钥 → `export` 环境变量 → 脚本直接发 |
| 2 个以上发件邮箱，想分摊量、按预热爬坡 | **A2 多邮箱托管** | `mail_setup.py add` 登记 → 发信脚本自动挑剩余额度最多的邮箱 |
| 运行环境已接 Gmail / Outlook 连接器或邮件 MCP，不想给脚本密钥 | **B MCP / 连接器** | 脚本只出演练报告 → 人工逐条批准 → AI 用连接器建草稿/发送 → 回写记录 |

三条路径的共同点：先 `DRY_RUN=1` 出演练报告、逐条核对收件人和正文，再真发。

---

## 二、A1 单邮箱密钥

```bash
python3 scripts/mail_setup.py providers                       # 看服务器、端口、密钥叫法、在哪生成
python3 scripts/mail_setup.py env tencent_exmail --user sales@你的域名   # 打印要 export 的行
export SMTP_PASS=<后台生成的客户端密钥>                         # 只在终端里填，不写进任何文件
python3 scripts/mail_setup.py test                            # 只登录 SMTP/IMAP，不发任何邮件
```

### 服务商预设（出处见右列）

| 服务商 | SMTP | IMAP | 密钥叫法与生成位置 | 出处 |
|---|---|---|---|---|
| 腾讯企业邮箱 `tencent_exmail` | `smtp.exmail.qq.com` 465 SSL | `imap.exmail.qq.com` 993 SSL | 开启安全登录后须用「客户端专用密码」；网页版 设置 → 邮箱绑定 生成；需在 收发信设置 开启 IMAP/SMTP。海外节点 `hwsmtp/hwimap.exmail.qq.com` | [企业微信帮助中心](https://open.work.weixin.qq.com/help2/pc/19886)、[腾讯云文档](https://main.qcloudimg.com/raw/document/product/pdf/613_46019_cn.pdf) |
| 阿里企业邮箱 `aliyun_qiye` | `smtp.qiye.aliyun.com` 465 SSL | `imap.qiye.aliyun.com` 993 SSL | 「三方客户端安全密码」；设置 → 账户与安全 → 账户安全。香港节点 `smtphk/imaphk.qiye.aliyun.com` | [阿里云帮助 36576](https://help.aliyun.com/zh/document_detail/36576.html)、[阿里云帮助 36687](https://help.aliyun.com/zh/document_detail/36687.html) |
| 网易企业邮箱 `netease_qiye` | `smtphz.qiye.163.com` 465 SSL | `imaphz.qiye.163.com` 993 SSL | 第三方客户端须用「客户端授权码」；设置 → 账户与安全 → 客户端设置，只显示一次；管理员可能需先开放客户端协议 | [网易企业邮帮助 1](https://office.163.com/helpCenter/mail/d/2057123645218729986.html)、[网易企业邮帮助 2](https://office.163.com/helpCenter/mail/d/1892504337403437057.html) |
| Gmail / Workspace `gmail` | `smtp.gmail.com` 465 SSL（或 587 TLS） | `imap.gmail.com` 993 SSL | 「应用专用密码」需先开两步验证；改账户密码后会被吊销；Google 更推荐 OAuth（即路径 B） | [Gmail 帮助](https://support.google.com/mail/answer/185833?hl=en)、[Workspace 管理帮助](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app)、[Gmail 开发者文档](https://developers.google.com/workspace/gmail/imap/imap-smtp) |
| Microsoft 365 `microsoft365` | `smtp.office365.com` 587 STARTTLS（TLS 1.2+） | 不预设（收信/退信扫描建议走 OAuth 或连接器） | 邮箱需开启 Authenticated SMTP；SMTP AUTH 基本认证到 2026 年 12 月底前不变，之后现有租户默认关闭（管理员可再开），2026 年 12 月之后新建的租户须用 OAuth；最终移除日期将于 2027 下半年公布。建议直接走路径 B | [Microsoft Learn](https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365)、[Microsoft Exchange 团队博客](https://techcommunity.microsoft.com/blog/exchange/updated-exchange-online-smtp-auth-basic-authentication-deprecation-timeline/4489835) |
| 其他 `custom` | 服务商给的地址 | 同左 | 服务商给的 SMTP 密码 / 授权码 | 看服务商帮助文档 |

**常见失败**：用了网页登录密码而不是客户端密钥；没开 IMAP/SMTP 服务；管理员没开放客户端协议；公司网络拦了 465/587 端口。`test` 会把认证失败的原因提示出来。

---

## 三、A2 多邮箱托管 + 预热爬坡

```bash
python3 scripts/mail_setup.py add mb1 --provider aliyun_qiye --user a@你的域名
python3 scripts/mail_setup.py add mb2 --provider tencent_exmail --user b@你的域名 --daily-cap 60
export MAILBOX_PASS_MB1=<mb1 的客户端密钥>
export MAILBOX_PASS_MB2=<mb2 的客户端密钥>
python3 scripts/mail_setup.py list          # 每个邮箱：状态 / 预热第几天 / 今日上限 / 已用 / 剩余
python3 scripts/mail_setup.py test --mailbox mb1
```

- **托管文件** `config/mailboxes.json`：只存邮箱地址、服务商、密钥的**环境变量名**，不存密钥本身。打包分发时 `config/` 整体排除。
- **自动轮换**：没设 `SMTP_HOST` 时，`batch_sender.py` / `decision_maker_sender.py` 自动挑今天剩余额度最多的邮箱；`MAILBOX=mb2` 可指定。
- **预热爬坡**：每个邮箱有 `warmup_schedule`（从第 N 天起 → 每日上限）。内置默认 `第1天 20 → 第8天 40 → 第15天 80 → 第22天 150 → 第29天 200`。
  这是本技能的**保守可调默认值，不是任何服务商公布的数字**；服务商对你的账户有明确发信额度时以服务商为准。
  发信脚本取 `min(档案 rules.daily_limit, 预热上限 − 今日已用)`。
- **自动暂停**：一轮真发里退信（收件人被拒）占比超过 `bounce_pause_rate`（默认 0.05，可改）→ 该邮箱置为 `paused`，之后发信脚本拒绝使用它；排查名单后 `mail_setup.py resume mb1`。`triggers.py scan --apply-safe` 也会在近 7 天退信率异常时暂停全部托管邮箱。
- **用量记录** `data/mailbox_usage.csv`：日期、邮箱、发送数、退信数，看板和触发口都读它。
- **第三方预热服务**（选用）：市面上有专门的邮箱预热/托管服务，可与本技能并用；本技能不内置、不推荐具体厂商，接入前自行核实其条款与数据处理方式。

---

## 四、B MCP / 连接器发信

适合：不想把邮箱密钥交给脚本，或 Microsoft 365 / Google 只允许 OAuth。

```bash
DRY_RUN=1 python3 scripts/decision_maker_sender.py queue.json reports/     # 1 出演练报告（含最终正文）
python3 scripts/mail_setup.py mcp-export reports/decision_maker_report_<日期>.json   # 2 生成 outbox
# 3 人工逐条核对 reports/mcp_outbox.json，把要发的条目改成 "approved": true
# 4 AI 用运行环境里的 Gmail / Outlook 连接器（或邮件 MCP）对 approved 条目「建草稿」；
#   用户明确授权后才「发送」；每条处理完把 status 改为 drafted / sent
python3 scripts/mail_setup.py mcp-writeback reports/mcp_outbox.json        # 5 回写 sent_history（标 via:mcp）
```

规则：脚本本身不调用任何 MCP；AI 只处理 `approved=true` 的条目；默认建草稿，不默认发送。

---

## 五、发件域认证与退订（进箱率的硬条件）

```bash
python3 scripts/mail_setup.py auth-check 你的域名 --selector <DKIM selector>
```
查 SPF、DMARC、DKIM 三条 DNS TXT 记录（UDP 53 不通时自动改用 DNS-over-HTTPS）。

Gmail 发件人要求（[Google 发件人指南](https://support.google.com/mail/answer/81126?hl=en)、[Google 发件人指南 FAQ](https://support.google.com/mail/answer/14229414?hl=en)）：
- 所有发件人：至少配置 SPF 或 DKIM；发件 IP 有有效的反向解析（PTR）；Postmaster Tools 里的垃圾邮件率保持在 0.3% 以下。
- 每天给 Gmail 个人账户发约 5000 封以上的批量发件人：SPF + DKIM + DMARC 都要配（DMARC 可以是 `p=none`），From 域与 SPF/DKIM 对齐；营销类邮件要支持一键退订（`List-Unsubscribe` + `List-Unsubscribe-Post` 头）并在正文里放明显的退订链接；垃圾邮件率建议保持在 0.1% 以下。

本技能的落地：
- 发信脚本发**纯文本**邮件，每封自动带 `List-Unsubscribe: <mailto:发件邮箱?subject=unsubscribe>` 头；设了 `UNSUBSCRIBE_URL=https://...` 时再加 HTTPS 一键退订头和 `List-Unsubscribe-Post`。
- 正文末尾自动补一句退订提示（默认英文 “If this isn't relevant for you, just reply "no" and I won't write again.”；档案 `rules.opt_out_line` 可改成当地语言，设 `off` 可关闭但不建议）。演练报告里看到的就是最终正文。
- 收到 “no / unsubscribe / 退订” 的回复 → `csv_ops.py add_blacklist`，或在客户库把关系改成 `do_not_contact` 后重新 `data_import`，之后永不再发。
