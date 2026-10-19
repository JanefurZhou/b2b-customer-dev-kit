# 外贸 SaaS / 数据平台对接指引（导出 → 导入 → 同步）

> 本技能默认只用公开搜索和免注册路径找客户。覆盖面和速度比不上付费数据平台：
> 例如跨境魔方宣称整合海关、领英、WhatsApp 等 7 类线索来源，有 43 亿条海关贸易数据和 3.9 亿领英联系人（厂商自报，见[跨境魔方资讯](https://www.upkuajing.com/knowledge/zixun/29556)）；
> 网易外贸通宣称输入公司名可给出关键人联系方式与采购记录（厂商自述，见[网易外贸通知识库](https://waimao.163.com/knowledge/article/1650)）。
> 如果你已经在用这类平台，本页告诉你怎么把它的数据**嫁接**进本技能的闭环，而不是二选一。

---

## 一、对接原则

1. **统一入口**：任何平台的数据，最终都落到 `$B2B_DATA_DIR/customer_db.csv`（`data_import.py`）。搜索去重、补池、触发口、CRM 同步都只认这一张表。
2. **三档接法，从易到难**：
   - **档 1 导出文件**（所有平台都能用）：平台里导出 CSV / Excel → 放进 `data/inbox/` → `triggers.py scan` 提醒 → `data_import.py inspect` 预览映射 → 人工确认 → `import`。
   - **档 2 官方 API**：平台公开了 API 且你有权限时，用平台自己的 SDK/接口拉数据，落成 CSV 再走档 1。本技能不内置任何第三方平台的 API 客户端（各家鉴权、配额、条款差异大）。
   - **档 3 官方 MCP / Agent Skill**：平台提供官方 MCP 服务或 Skill 时，在运行环境里接入，由 AI 按本技能流程调用（查人 → 写回 customer_db → 背调 → DRY_RUN → 人工批准）。
3. **不编造接口**：下表只写已查到公开出处的接入方式；没查到的一律写「以官网为准」，默认走档 1。
4. **合规**：导入的是平台授权给你的数据；平台条款不允许导出或二次使用的，不要导入。来源一律记在 `--source`（例：`saas:平台名`、`customs:平台名`），方便追溯和按来源复盘。

---

## 二、平台对照（截至本版本查证）

| 类型 | 平台 | 已查到的接入方式 | 本技能接法 | 出处 |
|---|---|---|---|---|
| 外贸 CRM | OKKI（小满） | OKKI CRM Open API（open.xiaoman.cn，OAuth2，覆盖客户/线索/商机/订单等）；OKKI Go 另有公司搜索、联系人解锁、发信接口，并发布了官方 Agent Skill | 档 1 导出 → `data_import`；有 API 权限可走档 2；`crm_sync.py export --target okki` 回写 | [APIs.io 收录页](https://apis.io/providers/xiaoman/)、[OKKI 官方新闻](https://www.okki.com/news/321.html) |
| 外贸获客 / 海关 | 跨境魔方 | 官方提供 OpenClaw 用的外贸获客 Skill（找采购商、海关记录、决策人联系方式） | 档 3：在支持该 Skill 的环境里调用，结果写回 `customer_db`；或档 1 导出 | [跨境魔方课程页](https://www.upkuajing.com/knowledge/shipin-system/intermediate/25748) |
| 外贸获客 / 海关 / 邮件营销 | 网易外贸通 | 未查到官方公开 API 文档（网上有第三方代理商页面，不作为依据） | 档 1：导出 → `data_import`；API 以官网/客户经理答复为准 | [网易外贸通官网](https://waimao.163.com/) |
| 海关数据 | 腾道、特易等 | 未在本版本查证其开放接口 | 档 1：导出 → `data_import --source customs:平台名` | 以官网为准 |
| 找邮箱 / 验证 | Hunter | 官方远程 MCP：`https://mcp.hunter.io/mcp`（API Key 放 `X-API-Key` 头，部分客户端支持 OAuth） | 档 3：查域名联系人、验证邮箱 → 写回；或导出 CSV 走档 1 | [Hunter MCP](https://hunter.io/mcp)、[Hunter API 文档](https://hunter.io/api-documentation/v2) |
| 找人 / 找公司 | Apollo | 官方远程 MCP：`https://mcp.apollo.io/mcp`（Streamable HTTP，OAuth 2.0；无浏览器的客户端用 master API key） | 档 3：按职位/地区找决策人 → 写回；或导出 CSV 走档 1 | [Apollo MCP 文档](https://docs.apollo.io/docs/apollo-mcp) |
| 通用 CRM | HubSpot | 官方远程 MCP：`https://mcp.hubspot.com`（OAuth 2.1 + PKCE，可读写联系人/公司/商机等）；REST 批量 upsert | `crm_sync.py`：CSV / API / MCP 三条路 | [HubSpot 开发者更新](https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available)、[HubSpot MCP 文档](https://developers.hubspot.com/docs/build-with-ai/remote-mcp-server) |

> 平台功能和接口随时会变；接入前以各平台当前官网文档为准。上表的数字和能力描述都是厂商自述，不是本技能的实测。

---

## 三、操作步骤（档 1，最常用）

```bash
export B2B_DATA_DIR=data
mkdir -p data/inbox
# 1 从平台导出 CSV / Excel，放进 data/inbox/
python3 scripts/triggers.py scan                         # 2 出现 NEW_IMPORT_FILE 提醒
python3 scripts/data_import.py inspect data/inbox/导出.xlsx   # 3 看列映射与预览（只读）
python3 scripts/data_import.py import data/inbox/导出.xlsx \
        --relation prospect --source saas:平台名 [--map 原列名=标准字段 ...]   # 4 人工确认后导入
python3 scripts/data_import.py stats                     # 5 看来源分布、可冷开发量
```

导入后照常走：背调（第二步）→ 需求定位（第三步）→ 撰写（第四步）→ DRY_RUN → 人工批准 → 发送（第五步）。
平台给的邮箱同样要过 `dns_validator.py` 校验；平台说「已验证」也不跳过。

---

## 四、档 3 的人工关卡

用平台 MCP 时，AI 可以自动做：查询、补全、写回客户库、生成草稿。
AI 不能自动做：消耗付费额度的批量解锁（先报数量和预计消耗，等用户确认）、发出邮件或消息、推送到 CRM。
