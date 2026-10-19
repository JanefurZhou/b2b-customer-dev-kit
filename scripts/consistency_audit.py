#!/usr/bin/env python3
"""Terminology consistency audit (read-only, changes no files, needs no company profile)

Usage:
    python3 scripts/consistency_audit.py            # print report; exit code 1 when any FAIL
    python3 scripts/consistency_audit.py --json     # machine-readable output

Compares "what the docs say" with "what the scripts really define", item by item:
  A  CLI sub-commands & flags   does every `xxx.py <sub> --flag` in the docs exist
  B  profile field paths        are business.* / offer.* … references present in the blank profile
  C  decision-driver tags       are the 11 solution_tag values complete in scripts, dashboard, hook table, templates, docs
  D  legacy tag remnants        old eco_only / traditional / low_moq … allowed only inside "legacy mapping" notes
  E  discovery channels         CHANNEL_RECIPES vs the doc channel table, pack recommended channels, --ch usage
  F  industry packs             pack ids, fields vs the doc table and the fields apply-pack reads
  G  file references            do the references/ scripts/ examples/ files mentioned in docs exist
  H  environment variables      is every env var in the docs really read by a script
  I  CSV headers                examples/data_templates vs the fields csv_ops writes vs csv_guide
  J  counts & versions          "13 industry packs / 15 channels / 11 tags", SKILL version vs CHANGELOG
  K  cooldown rules             csv_guide §3.9 table / FAQ / SOP pseudocode vs csv_ops COOLDOWN_RULES etc.
  L  status values              are the status values in csv_guide really written by csv_ops (derived states must not be listed as stored)
  N  flowchart vs docs/scripts  step names, commands and key numbers in references/assets/sop_flowchart.json
                                (generated together with PNG/PDF) vs SKILL.md / SOP.md / sop_flowchart.md / script constants
  M  social platforms & titles  the 10 platforms / 30 titles of social_platforms.py vs social_media_playbooks.md, SKILL.md
  O  data access layer & axes   customer-DB declaration required, four axis names (Height/Breadth/Depth/Reach) and depth tiers,
                                trigger cooldown rules, mail-provider host sources, sender scripts wired to hosting and opt-out
Standard library only.
"""
import ast
import glob
import json
import os
import re
import sys
for _s in (sys.stdout, sys.stderr):  # no mojibake / errors on Windows redirects or GBK terminals
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
    """{script_basename: {subcommand: set(flags)}}."""
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
    # v3.1 data-access scripts: argparse lives in main(), so parse add_parser / add_argument from source
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
            # table form: | purpose | csv_ops.py | `sub flags…` |
            tm = re.search(r"\|\s*([a-z_]+\.py)\s*\|\s*`([a-z][a-z_-]+)([^`]*)`", line)
            if tm and tm.group(2) not in ("python", "python3", "py"):
                hits.append((tm.group(1), tm.group(2), tm.group(3)))
            for script, sub, rest in hits:
                if script not in spec:
                    continue
                subs = spec[script]
                if sub not in subs:
                    add("A", "FAIL", f"{rel(p)}:{ln} `{script} {sub}` — sub-command does not exist (available: {', '.join(sorted(subs))})")
                    bad += 1
                    continue
                for flag in re.findall(r"(?<![\w-])(--[a-z][a-z_-]+)", rest):
                    if flag in ("--help",):
                        continue
                    if flag not in subs[sub]:
                        add("A", "FAIL", f"{rel(p)}:{ln} `{script} {sub} {flag}` — flag does not exist"
                                         f" ({sub} supports: {', '.join(sorted(subs[sub])) or 'no flags'})")
                        bad += 1
    if not bad:
        add("A", "PASS", "every sub-command and flag mentioned in the docs exists")


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
        add("B", "FAIL", f"{f}:{ln} references profile field `{path}`, missing from the blank profile (onboarding.blank_profile)")
    if not bad:
        add("B", "PASS", f"every profile field referenced by docs and scripts exists (blank profile has {len(paths)} paths)")


# ---------------------------------------------------------------- C/D. tags
def check_tags():
    import config
    drivers = [t for t in config.DRIVER_TAGS if t not in ("open", "unknown")]
    targets = {
        "references/industry_playbooks.md": "§1 decision-driver table",
        "references/solution_capabilities.md": "§2 diagnosis map",
        "references/email_templates.md": "§1 templates",
        "references/industry_adaptation_guide.md": "§4 dual tags",
        "references/research_guide.md": "solution_tag table",
        "references/dashboard_guide.md": "field notes",
        "references/sop_flowchart.md": "dual-tag routing",
        "references/SOP.md": "template_map",
    }
    for f, label in targets.items():
        txt = read(os.path.join(ROOT, f))
        miss = [t for t in drivers if not re.search(r"(?<![a-z_])%s(?![a-z_])" % t, txt)]
        if miss:
            add("C", "FAIL", f"{f} ({label}) missing solution_tag: {', '.join(miss)}")
        else:
            add("C", "PASS", f"{f} ({label}) all 11 solution_tags present")
    src = read(os.path.join(SCRIPTS, "decision_maker_sender.py"))
    tbl = src[src.index("table = {"):src.index("return table.get")]
    miss = [t for t in config.DRIVER_TAGS if f'"{t}"' not in tbl]
    add("C", "FAIL" if miss else "PASS",
        f"decision_maker_sender.build_hook hook table {'missing: ' + ', '.join(miss) if miss else 'covers all 13 values'}")
    src = read(os.path.join(SCRIPTS, "email_dashboard.py"))
    lab = src[src.index("need_tag_labels_map = {"):]
    lab = lab[:lab.index("}")]
    miss = [t for t in drivers if f'"{t}"' not in lab]
    add("C", "FAIL" if miss else "PASS",
        f"email_dashboard label table {'missing: ' + ', '.join(miss) if miss else 'covers all 11 decision drivers'}")
    for legacy, new in config.LEGACY_TAG_ALIASES.items():
        if new not in config.DRIVER_TAGS:
            add("C", "FAIL", f"config.LEGACY_TAG_ALIASES: {legacy}→{new}, target not in DRIVER_TAGS")
    # D. legacy tag remnants
    allow = re.compile(r"旧|legacy|LEGACY|映射|兼容|alias|mapping|compat", re.I)
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
                    continue          # the plain English word 'regulated'
                ctx = " ".join(lines[max(0, ln - 3):ln + 1])
                if allow.search(ctx) or "LEGACY_TAG_ALIASES" in ctx:
                    continue
                hits.append(f"{rel(p)}:{ln} legacy tag `{tok}`")
    for h in hits:
        add("D", "FAIL", h + " (use the new value, or mark the passage as a legacy mapping)")
    if not hits:
        add("D", "PASS", "legacy tags appear only in mapping / compatibility notes")


# ---------------------------------------------------------------- E. channels
def check_channels():
    import search_customers as sc
    keys = set(sc.CHANNEL_RECIPES)
    txt = read(os.path.join(ROOT, "references", "search_guide.md"))
    sec = txt[txt.index("## Channel recipes"):]
    doc_keys = set(re.findall(r"\|\s*`([a-z]+)` [^\s|]", sec))
    doc_keys &= keys | {k for k in doc_keys}
    miss = keys - doc_keys
    extra = {k for k in doc_keys if k not in keys and k.isascii() and len(k) > 2}
    add("E", "FAIL" if miss else "PASS",
        f"search_guide channel table {'missing: ' + ', '.join(sorted(miss)) if miss else 'covers all %d channels' % len(keys)}")
    for k in sorted(extra):
        add("E", "FAIL", f"search_guide channel table lists channel `{k}` that the script does not have")
    packs = json.load(open(os.path.join(ROOT, "references", "industry_packs.json"), encoding="utf-8"))["packs"]
    for pk in packs:
        bad = [c for c in pk.get("recommended_channels", []) if c not in keys]
        if bad:
            add("E", "FAIL", f"industry pack {pk['id']} recommends non-existent channels: {', '.join(bad)}")
    guide = read(os.path.join(ROOT, "references", "industry_adaptation_guide.md"))
    for pk in packs:
        row = re.search(r"^\|[ \t]*`%s`[ \t]*\|[^\n]*" % re.escape(pk["id"]), guide, re.M)
        if not row:
            continue
        cells = [c.strip() for c in row.group(0).strip("|").split("|")]
        doc_ch = [c.strip() for c in cells[-1].split("·")] if cells else []
        if doc_ch != pk.get("recommended_channels", []):
            add("E", "FAIL", f"industry_adaptation_guide §2 `{pk['id']}` recommended channels differ from industry_packs.json: "
                             f"doc={doc_ch} / data={pk.get('recommended_channels')}")
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for m in re.finditer(r"--ch ((?:[a-z]+ ?)+)", line):
                for c in m.group(1).split():
                    if c not in keys:
                        add("E", "FAIL", f"{rel(p)}:{ln} `--ch {c}` is not a valid channel")
                        bad += 1
    if not bad:
        add("E", "PASS", "every channel used with --ch in the docs is valid")
    add("E", "PASS" if all(pk.get("recommended_channels") for pk in packs) else "FAIL", "every industry pack has recommended channels")


# ---------------------------------------------------------------- F. packs
def check_packs():
    import onboarding
    doc = json.load(open(os.path.join(ROOT, "references", "industry_packs.json"), encoding="utf-8"))
    packs = doc["packs"]
    ids = [p["id"] for p in packs]
    if len(ids) != len(set(ids)):
        add("F", "FAIL", "industry_packs.json has duplicate ids")
    need = {k for _, k in onboarding._PACK_TARGETS} | {"id", "name", "offer_type", "suits"}
    for p in packs:
        miss = [k for k in need if k not in p]
        if miss:
            add("F", "FAIL", f"industry pack {p['id']} missing fields: {', '.join(sorted(miss))} (read by apply-pack)")
        if p.get("offer_type") not in doc["offer_types"]:
            add("F", "FAIL", f"industry pack {p['id']} offer_type={p.get('offer_type')} not in offer_types")
    import config
    if set(doc["offer_types"]) != set(config.OFFER_TYPES):
        add("F", "FAIL", f"offer_types differ: packs={sorted(doc['offer_types'])} / config={sorted(config.OFFER_TYPES)}")
    guide = read(os.path.join(ROOT, "references", "industry_adaptation_guide.md"))
    sec = guide[guide.index("## 2."):guide.index("## 3.")]
    doc_ids = re.findall(r"^\|[ \t]*`([a-z0-9_]+)`[ \t]*\|", sec, re.M)
    if set(doc_ids) != set(ids):
        add("F", "FAIL", f"industry_adaptation_guide §2 pack list differs from data: missing {sorted(set(ids) - set(doc_ids))} extra {sorted(set(doc_ids) - set(ids))}")
    for p in packs:
        row = re.search(r"^\|[ \t]*`%s`[ \t]*\|[^|\n]*\|[ \t]*([a-z_]+)[ \t]*\|" % re.escape(p["id"]), sec, re.M)
        if row and row.group(1) != p["offer_type"]:
            add("F", "FAIL", f"industry_adaptation_guide §2 `{p['id']}` offer_type says {row.group(1)}, data is {p['offer_type']}")
    all_txt = "\n".join(read(x) for x in docs() if not is_changelog(x))
    for m in set(re.findall(r"apply-pack ([a-z0-9_]+)", all_txt)) | set(re.findall(r"onboarding\.py pack ([a-z0-9_]+)", all_txt)):
        if m not in ids and m not in ("id",):
            add("F", "FAIL", f"doc example uses non-existent industry pack `{m}`")
    for f in glob.glob(os.path.join(ROOT, "examples", "profiles", "*.json")):
        d = json.load(open(f, encoding="utf-8-sig"))
        pid = d.get("business", {}).get("industry_pack")
        if pid and pid not in ids:
            add("F", "FAIL", f"{rel(f)} references non-existent industry pack {pid}")
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
                add("F", "FAIL", f"{rel(f)} contains field `{e}` that the blank profile lacks")
    if not [r for r in RESULTS if r[0] == "F" and r[1] == "FAIL"]:
        add("F", "PASS", f"ids, fields, offer_type, doc table and demo profiles of all {len(ids)} industry packs are consistent")


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
                    add("G", "FAIL", f"{rel(p)}:{ln} referenced file does not exist: {path}")
                    bad += 1
            for m in bare.finditer(line):
                n = m.group(1)
                if n not in names and n not in runtime and not n.startswith(("my_", "your")):
                    add("G", "WARN", f"{rel(p)}:{ln} mentions `{n}`, no such file in the package (ignore if generated at runtime)")
    if not bad:
        add("G", "PASS", "every path-qualified file reference in the docs exists")


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
            envish = "环境变量" in line or "env var" in line.lower() or "environment variable" in line.lower()
            for m in pat.finditer(line):
                v = m.group(1)
                if v in used or v in known_os or v in status_words or v.startswith("MAILBOX_PASS_"):
                    continue
                explicit = re.search(r"(?:^|[\s`(])(?:export |\$env:)%s\b|(?:^|[\s`])%s=\S" % (v, v), line)
                if explicit or envish:
                    bad.add((rel(p), ln, v))
    for f, ln, v in sorted(bad):
        add("H", "FAIL", f"{f}:{ln} docs ask to set env var {v}, but no script reads it")
    if not bad:
        add("H", "PASS", f"every env var in the docs is read by a script (scripts read {len(used)} in total)")


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
            add("I", "WARN", f"examples/data_templates lacks header template {fn} (csv_ops writes it)")
            continue
        hdr = read(tp).splitlines()[0].strip().split(",")
        if hdr != fields[var]:
            add("I", "FAIL", f"examples/data_templates/{fn} header differs from csv_ops.{var}: "
                             f"template={hdr} / script={fields[var]}")
        else:
            add("I", "PASS", f"{fn} header matches csv_ops")
    for tp in glob.glob(os.path.join(tpl_dir, "*.csv")):
        if os.path.basename(tp) not in file_map:
            add("I", "WARN", f"examples/data_templates/{os.path.basename(tp)} is read or written by no script (possibly redundant)")
    guide = read(os.path.join(ROOT, "references", "csv_guide.md"))
    for fn, var in file_map.items():
        m = re.search(r"###[^\n]*%s[^\n]*\n(.*?)(?=\n### |\n## |\Z)" % re.escape(fn), guide, re.S)
        if not m:
            add("I", "WARN", f"csv_guide.md has no field section for {fn}")
            continue
        doc_cols = re.findall(r"^\|\s*([a-z_]+)\s*\|", m.group(1), re.M)
        doc_cols = [c for c in doc_cols if c not in ("字段", "field", "Field")]
        miss = [c for c in fields[var] if c not in doc_cols]
        extra = [c for c in doc_cols if c not in fields[var]]
        if miss or extra:
            add("I", "FAIL", f"csv_guide.md {fn} field table differs from csv_ops.{var}: missing {miss} extra {extra}")
        else:
            add("I", "PASS", f"csv_guide.md {fn} field table matches the script")


# ---------------------------------------------------------------- J. counts & versions
def check_counts():
    import config
    import search_customers as sc
    n_packs = len(config.load_packs())
    n_ch = len(sc.CHANNEL_RECIPES)
    n_drv = len([t for t in config.DRIVER_TAGS if t not in ("open", "unknown")])
    rules = [(r"(\d+)\s*(?:built-in )?industry packs", n_packs, "industry packs"),
             (r"(\d+)\s*(?:new )?discovery channels", n_ch, "discovery channels"),
             (r"(\d+)\s*(?:industry-)?generic decision drivers", n_drv, "decision drivers")]
    bad = 0
    for p in docs():
        if is_changelog(p):
            continue
        for ln, line in enumerate(read(p).splitlines(), 1):
            for rx, real, label in rules:
                for m in re.finditer(rx, line):
                    val = next(g for g in m.groups() if g)
                    if int(val) != real and not (("新增" in line or "added" in line.lower()) and label == "discovery channels"):
                        add("J", "FAIL", f"{rel(p)}:{ln} says '{m.group(0)}', actual {label}: {real}")
                        bad += 1
    sk = read(os.path.join(ROOT, "SKILL.md"))
    v = re.search(r'version:\s*"([\d.]+)"', sk)
    cl = read(os.path.join(ROOT, "CHANGELOG.md"))
    top = re.search(r"^## v([\d.]+)", cl, re.M)
    if v and top and v.group(1) != top.group(1):
        add("J", "FAIL", f"SKILL.md version={v.group(1)}, CHANGELOG latest={top.group(1)}")
        bad += 1
    if not bad:
        add("J", "PASS", f"counts consistent (packs {n_packs} / channels {n_ch} / decision drivers {n_drv}); version {v.group(1) if v else '?'} matches CHANGELOG")


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
    sec = sec[:sec.index("**Return fields**")]
    rows = dict(re.findall(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|", sec, re.M))
    if {int(k): int(v) for k, v in rows.items()} != rules:
        add("K", "FAIL", f"csv_guide §3.9 cooldown table {rows} ≠ COOLDOWN_RULES {rules}")
        bad += 1
    if not re.search(r"^\|\s*%d\s*\|\s*Stop generic mailboxes permanently" % mg, sec, re.M) or \
            not re.search(r"^\|\s*≥%d\s*\|\s*Stop sending permanently" % mt, sec, re.M):
        add("K", "FAIL", f"csv_guide §3.9 stop rows differ from MAX_GENERIC_FOLLOWUP={mg} / MAX_TOTAL_FOLLOWUP={mt}")
        bad += 1
    sop = read(os.path.join(ROOT, "references", "SOP.md"))
    blk = sop[sop.index("# 5-level progressive cooldown rules"):]
    blk = blk[:blk.index("# === Follow-up content must differ")]
    pairs = {int(a): int(b) for a, b in re.findall(
        r"followup_count == (\d+):[^\n]*\n\s*cooldown_days = (\d+)\b", blk)}
    if pairs != rules or re.search(r"cooldown_days = \d+-\d+", blk):
        add("K", "FAIL", f"SOP.md cooldown pseudocode {pairs} ≠ COOLDOWN_RULES {rules}")
        bad += 1
    for p in docs():
        if is_changelog(p):
            continue
        lines = read(p).splitlines()
        for ln, line in enumerate(lines, 1):
            ctx = " ".join(lines[max(0, ln - 3):ln])
            if ("冷却" in ctx or "COOLDOWN" in ctx or "cooldown" in ctx):
                for d in re.findall(r"默认\s*(\d+)\s*天|default\s*(\d+)\s*days", line):
                    d = d[0] or d[1]
                    if int(d) not in rules.values():
                        add("K", "FAIL", f"{rel(p)}:{ln} says default cooldown {d} days, script has {sorted(set(rules.values()))}")
                        bad += 1
            if "cooldown_rules" in line:
                add("K", "FAIL", f"{rel(p)}:{ln} says `cooldown_rules`, the script constant is `COOLDOWN_RULES`")
                bad += 1
    if not bad:
        add("K", "PASS", f"cooldown docs match the script (COOLDOWN_RULES={rules}, stop generic={mg}, stop all ≥{mt})")


# ---------------------------------------------------------------- L. status values
def check_status():
    src = read(os.path.join(SCRIPTS, "csv_ops.py"))
    written = set(re.findall(r"'status'\s*(?:\]\s*=|:)\s*'([a-z_]+)'", src))
    guide = read(os.path.join(ROOT, "references", "csv_guide.md"))
    m = re.search(r"^\| status \| enum \| Current status \| ([^|（(]+)", guide, re.M)
    doc = {x.strip() for x in m.group(1).split("/")} if m else set()
    extra = doc - written
    if not m:
        add("L", "WARN", "csv_guide: sent_history status row not found")
    elif extra:
        add("L", "FAIL", f"csv_guide sent_history.status lists {sorted(extra)}, never written by csv_ops (written: {sorted(written)})")
    else:
        add("L", "PASS", f"sent_history.status doc values {sorted(doc)} are all written by the script")


# ---------------------------------------------------------------- M. social platforms
def check_social():
    sys.path.insert(0, SCRIPTS)
    import social_platforms as sp
    bad = 0
    names = [v["name"] for v in sp.PLATFORMS.values()]
    pb = read(os.path.join(ROOT, "references", "social_media_playbooks.md"))
    table = pb[pb.index("## 2."):pb.index("## 3.")]
    doc_names = re.findall(r"^\|\s*([A-Za-z][A-Za-z0-9 ()]+?)\s*\|\s*⭐", table, re.M)
    if sorted(doc_names) != sorted(names):
        add("M", "FAIL", f"social_media_playbooks §2 platforms {doc_names} ≠ script {names}")
        bad += 1
    n_titles = sum(len(v) for v in sp.TITLE_TIERS.values())
    for p in (os.path.join(ROOT, "SKILL.md"), os.path.join(ROOT, "references", "social_media_playbooks.md")):
        for m in re.finditer(r"(\d+)\s*(?:procurement-chain )?titles\b", read(p)):
            if int(m.group(1)) != n_titles:
                add("M", "FAIL", f"{rel(p)} says {m.group(1)} titles, title bank has {n_titles}")
                bad += 1
        for m in re.finditer(r"(\d+)\s*(?:overseas )?social (?:media )?platforms", read(p)):
            if int(m.group(1)) != len(names):
                add("M", "FAIL", f"{rel(p)} says {m.group(1)} social platforms, script has {len(names)}")
                bad += 1
    if not bad:
        add("M", "PASS", f"{len(names)} social platforms and {n_titles} titles consistent between script and docs")


# ---------------------------------------------------------------- N. flowchart
STEP_NAMES = {"0": "Omni-channel Review", "1": "Search Candidates", "2": "Background Research", "3": "Need Positioning",
              "4": "Write Content", "5": "Send", "6": "Follow-up Management", "7": "WhatsApp Trigger",
              "8": "Win Review + Kit Write-back"}


def _default_of(src, flag):
    m = re.search(r'add_argument\(\s*"%s"[^)]*default=(\d+)' % re.escape(flag), src)
    return int(m.group(1)) if m else None


def check_flowchart():
    path = os.path.join(ROOT, "references", "assets", "sop_flowchart.json")
    if not os.path.exists(path):
        add("N", "FAIL", "missing references/assets/sop_flowchart.json (flowchart spec, generated with PNG/PDF)")
        return
    spec = json.load(open(path, encoding="utf-8-sig"))
    bad = 0
    # N1 version
    m = re.search(r'version:\s*"([\d.]+)"', read(os.path.join(ROOT, "SKILL.md")))
    if not m or spec.get("version") != m.group(1):
        add("N", "FAIL", f"flowchart version {spec.get('version')} ≠ SKILL.md version {m and m.group(1)}")
        bad += 1
    # N2 step names: flowchart / SKILL / SOP / sop_flowchart must all contain 'Step N + canonical name'
    fc_text = "\n".join(spec["clusters"] + [n["title"] for n in spec["nodes"].values()])
    srcs = {"flowchart": fc_text,
            "SKILL.md": read(os.path.join(ROOT, "SKILL.md")),
            "references/SOP.md": read(os.path.join(ROOT, "references", "SOP.md")),
            "references/sop_flowchart.md": read(os.path.join(ROOT, "references", "sop_flowchart.md"))}
    for num, name in STEP_NAMES.items():
        pat = re.compile(r"Step %s[ ·：:*]*%s" % (num, re.escape(name)))
        head = re.compile(r"^###\s*Step %s: %s" % (num, re.escape(name)), re.M)   # SOP section heading must use the canonical name
        for label, text in srcs.items():
            if not (head if label == "references/SOP.md" else pat).search(text):
                add("N", "FAIL", f"{label} lacks 'Step {num} {name}' (step names must match in all four places)")
                bad += 1
    # N3 commands: every sub-command / flag / script / doc under ▶ in a node must exist
    cli = spec_cli()
    subs = set().union(*[set(v) for v in cli.values()])
    flags = set().union(*[f for v in cli.values() for f in v.values()])
    script_files = glob.glob(os.path.join(SCRIPTS, "*.py")) + glob.glob(os.path.join(SCRIPTS, "wa_bulk", "*.py"))
    for sp_ in script_files:   # add sub-commands of scripts not covered by spec_cli (e.g. send_window.py)
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
                add("N", "FAIL", f"flowchart node {nid} '{n['title']}' command `{tok}` does not exist in scripts/docs")
                bad += 1
    # N4 key numbers: numbers on the flowchart = script constants
    sys.path.insert(0, SCRIPTS)
    import search_customers as _sc, social_platforms as _sp
    sc_src = read(os.path.join(SCRIPTS, "search_customers.py"))
    bs_src = read(os.path.join(SCRIPTS, "batch_sender.py"))
    wa_src = read(os.path.join(SCRIPTS, "wa_bulk", "wa_bulk_sender.py"))
    _c = _csv_ops_consts()
    rules, mg, mt = _c["COOLDOWN_RULES"], _c["MAX_GENERIC_FOLLOWUP"], _c["MAX_TOTAL_FOLLOWUP"]
    allt = json.dumps(spec, ensure_ascii=False)
    expect = [
        (f"{len(_sc.CHANNEL_RECIPES)} discovery channels", "CHANNEL_RECIPES"),
        (f"{len(_sp.PLATFORMS)} social platforms", "social_platforms.PLATFORMS"),
        (f"{sum(len(v) for v in _sp.TITLE_TIERS.values())} procurement-chain titles", "social_platforms.TITLE_TIERS"),
        (f"sendable<{_default_of(sc_src, '--floor')} or reserve<{_default_of(sc_src, '--ahead-days')} days", "replenish --floor / --ahead-days defaults"),
        (f"dup in DB>{round(_sc.FUNNEL_DUP_DB_RED * 100)}%", "FUNNEL_DUP_DB_RED"),
        (f"named rate<{round(_sc.FUNNEL_NAMED_EMAIL_RED * 100)}%", "FUNNEL_NAMED_EMAIL_RED"),
        (" / ".join(str(rules[k]) for k in sorted(rules)) + " days", "COOLDOWN_RULES"),
        (f"={mg} ({mg + 1} e-mails sent)", "MAX_GENERIC_FOLLOWUP"),
        (f"≥{mt} ({mt + 1}+ e-mails sent)", "MAX_TOTAL_FOLLOWUP"),
    ]
    m = re.search(r'env\("DAILY_LIMIT", str\(profile_limit or (\d+)\)\)', bs_src)
    expect.append((f"≤{m.group(1) if m else '?'}/day", "batch_sender DAILY_LIMIT default"))
    m = re.search(r'env\("SEND_INTERVAL", "(\d+)"\)', bs_src)
    expect.append((f"{m.group(1) if m else '?'}s interval", "batch_sender SEND_INTERVAL default"))
    m = re.search(r"random\.uniform\((\d+), (\d+)\)\s*$", wa_src, re.M)
    expect.append((f"{m.group(1)}–{m.group(2)}s interval" if m else "?", "wa_bulk_sender pacing"))
    m = re.search(r'min\((\d+), int\(os\.environ\.get\("WA_DAILY_LIMIT"', wa_src)
    expect.append((f"{m.group(1) if m else '?'} → STOP", "WA DAILY_LIMIT cap"))
    for text, const in expect:
        if text not in allt:
            add("N", "FAIL", f"flowchart lacks '{text}' (from {const}) — numbers on the chart differ from the script")
            bad += 1
    # N5 evidence threshold: same sentence in flowchart, SKILL and research_guide
    ev = "≥1 S1 or 2 independent S2"
    if ev not in allt:
        add("N", "FAIL", f"flowchart lacks evidence threshold '{ev}'")
        bad += 1
    if not bad:
        add("N", "PASS", f"flowchart {len(spec['nodes'])} nodes / {len(spec['decisions'])} decisions: 9 step names consistent in 4 places, "
                         f"all commands exist, {len(expect)} key numbers match script constants")


def check_data_layer():
    """O data access layer + four-axis rotation: script constants match docs / flowchart / profile gate."""
    bad = 0
    import config as _cfg
    import search_customers as _sc
    import mail_setup as _ms
    import triggers as _tr
    # O1 required at install: own customer DB declaration
    if "data_sources.customer_db" not in _cfg.REQUIRED:
        add("O", "FAIL", "config.REQUIRED lacks data_sources.customer_db (own customer DB must be declared at install)")
        bad += 1
    for st in _cfg.CUSTOMER_DB_STATES:
        for doc in ("SKILL.md", "references/data_access_and_triggers.md"):
            if st not in read(os.path.join(ROOT, doc)):
                add("O", "FAIL", f"{doc} does not mention customer-DB declaration value `{st}`")
                bad += 1
    # O2 axis names: engine doc / SKILL / flowchart / search script all use Height · Breadth · Depth · Reach
    dims = ("Height", "Breadth", "Depth", "Reach")
    spec = json.load(open(os.path.join(ROOT, "references", "assets", "sop_flowchart.json"), encoding="utf-8"))
    srcs = {"references/self_replenishing_engine.md": read(os.path.join(ROOT, "references", "self_replenishing_engine.md")),
            "SKILL.md": read(os.path.join(ROOT, "SKILL.md")),
            "flowchart": json.dumps(spec, ensure_ascii=False),
            "scripts/search_customers.py": read(os.path.join(SCRIPTS, "search_customers.py"))}
    for label, text in srcs.items():
        for d in dims:
            if d not in text:
                add("O", "FAIL", f"{label} lacks axis name '{d}'")
                bad += 1
        for dep in _sc.DEPTHS:
            if label != "SKILL.md" and dep.split("_")[0] not in text:
                add("O", "FAIL", f"{label} lacks depth tier {dep}")
                bad += 1
    for p in docs() + glob.glob(os.path.join(SCRIPTS, "*.py")):
        if is_changelog(p) or p.endswith("consistency_audit.py"):
            continue
        if "高光深远" in read(p):
            add("O", "FAIL", f"{rel(p)} still uses the legacy phrase 高光深远 (since v3.1: Height/Breadth/Depth/Reach)")
            bad += 1
    # O3 trigger cooldown rules = csv_ops
    c = _csv_ops_consts()
    if _tr.COOLDOWN_RULES != c["COOLDOWN_RULES"] or _tr.MAX_GENERIC_FOLLOWUP != c["MAX_GENERIC_FOLLOWUP"]:
        add("O", "FAIL", f"triggers.py cooldown rules {_tr.COOLDOWN_RULES}/{_tr.MAX_GENERIC_FOLLOWUP} ≠ csv_ops "
                         f"{c['COOLDOWN_RULES']}/{c['MAX_GENERIC_FOLLOWUP']}")
        bad += 1
    # O4 provider presets: every host in mail_setup.py appears in mail_setup.md with a source
    md = read(os.path.join(ROOT, "references", "mail_setup.md"))
    n_hosts = 0
    for pid, pv in _ms.PROVIDERS.items():
        if pid == "custom":
            continue
        for k in ("smtp_host", "imap_host"):
            if pv[k]:
                n_hosts += 1
                if pv[k] not in md:
                    add("O", "FAIL", f"mail_setup.py preset {pid}.{k}={pv[k]} is not in references/mail_setup.md")
                    bad += 1
        if f"`{pid}`" not in md:
            add("O", "FAIL", f"references/mail_setup.md lacks a source line for provider `{pid}`")
            bad += 1
    # O5 both sender scripts wired to mailbox hosting and the opt-out header
    for name in ("batch_sender.py", "decision_maker_sender.py"):
        src = read(os.path.join(SCRIPTS, name))
        for tok in ("resolve_sender_route", "with_opt_out", "compose(", "record_usage", "maybe_auto_pause"):
            if tok not in src:
                add("O", "FAIL", f"{name} not wired to {tok} (multi-mailbox hosting / opt-out / auto-pause)")
                bad += 1
    if not bad:
        add("O", "PASS", f"data access layer consistent: customer-DB declaration required ({'/'.join(_cfg.CUSTOMER_DB_STATES)}); four axis names and 3 depth tiers consistent in engine/SKILL/flowchart/script; "
                         f"trigger cooldown = csv_ops; all {n_hosts} provider hosts sourced; both sender scripts wired to hosting and opt-out")


def main():
    for fn in (check_cli, check_profile_paths, check_tags, check_channels, check_packs,
               check_file_refs, check_env, check_csv, check_counts, check_cooldown, check_status, check_social, check_flowchart, check_data_layer):
        try:
            fn()
        except Exception as e:  # report auditor errors explicitly too
            add(fn.__name__, "FAIL", f"audit item crashed: {type(e).__name__}: {e}")
    if "--json" in sys.argv:
        print(json.dumps([{"section": s, "level": l, "message": m} for s, l, m in RESULTS],
                         ensure_ascii=False, indent=2))
    else:
        names = {"A": "CLI sub-commands & flags", "B": "profile field paths", "C": "decision-driver tags", "D": "legacy tag remnants",
                 "E": "discovery channels", "F": "industry packs", "G": "file references", "H": "environment variables", "I": "CSV headers",
                 "J": "counts & versions", "K": "cooldown rules", "L": "status values", "M": "social platforms", "N": "flowchart consistency",
                 "O": "data access layer & four axes"}
        for sec in sorted({r[0] for r in RESULTS}):
            print(f"\n[{sec}] {names.get(sec, sec)}")
            for s, l, m in RESULTS:
                if s == sec:
                    print(f"  {l:<4} {m}")
        c = {k: sum(1 for r in RESULTS if r[1] == k) for k in ("PASS", "WARN", "FAIL")}
        print(f"\nTotal: PASS {c['PASS']} · WARN {c['WARN']} · FAIL {c['FAIL']}")
    sys.exit(1 if any(r[1] == "FAIL" for r in RESULTS) else 0)


if __name__ == "__main__":
    main()
