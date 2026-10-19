# Demo profiles (fictional)

Three **fictional** `company_profile.json` files showing how different industries fill the same set of fields:

| File | Industry | offer_type | Industry pack |
|---|---|---|---|
| `demo_industrial_parts.json` | Industrial parts export | physical_product | industrial_b2b |
| `demo_hr_saas.json` | HR SaaS | software | saas_software |
| `demo_seo_agency.json` | B2B marketing consultancy | service | professional_services |

- Names, domains (`.example`) and people are all made up; `<...>` marks placeholders a real user must replace.
- All three are `configured=false`, `user_confirmed=false`; they **cannot be activated directly** and must not be copied into a real profile as any user's facts.
- Purpose: compare how fields are written; or set `B2B_PROFILE=examples/profiles/demo_hr_saas.json` in a test environment to see the query / e-mail structure (real use must go through the profile and confirmation flow in SKILL.md).
