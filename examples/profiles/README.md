# 演示档案（虚构）

三份**虚构**的 `company_profile.json`，演示不同行业怎么填同一套字段：

| 文件 | 行业 | offer_type | 行业包 |
|---|---|---|---|
| `demo_industrial_parts.json` | 工业零部件出口 | physical_product | industrial_b2b |
| `demo_hr_saas.json` | HR SaaS | software | saas_software |
| `demo_seo_agency.json` | B2B 营销咨询 | service | professional_services |

- 名称、域名（`.example`）、人名全部是假的；`<...>` 是必须由真实用户替换的占位。
- 三份都是 `configured=false`、`user_confirmed=false`，**不能直接激活**，也不能当作任何用户的事实复制进真实档案。
- 用途：对照字段写法；或配合 `B2B_PROFILE=examples/profiles/demo_hr_saas.json` 在测试环境里看搜索式/邮件结构（真实使用必须走 SKILL.md 的建档与确认流程）。
