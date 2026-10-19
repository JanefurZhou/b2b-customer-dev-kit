# 数据表模板（空表头）

这 5 个 CSV 只带表头、无任何真实数据，表头与 `scripts/csv_ops.py` 实际写入的字段**完全一致**
（`scripts/consistency_audit.py` 第 I 项会自动核对）：

| 文件 | 对应 csv_ops 字段常量 | 用途 |
|---|---|---|
| `sent_history.csv` | `SENT_FIELDS` | 发信台账（冷却期、跟进次数、状态） |
| `blacklist.csv` | `BL_FIELDS` | 黑名单/退信/拦截 |
| `wa_contacts.csv` | `WA_FIELDS` | WhatsApp 触达记录 |
| `success_cases.csv` | `SUCCESS_FIELDS` | 成功案例（用户确认后才写入） |
| `pipeline.csv` | `PIPELINE_FIELDS` | 备用客户池 |

## 运行时放在哪

脚本默认读写运行目录下的 `data/`，可用环境变量 `B2B_DATA_DIR` 指定：

```bash
export B2B_DATA_DIR=/path/to/your/data
python3 scripts/csv_ops.py stats
```

首次使用：把本目录的表头复制到你的 `B2B_DATA_DIR`（脚本在文件不存在时也会自动建表）。
这些模板保留在 `examples/` 内不参与运行写入；**真实客户数据永远只存在于你自己
的私有数据目录，不要提交回技能包**。字段定义见 `references/csv_guide.md`。
