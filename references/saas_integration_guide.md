# Trade SaaS / data platform integration guide (export → import → sync)

> By default this skill finds customers only through public search and no-registration paths. Its coverage and speed cannot match paid data platforms:
> for example Kuajing Mofang claims to combine 7 lead sources including customs, LinkedIn and WhatsApp, with 4.3 billion customs records and 390 million LinkedIn contacts (vendor-reported, see [Kuajing Mofang news](https://www.upkuajing.com/knowledge/zixun/29556));
> NetEase Waimaotong claims to return key contacts and purchase records from a company name (vendor-stated, see [NetEase Waimaotong knowledge base](https://waimao.163.com/knowledge/article/1650)).
> If you already use such a platform, this page explains how to **graft** its data into this skill's loop instead of choosing one or the other.

---

## 1. Integration principles

1. **One entry point**: data from any platform ends up in `$B2B_DATA_DIR/customer_db.csv` (`data_import.py`). Search de-dup, replenish, triggers and CRM sync all read that one table.
2. **Three tiers, easiest first**:
   - **Tier 1 export file** (works for every platform): export CSV / Excel from the platform → drop into `data/inbox/` → `triggers.py scan` raises a notice → `data_import.py inspect` previews the mapping → human confirmation → `import`.
   - **Tier 2 official API**: when the platform publishes an API and you have access, pull data with the platform's own SDK / endpoints, save as CSV, then go through tier 1. This skill ships no third-party API client (authentication, quotas and terms differ too much).
   - **Tier 3 official MCP / Agent Skill**: when the platform offers an official MCP service or Skill, connect it in the runtime and let the AI call it following this skill's flow (look up people → write back to customer_db → research → DRY_RUN → human approval).
3. **No invented interfaces**: the table below lists only integration methods with a public source; anything unverified says "see the vendor's website" and defaults to tier 1.
4. **Compliance**: import only data the platform licenses to you; if the platform's terms forbid export or re-use, do not import. Always record the origin in `--source` (e.g. `saas:<platform>`, `customs:<platform>`) for traceability and per-source review.

---

## 2. Platform table (verified as of this version)

| Type | Platform | Verified integration method | How this skill connects | Source |
|---|---|---|---|---|
| Trade CRM | OKKI (Xiaoman) | OKKI CRM Open API (open.xiaoman.cn, OAuth2, covering customers / leads / opportunities / orders); OKKI Go also offers company search, contact unlock and sending endpoints and has published an official Agent Skill | Tier 1 export → `data_import`; tier 2 with API access; `crm_sync.py export --target okki` to write back | [APIs.io listing](https://apis.io/providers/xiaoman/), [OKKI official news](https://www.okki.com/news/321.html) |
| Lead generation / customs | Kuajing Mofang | Official trade lead-generation Skill for OpenClaw (find buyers, customs records, decision-maker contacts) | Tier 3: call the Skill in an environment that supports it and write results back to `customer_db`; or tier 1 export | [Kuajing Mofang course page](https://www.upkuajing.com/knowledge/shipin-system/intermediate/25748) |
| Lead generation / customs / e-mail marketing | NetEase Waimaotong | No official public API documentation found (third-party reseller pages exist but are not used as evidence) | Tier 1: export → `data_import`; API per the vendor's website / account manager | [NetEase Waimaotong website](https://waimao.163.com/) |
| Customs data | Tendata, Tradesns etc. | Open interfaces not verified in this version | Tier 1: export → `data_import --source customs:<platform>` | see the vendor's website |
| E-mail finder / verifier | Hunter | Official remote MCP: `https://mcp.hunter.io/mcp` (API key in the `X-API-Key` header; some clients support OAuth) | Tier 3: look up domain contacts, verify e-mails → write back; or export CSV via tier 1 | [Hunter MCP](https://hunter.io/mcp), [Hunter API docs](https://hunter.io/api-documentation/v2) |
| People / company search | Apollo | Official remote MCP: `https://mcp.apollo.io/mcp` (Streamable HTTP, OAuth 2.0; browserless clients use the master API key) | Tier 3: find decision makers by title / region → write back; or export CSV via tier 1 | [Apollo MCP docs](https://docs.apollo.io/docs/apollo-mcp) |
| General CRM | HubSpot | Official remote MCP: `https://mcp.hubspot.com` (OAuth 2.1 + PKCE; read/write contacts / companies / deals etc.); REST batch upsert | `crm_sync.py`: CSV / API / MCP, three paths | [HubSpot developer changelog](https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available), [HubSpot MCP docs](https://developers.hubspot.com/docs/build-with-ai/remote-mcp-server) |

> Platform features and interfaces change at any time; check each vendor's current documentation before connecting. The numbers and capability descriptions above are vendor statements, not this skill's own tests.

---

## 3. Procedure (tier 1, most common)

```bash
export B2B_DATA_DIR=data
mkdir -p data/inbox
# 1 export CSV / Excel from the platform and drop it into data/inbox/
python3 scripts/triggers.py scan                         # 2 a NEW_IMPORT_FILE notice appears
python3 scripts/data_import.py inspect data/inbox/export.xlsx   # 3 view column mapping and preview (read-only)
python3 scripts/data_import.py import data/inbox/export.xlsx \
        --relation prospect --source saas:<platform> [--map original_column=standard_field ...]   # 4 import after human confirmation
python3 scripts/data_import.py stats                     # 5 source split and cold-outreach capacity
```

After import, continue as usual: research (Step 2) → need positioning (Step 3) → writing (Step 4) → DRY_RUN → human approval → send (Step 5).
E-mails supplied by a platform still go through `dns_validator.py`; "verified" on the platform does not skip it.

---

## 4. Human checkpoints for tier 3

With a platform MCP the AI may do automatically: look up, enrich, write back to the customer DB, generate drafts.
The AI may not do automatically: bulk unlocks that consume paid credits (report the count and expected cost first and wait for the user's confirmation), send e-mails or messages, push to a CRM.
