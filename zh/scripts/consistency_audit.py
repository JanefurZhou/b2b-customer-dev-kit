#!/usr/bin/env python3
"""术语一致性自动审计（只读，不改任何文件，无需公司档案）

用法:
    python3 scripts/consistency_audit.py            # 打印报告，有 FAIL 时退出码 1
    python3 scripts/consistency_audit.py --json     # 机器可读输出

逐项对比「文档里写的」与「脚本里真实定义的」：
  A  CLI 子命令与参数        文档中的 `xxx.py <子命令> --参数` 是否真实存在
  B  档案字段路径            文档/脚本引用的 business.* / offer.* … 是否在空白档案里
  C  决策驱动标签            solution_tag 11 个取值在脚本、看板、钩子表、模板、文档中是否齐全一致
  D  旧标签残留              旧版 eco_only / traditional / low_moq … 只允许出现在"旧版映射"说明里
  E  发现渠道                CHANNEL_RECIPES 与文档渠道表、行业包推荐渠道、--ch 用法是否一致
  F  行业包                  包 id、字段与文档表、apply-pack 读取字段是否一致
  G  文件引用                文档里提到的 references/ scripts/ examples/ 文件是否存在
  H  环境变量                文档里的环境变量是否真被脚本读取
  I  数据表表头              examples/data_templates 与 csv_ops 实际写入字段、csv_guide 是否一致
  J  数量与版本声明          "13 个行业包 / 15 个渠道 / 11 个标签"、SKILL 版本与 CHANGELOG 是否一致
  K  冷却期规则              csv_guide §3.9 表格 / FAQ / SOP 伪代码 与 csv_ops 的 COOLDOWN_RULES 等常量是否一致
  L  状态取值                csv_guide 写的 status 取值是否真被 csv_ops 写入（不落库的派生状态不得列为存储值）
  N  流程图与文档/脚本        references/assets/sop_flowchart.json（与 PNG/PDF 同时生成）的步骤名、命令、
                            关键数字是否与 SKILL.md / SOP.md / sop_flowchart.md / 脚本常量一致
  M  社媒平台与职位词库      social_platforms.py 的 10 个平台 / 30 个职位 与 social_media_playbooks.md、SKILL.md 是否一致
  O  数据接入层与四维轮换    客户库声明必填、四维名称（高度/广度/深度/远度）与深度档、触发口冷却规则、
                            邮箱服务商地址出处、发信脚本是否接入托管与退订
纯标准库。
"""
import ast
import glob
import json
import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

RESULTS = []  # (section, level, message)


def add(sec, level, msg):
    RESULTS.append((sec, level, msg))


def read(p):
    with open(p, encoding="utf-8-sig") as f:
        return f.read()


def docs():
    out = [os.path.join(ROOT, "SKILL.md"), os.path.join(ROOT, "CHANGELOG.md")]
    out += sorted(glob.glob(os.path.join(ROOT, "references", "**", "*.md"), recursive=True))
    out += sorted(glob.glob(os.path.join(ROOT, "examples", "**", "*.md"), recursive=True))
    return [p for p in out if os.path.exists(p)]


def rel(p):
    return os.path.relpath(p, ROOT)


def is_changelog(p):
    return p.endswith("CHANGELOG.md")


# ---------------------------------------------------------------- spec loaders
def spec_cli():
    """{script_basename: {subcommand: set(flags)}}；None 子命令 = 无子命令脚本的位置参数用法。"""
    spec = {}
    import search_customers as sc
    import wa_review as wr
    for name, mod, fn in (("search_customers.py", sc, "_build_parser"), ("wa_review.py", wr, "build_parser")):
        parser = getattr(mod, fn)()
        subs = {}
        for act in parser._actions:
            if act.__class__.__name__ == "_SubParsersAction":
                for sub_name, sp in act.choices.items():
                    flags = set()
                    for a in sp._actions:
                        flags.update(o for o in a.option_strings if o.startswith("--"))
                    subs[sub_name] = flags
        spec[name] = subs
    src = read(os.path.join(SCRIPTS, "csv_ops.py"))
    disp = src[src.index("dispatch = {"):]
    subs = {}
    for m in re.finditer(r"'([a-z_]+)': lambda", disp):
        start = m.end()
        nxt = re.search(r"\n        '[a-z_]+': lambda", disp[start:])
        body = disp[start:start + (nxt.start() if nxt else len(disp))]
        subs[m.group(1)] = set(re.findall(r"a=='(--[a-z_]+)'", body))
    spec["csv_ops.py"] = subs
    src = read(os.path.join(SCRIPTS, "onboarding.py"))
    spec["onboarding.py"] = {c: set() for c in re.findall(r'cmd (?:==|in \() ?"([a-z-]+)"', src)}
    spec["onboarding.py"].update({"apply-pack": set(), "pack": set(), "packs": set()})
    src = read(os.path.join(SCRIPTS, "wa_bulk", "wa_bulk_sender.py"))
    blk = src[src.index("commands = {"):]
    blk = blk[:blk.index("}")]
    spec["wa_bulk_sender.py"] = {c: set() for c in re.findall(r"'([a-z_]+)':", blk)}
    # v3.1 数据接入层脚本：argparse 写在 main() 里，用源码解析 add_parser / add_argument
    for name in ("data_import.py", "mail_setup.py", "crm_sync.py", "triggers.py"):
        src = read(os.path.join(SCRIPTS, name))
        var2sub, subs = {}, {}
        for m in re.finditer(r'(\w+)\s*=\s*sub\.add_parser\(\s*"([a-z][a-z_-]+)"', src):
            var2sub[m.group(1)] = m.group(2)
            subs[m.group(2)] = set()
        for m in re.finditer(r'sub\.add_parser\(\s*"([a-z][a-z_-]+)"\)\.set_defaults', src):
            subs.setdefault(m.group(1), set())
        for m in re.finditer(r'(\w+)\.add_argument\(\s*"(--[a-z][a-z_-]+)"', src):
            if m.group(1) in var2sub:
                subs[var2sub[m.group(1)]].add(m.group(2))
        spec[name] = subs
    return spec


def blank_profile_paths():
    import onboarding
    paths = set()

    def walk(d, pre):
        for k, v in d.items():
            p = f"{pre}.{k}" if pre else k
            paths.add(p)
            if isinstance(v, dict) and v and pre:
                walk(v, p)
            elif isinstance(v, dict) and not pre:
                walk(v, p)
    walk(onboarding.blank_profile(), "")
    return paths


# ---------------------------------------------------------------- A. CLI
def check_cli():
    spec = spec_cli()
    pat = re.compile(r"(?:scripts/(?:wa_bulk/)?)?\b([a-z_]+\.py)\s+([a-z][a-z_-]+)((?:[ \t]+[^\n`|]*)?)")
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            hits = [(m.group(1), m.group(2), m.group(3) or "") for m in pat.finditer(line)]
            # 表格写法：| 用途 | csv_ops.py | `子命令 参数…` |
            tm = re.search(r"\|\s*([a-z_]+\.py)\s*\|\s*`([a-z][a-z_-]+)([^`]*)`", line)
            if tm and tm.group(2) not in ("python", "python3", "py"):
                hits.append((tm.group(1), tm.group(2), tm.group(3)))
            for script, sub, rest in hits:
                if script not in spec:
                    continue
                subs = spec[script]
                if sub not in subs:
                    add("A", "FAIL", f"{rel(p)}:{ln} `{script} {sub}` —— 该子命令不存在（可用：{', '.join(sorted(subs))}）")
                    bad += 1
                    continue
                for flag in re.findall(r"(?<![\w-])(--[a-z][a-z_-]+)", rest):
                    if flag in ("--help",):
                        continue
                    if flag not in subs[sub]:
                        add("A", "FAIL", f"{rel(p)}:{ln} `{script} {sub} {flag}` —— 该参数不存在"
                                         f"（{sub} 支持：{', '.join(sorted(subs[sub])) or '无参数'}）")
                        bad += 1
    if not bad:
        add("A", "PASS", "文档中出现的子命令与参数全部存在")


# ---------------------------------------------------------------- B. profile paths
SECTIONS = ("business", "company", "contact", "product", "offer", "positioning", "targeting", "search", "rules", "data_sources")


def check_profile_paths():
    paths = blank_profile_paths()
    pat = re.compile(r"`((?:%s)\.[a-z_]+(?:\.[a-z_]+)?)(?:\[[^\]]*\])?`" % "|".join(SECTIONS))
    bad = set()
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for m in pat.finditer(line):
                path = m.group(1)
                if path not in paths:
                    bad.add((rel(p), ln, path))
    code_pat = re.compile(r"""get\(\s*(?:profile|prof|data|self\.profile|p)\s*(?:or \{\})?\s*,\s*["']((?:%s)\.[a-z_.]+)["']""" % "|".join(SECTIONS))
    for f in glob.glob(os.path.join(SCRIPTS, "**", "*.py"), recursive=True):
        for ln, line in enumerate(read(f).splitlines(), 1):
            for m in code_pat.finditer(line):
                if m.group(1) not in paths:
                    bad.add((rel(f), ln, m.group(1)))
    for f, ln, path in sorted(bad):
        add("B", "FAIL", f"{f}:{ln} 引用档案字段 `{path}`，但空白档案（onboarding.blank_profile）里没有")
    if not bad:
        add("B", "PASS", f"文档与脚本引用的档案字段全部存在（空白档案共 {len(paths)} 个路径）")


# ---------------------------------------------------------------- C/D. tags
def check_tags():
    import config
    drivers = [t for t in config.DRIVER_TAGS if t not in ("open", "unknown")]
    targets = {
        "references/industry_playbooks.md": "§一 决策驱动表",
        "references/解决方案能力.md": "§二 诊断映射表",
        "references/email_templates.md": "§一 模板",
        "references/行业适配指南.md": "§四 双标签",
        "references/research_guide.md": "solution_tag 表",
        "references/dashboard_guide.md": "字段说明",
        "references/sop_flowchart.md": "双标签分流",
        "references/SOP.md": "template_map",
    }
    for f, label in targets.items():
        txt = read(os.path.join(ROOT, f))
        miss = [t for t in drivers if not re.search(r"(?<![a-z_])%s(?![a-z_])" % t, txt)]
        if miss:
            add("C", "FAIL", f"{f}（{label}）缺少 solution_tag：{', '.join(miss)}")
        else:
            add("C", "PASS", f"{f}（{label}）11 个 solution_tag 齐全")
    src = read(os.path.join(SCRIPTS, "decision_maker_sender.py"))
    tbl = src[src.index("table = {"):src.index("return table.get")]
    miss = [t for t in config.DRIVER_TAGS if f'"{t}"' not in tbl]
    add("C", "FAIL" if miss else "PASS",
        f"decision_maker_sender.build_hook 钩子表{'缺少：' + ', '.join(miss) if miss else '覆盖全部 13 个取值'}")
    src = read(os.path.join(SCRIPTS, "email_dashboard.py"))
    lab = src[src.index("need_tag_labels_map = {"):]
    lab = lab[:lab.index("}")]
    miss = [t for t in drivers if f'"{t}"' not in lab]
    add("C", "FAIL" if miss else "PASS",
        f"email_dashboard 中文标签表{'缺少：' + ', '.join(miss) if miss else '覆盖全部 11 个决策驱动'}")
    for legacy, new in config.LEGACY_TAG_ALIASES.items():
        if new not in config.DRIVER_TAGS:
            add("C", "FAIL", f"config.LEGACY_TAG_ALIASES: {legacy}→{new}，目标值不在 DRIVER_TAGS")
    # D. 旧标签残留
    allow = re.compile(r"旧|legacy|LEGACY|映射|兼容|alias", re.I)
    legacy_re = re.compile(r"(?<![a-z_])(%s)(?![a-z_])" % "|".join(sorted(config.LEGACY_TAG_ALIASES, key=len, reverse=True)))
    hits = []
    files = docs() + glob.glob(os.path.join(SCRIPTS, "**", "*.py"), recursive=True) \
        + glob.glob(os.path.join(ROOT, "examples", "**", "*.json"), recursive=True)
    for p in files:
        if is_changelog(p) or p.endswith("consistency_audit.py"):
            continue
        lines = read(p).splitlines()
        in_alias = False
        for ln, line in enumerate(lines, 1):
            if "LEGACY_TAG_ALIASES = {" in line:
                in_alias = True
            if in_alias:
                if line.strip().startswith("}"):
                    in_alias = False
                continue
            for m in legacy_re.finditer(line):
                tok = m.group(1)
                if tok == "regulated" and not re.search(r"[`'\"]regulated[`'\"]", line):
                    continue          # 英文单词 regulated 正常使用
                ctx = " ".join(lines[max(0, ln - 3):ln + 1])
                if allow.search(ctx) or "LEGACY_TAG_ALIASES" in ctx:
                    continue
                hits.append(f"{rel(p)}:{ln} 旧标签 `{tok}`")
    for h in hits:
        add("D", "FAIL", h + "（应改为新取值，或在同段注明是旧版映射）")
    if not hits:
        add("D", "PASS", "旧版标签只出现在映射/兼容说明中")


# ---------------------------------------------------------------- E. channels
def check_channels():
    import search_customers as sc
    keys = set(sc.CHANNEL_RECIPES)
    txt = read(os.path.join(ROOT, "references", "search_guide.md"))
    sec = txt[txt.index("## 渠道配方"):]
    doc_keys = set(re.findall(r"\|\s*([a-z]+) [^\s|]", sec))
    doc_keys &= keys | {k for k in doc_keys}
    miss = keys - doc_keys
    extra = {k for k in doc_keys if k not in keys and k.isascii() and len(k) > 2}
    add("E", "FAIL" if miss else "PASS",
        f"search_guide 渠道表{'缺少：' + ', '.join(sorted(miss)) if miss else '覆盖全部 %d 个渠道' % len(keys)}")
    for k in sorted(extra):
        add("E", "FAIL", f"search_guide 渠道表出现脚本里没有的渠道 `{k}`")
    packs = json.load(open(os.path.join(ROOT, "references", "industry_packs.json"), encoding="utf-8"))["packs"]
    for pk in packs:
        bad = [c for c in pk.get("recommended_channels", []) if c not in keys]
        if bad:
            add("E", "FAIL", f"行业包 {pk['id']} 推荐了不存在的渠道：{', '.join(bad)}")
    guide = read(os.path.join(ROOT, "references", "行业适配指南.md"))
    for pk in packs:
        row = re.search(r"^\|[ \t]*`%s`[ \t]*\|[^\n]*" % re.escape(pk["id"]), guide, re.M)
        if not row:
            continue
        cells = [c.strip() for c in row.group(0).strip("|").split("|")]
        doc_ch = [c.strip() for c in cells[-1].split("·")] if cells else []
        if doc_ch != pk.get("recommended_channels", []):
            add("E", "FAIL", f"行业适配指南 §二 `{pk['id']}` 推荐渠道与 industry_packs.json 不一致："
                             f"文档={doc_ch} / 数据={pk.get('recommended_channels')}")
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for m in re.finditer(r"--ch ((?:[a-z]+ ?)+)", line):
                for c in m.group(1).split():
                    if c not in keys:
                        add("E", "FAIL", f"{rel(p)}:{ln} `--ch {c}` 不是有效渠道")
                        bad += 1
    if not bad:
        add("E", "PASS", "文档中 --ch 用到的渠道全部有效")
    add("E", "PASS" if all(pk.get("recommended_channels") for pk in packs) else "FAIL", "每个行业包都有推荐渠道")


# ---------------------------------------------------------------- F. packs
def check_packs():
    import onboarding
    doc = json.load(open(os.path.join(ROOT, "references", "industry_packs.json"), encoding="utf-8"))
    packs = doc["packs"]
    ids = [p["id"] for p in packs]
    if len(ids) != len(set(ids)):
        add("F", "FAIL", "industry_packs.json 有重复 id")
    need = {k for _, k in onboarding._PACK_TARGETS} | {"id", "name", "offer_type", "suits"}
    for p in packs:
        miss = [k for k in need if k not in p]
        if miss:
            add("F", "FAIL", f"行业包 {p['id']} 缺字段：{', '.join(sorted(miss))}（apply-pack 会读取）")
        if p.get("offer_type") not in doc["offer_types"]:
            add("F", "FAIL", f"行业包 {p['id']} offer_type={p.get('offer_type')} 不在 offer_types 中")
    import config
    if set(doc["offer_types"]) != set(config.OFFER_TYPES):
        add("F", "FAIL", f"offer_types 不一致：packs={sorted(doc['offer_types'])} / config={sorted(config.OFFER_TYPES)}")
    guide = read(os.path.join(ROOT, "references", "行业适配指南.md"))
    sec = guide[guide.index("## 二、"):guide.index("## 三、")]
    doc_ids = re.findall(r"^\|[ \t]*`([a-z0-9_]+)`[ \t]*\|", sec, re.M)
    if set(doc_ids) != set(ids):
        add("F", "FAIL", f"行业适配指南 §二 包列表与数据不一致：缺 {sorted(set(ids) - set(doc_ids))} 多 {sorted(set(doc_ids) - set(ids))}")
    for p in packs:
        row = re.search(r"^\|[ \t]*`%s`[ \t]*\|[^|\n]*\|[ \t]*([a-z_]+)[ \t]*\|" % re.escape(p["id"]), sec, re.M)
        if row and row.group(1) != p["offer_type"]:
            add("F", "FAIL", f"行业适配指南 §二 `{p['id']}` 交付形态写 {row.group(1)}，数据是 {p['offer_type']}")
    all_txt = "\n".join(read(x) for x in docs() if not is_changelog(x))
    for m in set(re.findall(r"apply-pack ([a-z0-9_]+)", all_txt)) | set(re.findall(r"onboarding\.py pack ([a-z0-9_]+)", all_txt)):
        if m not in ids and m not in ("id",):
            add("F", "FAIL", f"文档示例使用了不存在的行业包 `{m}`")
    for f in glob.glob(os.path.join(ROOT, "examples", "profiles", "*.json")):
        d = json.load(open(f, encoding="utf-8-sig"))
        pid = d.get("business", {}).get("industry_pack")
        if pid and pid not in ids:
            add("F", "FAIL", f"{rel(f)} 引用不存在的行业包 {pid}")
        extra = set()

        def walk(x, pre):
            for k, v in x.items():
                pth = f"{pre}.{k}" if pre else k
                if pre and pth not in blank_profile_paths():
                    extra.add(pth)
                if isinstance(v, dict) and (not pre or pth in blank_profile_paths()):
                    walk(v, pth)
        walk({k: v for k, v in d.items() if isinstance(v, dict)}, "")
        for e in sorted(extra):
            if not e.startswith("positioning.conflict_groups") and not e.startswith("positioning.hooks"):
                add("F", "FAIL", f"{rel(f)} 含空白档案里没有的字段 `{e}`")
    if not [r for r in RESULTS if r[0] == "F" and r[1] == "FAIL"]:
        add("F", "PASS", f"{len(ids)} 个行业包的 id、字段、offer_type、文档表与演示档案全部一致")


# ---------------------------------------------------------------- G. file refs
def check_file_refs():
    pat = re.compile(r"(?<![\w/.-])((?:references|scripts|examples)/[\w./\u4e00-\u9fff-]+\.(?:md|py|json|csv|ps1|png|pdf))")
    bare = re.compile(r"`([\w\u4e00-\u9fff-]+\.(?:md|py|json|ps1))`")
    existing = {rel(p) for p in glob.glob(os.path.join(ROOT, "**", "*"), recursive=True)}
    names = {os.path.basename(p) for p in existing}
    runtime = {"company_profile.json", "IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md", "USER.md",
               "MEMORY.md", "HEARTBEAT.md", "candidates.json", "drafts.json", "preview.json", "list.json",
               "new.json", "data.json", "contacts.json", "ch.json", "q.json"}
    for f in glob.glob(os.path.join(SCRIPTS, "**", "*.py"), recursive=True) + \
            glob.glob(os.path.join(SCRIPTS, "**", "*.ps1"), recursive=True):
        runtime |= set(re.findall(r"[\w-]+\.(?:json|csv|txt|html)", read(f)))
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for m in pat.finditer(line):
                path = m.group(1).rstrip(".")
                if path not in existing and not path.startswith("scripts/wa_bulk/") or \
                        (path.startswith("scripts/wa_bulk/") and path not in existing):
                    add("G", "FAIL", f"{rel(p)}:{ln} 引用的文件不存在：{path}")
                    bad += 1
            for m in bare.finditer(line):
                n = m.group(1)
                if n not in names and n not in runtime and not n.startswith(("my_", "your")):
                    add("G", "WARN", f"{rel(p)}:{ln} 提到 `{n}`，包内没有同名文件（若是运行时生成可忽略）")
    if not bad:
        add("G", "PASS", "文档中带路径的文件引用全部存在")


# ---------------------------------------------------------------- H. env vars
def check_env():
    used = set()
    for f in glob.glob(os.path.join(SCRIPTS, "**", "*.py"), recursive=True) + \
            glob.glob(os.path.join(SCRIPTS, "**", "*.ps1"), recursive=True):
        s = read(f)
        used |= set(re.findall(r"""(?:environ\.get|getenv|env)\(\s*["']([A-Z][A-Z0-9_]+)["']""", s))
        used |= set(re.findall(r"""environ\[\s*["']([A-Z][A-Z0-9_]+)["']""", s))
        used |= set(re.findall(r"\$env:([A-Z][A-Z0-9_]+)", s))
    known_os = {"USERPROFILE", "PATH", "HOME", "INBOX"}
    pat = re.compile(r"\b([A-Z][A-Z0-9]*_[A-Z0-9_]+)\b")
    status_words = set()
    for f in glob.glob(os.path.join(SCRIPTS, "*.py")):
        status_words |= set(re.findall(r"print\(f?[\"']([A-Z][A-Z_]+)\b", read(f)))
    bad = set()
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            envish = "环境变量" in line or "env var" in line.lower()
            for m in pat.finditer(line):
                v = m.group(1)
                if v in used or v in known_os or v in status_words or v.startswith("MAILBOX_PASS_"):
                    continue
                explicit = re.search(r"(?:^|[\s`(])(?:export |\$env:)%s\b|(?:^|[\s`])%s=\S" % (v, v), line)
                if explicit or envish:
                    bad.add((rel(p), ln, v))
    for f, ln, v in sorted(bad):
        add("H", "FAIL", f"{f}:{ln} 文档要求设置环境变量 {v}，但没有任何脚本读取它")
    if not bad:
        add("H", "PASS", f"文档里的环境变量都被脚本读取（脚本共读取 {len(used)} 个）")


# ---------------------------------------------------------------- I. CSV headers
def check_csv():
    src = read(os.path.join(SCRIPTS, "csv_ops.py"))
    tree = ast.parse(src)
    fields = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.endswith("_FIELDS"):
            fields[node.targets[0].id] = [e.value for e in node.value.elts]
    file_map = {"sent_history.csv": "SENT_FIELDS", "blacklist.csv": "BL_FIELDS",
                "wa_contacts.csv": "WA_FIELDS", "success_cases.csv": "SUCCESS_FIELDS",
                "pipeline.csv": "PIPELINE_FIELDS"}
    tpl_dir = os.path.join(ROOT, "examples", "data_templates")
    for fn, var in file_map.items():
        tp = os.path.join(tpl_dir, fn)
        if not os.path.exists(tp):
            add("I", "WARN", f"examples/data_templates 缺少 {fn} 表头模板（csv_ops 会写入它）")
            continue
        hdr = read(tp).splitlines()[0].strip().split(",")
        if hdr != fields[var]:
            add("I", "FAIL", f"examples/data_templates/{fn} 表头与 csv_ops.{var} 不一致："
                             f"模板={hdr} / 脚本={fields[var]}")
        else:
            add("I", "PASS", f"{fn} 表头与 csv_ops 一致")
    for tp in glob.glob(os.path.join(tpl_dir, "*.csv")):
        if os.path.basename(tp) not in file_map:
            add("I", "WARN", f"examples/data_templates/{os.path.basename(tp)} 没有任何脚本读写（可能多余）")
    guide = read(os.path.join(ROOT, "references", "csv_guide.md"))
    for fn, var in file_map.items():
        m = re.search(r"###[^\n]*%s[^\n]*\n(.*?)(?=\n### |\n## |\Z)" % re.escape(fn), guide, re.S)
        if not m:
            add("I", "WARN", f"csv_guide.md 没有 {fn} 的字段小节")
            continue
        doc_cols = re.findall(r"^\|\s*([a-z_]+)\s*\|", m.group(1), re.M)
        doc_cols = [c for c in doc_cols if c not in ("字段", "field")]
        miss = [c for c in fields[var] if c not in doc_cols]
        extra = [c for c in doc_cols if c not in fields[var]]
        if miss or extra:
            add("I", "FAIL", f"csv_guide.md {fn} 字段表与 csv_ops.{var} 不一致：缺 {miss} 多 {extra}")
        else:
            add("I", "PASS", f"csv_guide.md {fn} 字段表与脚本一致")


# ---------------------------------------------------------------- J. counts & versions
def check_counts():
    import config
    import search_customers as sc
    n_packs = len(config.load_packs())
    n_ch = len(sc.CHANNEL_RECIPES)
    n_drv = len([t for t in config.DRIVER_TAGS if t not in ("open", "unknown")])
    rules = [(r"(\d+)\s*个(?:内置)?行业包", n_packs, "行业包"),
             (r"(\d+)\s*个(?:新)?发现渠道|共\s*(\d+)\s*个[）)]", n_ch, "发现渠道"),
             (r"(\d+)\s*个(?:行业)?通用(?:的)?(?:决策驱动|取值)|(\d+)\s*个通用决策驱动", n_drv, "决策驱动")]
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for rx, real, label in rules:
                for m in re.finditer(rx, line):
                    val = next(g for g in m.groups() if g)
                    if int(val) != real and not ("新增" in line and label == "发现渠道"):
                        add("J", "FAIL", f"{rel(p)}:{ln} 写「{m.group(0)}」，实际 {label} 为 {real}")
                        bad += 1
    sk = read(os.path.join(ROOT, "SKILL.md"))
    v = re.search(r'version:\s*"([\d.]+)"', sk)
    cl = read(os.path.join(ROOT, "CHANGELOG.md"))
    top = re.search(r"^## v([\d.]+)", cl, re.M)
    if v and top and v.group(1) != top.group(1):
        add("J", "FAIL", f"SKILL.md version={v.group(1)}，CHANGELOG 最新={top.group(1)}")
        bad += 1
    if not bad:
        add("J", "PASS", f"数量声明一致（行业包 {n_packs} / 渠道 {n_ch} / 决策驱动 {n_drv}），版本 {v.group(1) if v else '?'} 与 CHANGELOG 一致")


# ---------------------------------------------------------------- K. cooldown rules
def _csv_ops_consts():
    t = ast.parse(read(os.path.join(SCRIPTS, "csv_ops.py")))
    out = {}
    for n in t.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except Exception:
                pass
    return out


def check_cooldown():
    c = _csv_ops_consts()
    rules, mg, mt = c["COOLDOWN_RULES"], c["MAX_GENERIC_FOLLOWUP"], c["MAX_TOTAL_FOLLOWUP"]
    bad = 0
    guide = read(os.path.join(ROOT, "references", "csv_guide.md"))
    sec = guide[guide.index("### 3.9"):]
    sec = sec[:sec.index("**返回字段**")]
    rows = dict(re.findall(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|", sec, re.M))
    if {int(k): int(v) for k, v in rows.items()} != rules:
        add("K", "FAIL", f"csv_guide §3.9 冷却表 {rows} ≠ COOLDOWN_RULES {rules}")
        bad += 1
    if not re.search(r"^\|\s*%d\s*\|\s*永久停通用邮箱" % mg, sec, re.M) or \
            not re.search(r"^\|\s*≥%d\s*\|\s*永久停发" % mt, sec, re.M):
        add("K", "FAIL", f"csv_guide §3.9 停发行与 MAX_GENERIC_FOLLOWUP={mg} / MAX_TOTAL_FOLLOWUP={mt} 不一致")
        bad += 1
    sop = read(os.path.join(ROOT, "references", "SOP.md"))
    blk = sop[sop.index("# 5级递进冷却期规则"):]
    blk = blk[:blk.index("# === 跟进内容必须差异化")]
    pairs = {int(a): int(b) for a, b in re.findall(
        r"followup_count == (\d+):[^\n]*\n\s*cooldown_days = (\d+)\b", blk)}
    if pairs != rules or re.search(r"cooldown_days = \d+-\d+", blk):
        add("K", "FAIL", f"SOP.md 冷却伪代码 {pairs} ≠ COOLDOWN_RULES {rules}")
        bad += 1
    for p in docs():
        if is_changelog(p):
            continue
        lines = read(p).splitlines()
        for ln, line in enumerate(lines, 1):
            ctx = " ".join(lines[max(0, ln - 3):ln])
            if ("冷却" in ctx or "COOLDOWN" in ctx or "cooldown" in ctx):
                for d in re.findall(r"默认\s*(\d+)\s*天", line):
                    if int(d) not in rules.values():
                        add("K", "FAIL", f"{rel(p)}:{ln} 写默认冷却 {d} 天，脚本是 {sorted(set(rules.values()))}")
                        bad += 1
            if "cooldown_rules" in line:
                add("K", "FAIL", f"{rel(p)}:{ln} 写 `cooldown_rules`，脚本常量名是 `COOLDOWN_RULES`")
                bad += 1
    if not bad:
        add("K", "PASS", f"冷却期文档与脚本一致（COOLDOWN_RULES={rules}，停通用={mg}，全停≥{mt}）")


# ---------------------------------------------------------------- L. status values
def check_status():
    src = read(os.path.join(SCRIPTS, "csv_ops.py"))
    written = set(re.findall(r"'status'\s*(?:\]\s*=|:)\s*'([a-z_]+)'", src))
    guide = read(os.path.join(ROOT, "references", "csv_guide.md"))
    m = re.search(r"^\| status \| enum \| 当前状态 \| ([^|（(]+)", guide, re.M)
    doc = {x.strip() for x in m.group(1).split("/")} if m else set()
    extra = doc - written
    if not m:
        add("L", "WARN", "csv_guide 未找到 sent_history status 行")
    elif extra:
        add("L", "FAIL", f"csv_guide sent_history.status 列出 {sorted(extra)}，但 csv_ops 从不写入（写入的是 {sorted(written)}）")
    else:
        add("L", "PASS", f"sent_history.status 文档取值 {sorted(doc)} 均由脚本写入")


# ---------------------------------------------------------------- M. social platforms
def check_social():
    sys.path.insert(0, SCRIPTS)
    import social_platforms as sp
    bad = 0
    names = [v["name"] for v in sp.PLATFORMS.values()]
    pb = read(os.path.join(ROOT, "references", "social_media_playbooks.md"))
    table = pb[pb.index("## 二、"):pb.index("## 三、")]
    doc_names = re.findall(r"^\|\s*([A-Za-z][A-Za-z0-9 ()]+?)\s*\|\s*⭐", table, re.M)
    if sorted(doc_names) != sorted(names):
        add("M", "FAIL", f"social_media_playbooks §二 平台 {doc_names} ≠ 脚本 {names}")
        bad += 1
    n_titles = sum(len(v) for v in sp.TITLE_TIERS.values())
    for p in (os.path.join(ROOT, "SKILL.md"), os.path.join(ROOT, "references", "social_media_playbooks.md")):
        for m in re.finditer(r"(\d+)\s*个(?:采购链)?职位", read(p)):
            if int(m.group(1)) != n_titles:
                add("M", "FAIL", f"{rel(p)} 写 {m.group(1)} 个职位，词库实际 {n_titles} 个")
                bad += 1
        for m in re.finditer(r"(\d+)\s*(?:大|个)(?:海外)?社媒", read(p)):
            if int(m.group(1)) != len(names):
                add("M", "FAIL", f"{rel(p)} 写 {m.group(1)} 个社媒平台，脚本实际 {len(names)} 个")
                bad += 1
    if not bad:
        add("M", "PASS", f"社媒平台 {len(names)} 个、职位词库 {n_titles} 个，脚本与文档一致")


# ---------------------------------------------------------------- N. flowchart
STEP_NAMES = {"零": "全渠道复盘", "一": "搜索候选", "二": "背景调查", "三": "需求定位", "四": "撰写内容",
              "五": "发送执行", "六": "跟进管理", "七": "WhatsApp 触发", "八": "成单复盘 + 七件套写回"}


def _default_of(src, flag):
    m = re.search(r'add_argument\(\s*"%s"[^)]*default=(\d+)' % re.escape(flag), src)
    return int(m.group(1)) if m else None


def check_flowchart():
    path = os.path.join(ROOT, "references", "assets", "sop_flowchart.json")
    if not os.path.exists(path):
        add("N", "FAIL", "缺 references/assets/sop_flowchart.json（流程图规格，随 PNG/PDF 一起生成）")
        return
    spec = json.load(open(path, encoding="utf-8-sig"))
    bad = 0
    # N1 版本
    m = re.search(r'version:\s*"([\d.]+)"', read(os.path.join(ROOT, "SKILL.md")))
    if not m or spec.get("version") != m.group(1):
        add("N", "FAIL", f"流程图版本 {spec.get('version')} ≠ SKILL.md 版本 {m and m.group(1)}")
        bad += 1
    # N2 步骤名：流程图 / SKILL / SOP / sop_flowchart 四处都要出现「第X步 + 规范名」
    fc_text = "\n".join(spec["clusters"] + [n["title"] for n in spec["nodes"].values()])
    srcs = {"流程图": fc_text,
            "SKILL.md": read(os.path.join(ROOT, "SKILL.md")),
            "references/SOP.md": read(os.path.join(ROOT, "references", "SOP.md")),
            "references/sop_flowchart.md": read(os.path.join(ROOT, "references", "sop_flowchart.md"))}
    for num, name in STEP_NAMES.items():
        pat = re.compile(r"第%s步[ ·：:*]*%s" % (num, re.escape(name)))
        head = re.compile(r"^###\s*第%s步：%s" % (num, re.escape(name)), re.M)   # SOP 章节标题必须用规范名
        for label, text in srcs.items():
            if not (head if label == "references/SOP.md" else pat).search(text):
                add("N", "FAIL", f"{label} 缺「第{num}步 {name}」（四处步骤名必须一致）")
                bad += 1
    # N3 命令：节点底部 ▶ 的子命令 / 参数 / 脚本 / 文档都必须真实存在
    cli = spec_cli()
    subs = set().union(*[set(v) for v in cli.values()])
    flags = set().union(*[f for v in cli.values() for f in v.values()])
    script_files = glob.glob(os.path.join(SCRIPTS, "*.py")) + glob.glob(os.path.join(SCRIPTS, "wa_bulk", "*.py"))
    for sp_ in script_files:   # 补上 spec_cli 未覆盖的脚本（如 send_window.py）的子命令
        subs |= set(re.findall(r"""add_parser\(\s*['"]([a-z][a-z_-]+)['"]""", read(sp_)))
        subs |= set(re.findall(r"""(?:cmd|command|args\[0\]|sys\.argv\[1\])\s*==\s*['"]([a-z][a-z_-]+)['"]""", read(sp_)))
    stems = {os.path.basename(f) for f in script_files}
    names = {os.path.basename(p) for p in docs()} | stems
    for nid, n in spec["nodes"].items():
        for tok in n.get("cmd", "").split():
            if tok in ("/", "·", "→", "|") or re.search(r"[^\x00-\x7f]", tok.split("/")[-1].rsplit(".", 1)[0] if tok.endswith(".md") else tok) and not tok.endswith(".md"):
                continue
            if re.match(r"^\d", tok):
                continue
            if tok.endswith((".py", ".md")):
                ok = os.path.basename(tok) in names
            elif tok.startswith("--"):
                ok = tok in flags
            else:
                ok = tok in subs or tok + ".py" in stems
            if not ok:
                add("N", "FAIL", f"流程图节点 {nid}「{n['title']}」的命令 `{tok}` 在脚本/文档里不存在")
                bad += 1
    # N4 关键数字：流程图写的数 = 脚本常量
    sys.path.insert(0, SCRIPTS)
    import search_customers as _sc, social_platforms as _sp
    sc_src = read(os.path.join(SCRIPTS, "search_customers.py"))
    bs_src = read(os.path.join(SCRIPTS, "batch_sender.py"))
    wa_src = read(os.path.join(SCRIPTS, "wa_bulk", "wa_bulk_sender.py"))
    _c = _csv_ops_consts()
    rules, mg, mt = _c["COOLDOWN_RULES"], _c["MAX_GENERIC_FOLLOWUP"], _c["MAX_TOTAL_FOLLOWUP"]
    allt = json.dumps(spec, ensure_ascii=False)
    expect = [
        (f"{len(_sc.CHANNEL_RECIPES)} 个发现渠道", "CHANNEL_RECIPES"),
        (f"{len(_sp.PLATFORMS)} 大社媒", "social_platforms.PLATFORMS"),
        (f"{sum(len(v) for v in _sp.TITLE_TIERS.values())} 个采购链职位", "social_platforms.TITLE_TIERS"),
        (f"可发<{_default_of(sc_src, '--floor')} 或 储备<{_default_of(sc_src, '--ahead-days')} 天", "replenish --floor / --ahead-days 默认值"),
        (f"库内重复>{round(_sc.FUNNEL_DUP_DB_RED * 100)}%", "FUNNEL_DUP_DB_RED"),
        (f"具名率<{round(_sc.FUNNEL_NAMED_EMAIL_RED * 100)}%", "FUNNEL_NAMED_EMAIL_RED"),
        (" / ".join(str(rules[k]) for k in sorted(rules)) + " 天", "COOLDOWN_RULES"),
        (f"={mg} 已发 {mg + 1} 封", "MAX_GENERIC_FOLLOWUP"),
        (f"≥{mt}（已发 {mt + 1} 封+）", "MAX_TOTAL_FOLLOWUP"),
    ]
    m = re.search(r'env\("DAILY_LIMIT", str\(profile_limit or (\d+)\)\)', bs_src)
    expect.append((f"≤{m.group(1) if m else '?'} 封/天", "batch_sender DAILY_LIMIT 默认值"))
    m = re.search(r'env\("SEND_INTERVAL", "(\d+)"\)', bs_src)
    expect.append((f"间隔 {m.group(1) if m else '?'}s", "batch_sender SEND_INTERVAL 默认值"))
    m = re.search(r"random\.uniform\((\d+), (\d+)\)\s*$", wa_src, re.M)
    expect.append((f"{m.group(1)}–{m.group(2)}s 间隔" if m else "?", "wa_bulk_sender 发送节奏"))
    m = re.search(r'min\((\d+), int\(os\.environ\.get\("WA_DAILY_LIMIT"', wa_src)
    expect.append((f"到 {m.group(1) if m else '?'} 条 STOP", "WA DAILY_LIMIT 上限"))
    for text, const in expect:
        if text not in allt:
            add("N", "FAIL", f"流程图缺「{text}」（来自 {const}）——图上的数字和脚本不一致")
            bad += 1
    # N5 证据门槛：流程图与 SKILL / research_guide 同一句话
    ev = "≥1 条 S1 或 2 条独立 S2"
    if ev not in allt:
        add("N", "FAIL", f"流程图缺证据门槛「{ev}」")
        bad += 1
    if not bad:
        add("N", "PASS", f"流程图 {len(spec['nodes'])} 个节点 / {len(spec['decisions'])} 个判断：9 个步骤名在 4 处一致，"
                         f"命令全部存在，{len(expect)} 个关键数字与脚本常量一致")


def check_data_layer():
    """O 数据接入层 + 四维轮换：脚本常量与文档 / 流程图 / 档案门禁一致。"""
    bad = 0
    import config as _cfg
    import search_customers as _sc
    import mail_setup as _ms
    import triggers as _tr
    # O1 安装必填：自有客户库声明
    if "data_sources.customer_db" not in _cfg.REQUIRED:
        add("O", "FAIL", "config.REQUIRED 缺 data_sources.customer_db（安装时必须声明自有客户库）")
        bad += 1
    for st in _cfg.CUSTOMER_DB_STATES:
        for doc in ("SKILL.md", "references/数据接入与触发口.md"):
            if st not in read(os.path.join(ROOT, doc)):
                add("O", "FAIL", f"{doc} 没写客户库声明取值 `{st}`")
                bad += 1
    # O2 四维名称：引擎文档 / SKILL / 流程图 / 搜索指南都用 高度·广度·深度·远度
    dims = ("高度", "广度", "深度", "远度")
    spec = json.load(open(os.path.join(ROOT, "references", "assets", "sop_flowchart.json"), encoding="utf-8"))
    srcs = {"references/自循环引擎.md": read(os.path.join(ROOT, "references", "自循环引擎.md")),
            "SKILL.md": read(os.path.join(ROOT, "SKILL.md")),
            "流程图": json.dumps(spec, ensure_ascii=False),
            "scripts/search_customers.py": read(os.path.join(SCRIPTS, "search_customers.py"))}
    for label, text in srcs.items():
        for d in dims:
            if d not in text:
                add("O", "FAIL", f"{label} 缺维度名「{d}」")
                bad += 1
        for dep in _sc.DEPTHS:
            if label != "SKILL.md" and dep.split("_")[0] not in text:
                add("O", "FAIL", f"{label} 缺深度档 {dep}")
                bad += 1
    for p in docs() + glob.glob(os.path.join(SCRIPTS, "*.py")):
        if is_changelog(p) or p.endswith("consistency_audit.py"):
            continue
        if "高光深远" in read(p):
            add("O", "FAIL", f"{rel(p)} 仍有旧说法「高光深远」（v3.1 起统一为 高度/广度/深度/远度）")
            bad += 1
    # O3 触发口冷却规则 = csv_ops
    c = _csv_ops_consts()
    if _tr.COOLDOWN_RULES != c["COOLDOWN_RULES"] or _tr.MAX_GENERIC_FOLLOWUP != c["MAX_GENERIC_FOLLOWUP"]:
        add("O", "FAIL", f"triggers.py 冷却规则 {_tr.COOLDOWN_RULES}/{_tr.MAX_GENERIC_FOLLOWUP} ≠ csv_ops "
                         f"{c['COOLDOWN_RULES']}/{c['MAX_GENERIC_FOLLOWUP']}")
        bad += 1
    # O4 服务商预设：mail_setup.py 的服务器地址都写在 mail_setup.md 且带出处
    md = read(os.path.join(ROOT, "references", "mail_setup.md"))
    n_hosts = 0
    for pid, pv in _ms.PROVIDERS.items():
        if pid == "custom":
            continue
        for k in ("smtp_host", "imap_host"):
            if pv[k]:
                n_hosts += 1
                if pv[k] not in md:
                    add("O", "FAIL", f"mail_setup.py 预设 {pid}.{k}={pv[k]} 没写进 references/mail_setup.md")
                    bad += 1
        if f"`{pid}`" not in md:
            add("O", "FAIL", f"references/mail_setup.md 缺服务商 `{pid}` 的出处行")
            bad += 1
    # O5 发信脚本都接了邮箱托管与退订头
    for name in ("batch_sender.py", "decision_maker_sender.py"):
        src = read(os.path.join(SCRIPTS, name))
        for tok in ("resolve_sender_route", "with_opt_out", "compose(", "record_usage", "maybe_auto_pause"):
            if tok not in src:
                add("O", "FAIL", f"{name} 未接入 {tok}（多邮箱托管 / 退订 / 自动暂停）")
                bad += 1
    if not bad:
        add("O", "PASS", f"数据接入层一致：客户库声明必填（{'/'.join(_cfg.CUSTOMER_DB_STATES)}）；四维名称与 3 档深度在引擎/SKILL/流程图/脚本一致；"
                         f"触发口冷却规则 = csv_ops；{n_hosts} 个服务商地址都有出处；两个发信脚本都接了托管与退订")


def main():
    for fn in (check_cli, check_profile_paths, check_tags, check_channels, check_packs,
               check_file_refs, check_env, check_csv, check_counts, check_cooldown, check_status, check_social, check_flowchart, check_data_layer):
        try:
            fn()
        except Exception as e:  # 审计器自身出错也要显式报告
            add(fn.__name__, "FAIL", f"审计项执行出错：{type(e).__name__}: {e}")
    if "--json" in sys.argv:
        print(json.dumps([{"section": s, "level": l, "message": m} for s, l, m in RESULTS],
                         ensure_ascii=False, indent=2))
    else:
        names = {"A": "CLI 子命令与参数", "B": "档案字段路径", "C": "决策驱动标签", "D": "旧标签残留",
                 "E": "发现渠道", "F": "行业包", "G": "文件引用", "H": "环境变量", "I": "数据表表头",
                 "J": "数量与版本", "K": "冷却期规则", "L": "状态取值", "M": "社媒平台", "N": "流程图一致性",
                 "O": "数据接入层与四维轮换"}
        for sec in sorted({r[0] for r in RESULTS}):
            print(f"\n[{sec}] {names.get(sec, sec)}")
            for s, l, m in RESULTS:
                if s == sec:
                    print(f"  {l:<4} {m}")
        c = {k: sum(1 for r in RESULTS if r[1] == k) for k in ("PASS", "WARN", "FAIL")}
        print(f"\n合计：PASS {c['PASS']} · WARN {c['WARN']} · FAIL {c['FAIL']}")
    sys.exit(1 if any(r[1] == "FAIL" for r in RESULTS) else 0)


if __name__ == "__main__":
    main()
