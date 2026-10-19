# 发送路径人工审查记录（Skill-Self-Check · EXT.3）

> Skill-Self-Check 的 ship-safety 静态扫描对 PowerShell 自动化给出 should_fix「需要人工审查发送路径」。以下为逐文件审查结论（v3.0 审查，v3.1 未改动这三个文件）；改动这三个文件后需要重新审查。

| 文件 | 会不会发消息 | 发给谁 | 拦截与保护 |
|---|---|---|---|
| `scripts/wa_bulk/wa_harness.ps1` | 会（剪贴板粘贴 + 回车） | **只发给必填参数 `-TestPhone`**（你自己的测试号），不发给名单里的客户 | `-TestPhone` / `-MessageFile` 均为必填；消息文件不存在即退出；默认只发前 3 条（`-Count`）；每条截图留证 |
| `scripts/wa_bulk/wa_audit.ps1` | 不会（无发送按键） | — | 只打开聊天并截图，用于发后复查 |
| `scripts/wa_bulk/wa_phase1_batch3.ps1` | 不会（文件头注明 no send） | — | 只打开聊天 + 截图；运行前预检：残留 `<占位符>`、号码不是 8–15 位数字、重复号码 → 拒绝运行 |

正式群发只经 `wa_bulk_sender.py send`：门禁 READY + 内容指纹一致才运行；每条生成前检查当日计数（`WA_DAILY_LIMIT`，默认 200，到上限返回 STOP）；`validate` 不通过的文件 `harness` 拒绝使用。

## 其它外部动作的演练开关

| 脚本 | 外部动作 | 演练 |
|---|---|---|
| `batch_sender.py` / `decision_maker_sender.py` | SMTP 发信 | `DRY_RUN=1`：逐封输出主题、正文、当地窗口状态，不发送 |
| `imap_scanner.py` | 读邮箱（只读打开） | `DRY_RUN=1`：只列识别到的退信，不写黑名单 |
| `dns_validator.py` | DNS 查询（只读） | `DRY_RUN=1`：只列将要查询的域名，不发网络请求 |
| `search_customers.py` | 无（只生成搜索式文本） | — |
| `crm_sync.py push-hubspot` | 调 HubSpot 批量 upsert API | **默认演练**：不设 `CRM_PUSH=1` 只打印将推送的条目；真推还需 `HUBSPOT_TOKEN` 并过安装门禁（READY + 内容指纹一致）；禁联 / 同行永不推送 |
| `crm_sync.py export / pull / mcp-payload` | 无（只读写本地 CSV / JSON） | — |
| `mail_setup.py test` | 登录 SMTP / IMAP 验证密钥 | **只登录、不发信**；密码从环境变量读取，不落盘 |
| `mail_setup.py auth-check` | DNS 查询 SPF / DMARC（UDP，失败时走公共 DoH） | 只读查询 |
| `mail_setup.py mcp-export` | 无（只生成待发清单 JSON） | 清单里每条 `approved=false`，由你逐条改为 true 后才交给连接器 |
| `triggers.py scan --apply-safe` | 本地：暂停退信异常的托管邮箱 | 唯一的自动动作，且只会「停」不会「发」；恢复要人工 `mail_setup.py resume` |
| `data_import.py` | 无（只写本地客户库） | `inspect` / `--dry-run` 只读预览 |
