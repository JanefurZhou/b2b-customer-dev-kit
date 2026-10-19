# Skill-Self-Check 审计结果（v3.1）

工具：[xenos2025/Skill-Self-Check](https://github.com/xenos2025/Skill-Self-Check) 的 run_full_audit 全量审计（静态审计，不运行被审技能）。

| 审计项 | v2.2（改前） | v3.1（最终） |
|---|---|---|
| hard-gates | fail（critical 1.7 description 无「Use when」触发写法；should_fix 2.5 否定词密度 12） | **pass**（0 项非提示级问题） |
| ship-safety | stop_ship（critical CMD.1 `../csv_ops.py` 路径不存在 ×2；critical EXT.1 退信扫描无演练模式；should_fix EXT.1 DNS 校验无演练；should_fix EXT.3 PowerShell ×3） | **static_pass**（critical 0；仅剩 EXT.3 PowerShell ×3，已人工审查；v3.1 新增的 `crm_sync.py`、`mail_setup.py` 只有 info 级「有演练开关，需确认默认不外发」，已逐条核对，见 `ship_safety_review.md`） |
| role-contract | not_assessed（缺角色契约） | **pass**（`role-contract.json` single_context / single_role） |
| workflow-prompt | not_assessed | **not_applicable**（脚本不调用模型、无多步提示链，已在 SKILL.md 声明） |
| 评分 basic_usable | 4/5 | **5/5** |
| 评分 contract_clarity | 5/5 | **5/5** |
| 评分 support_kit | 4/4 | **4/4** |

包内自查：`python3 scripts/consistency_audit.py` → PASS 35 · WARN 0 · FAIL 0（A–O 15 个维度，含流程图一致性、数据接入层与四维轮换）。

复跑：
```bash
git clone https://github.com/xenos2025/Skill-Self-Check
cd Skill-Self-Check/skills/skill-self-check/scripts
# 运行该目录里的 run_full_audit 脚本，参数：<本技能目录> --out-dir <输出目录> --pretty
```
包内自查在本技能目录下运行：`python3 scripts/consistency_audit.py`。
