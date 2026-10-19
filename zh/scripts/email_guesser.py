#!/usr/bin/env python3
"""邮箱格式猜测脚本（零外部依赖，仅用 Python 标准库）

用法:
    python3 scripts/email_guesser.py <input.json> [output.json]

输入 JSON（数组）:
[
  {"brand": "Brand A", "contact_person": "Hannah Smith", "website": "https://branda.example"},
  {"brand": "Brand B", "contact_person": "Marie Dubois", "website": "brandb.example",
   "known_format": "flast"}
]

功能:
    - 根据决策人姓名 + 域名，按 9 种常见企业邮箱格式生成候选邮箱。
    - 若提供 known_format（该公司已知的邮箱格式），优先用该格式。
    - 复用 dns_validator 对域名做 MX 验证，MX 无效的域名标记后不建议发信。

支持的格式关键字（known_format 可选值）:
    first.last / firstlast / flast / first_last / f.last /
    first / last / lastf / first-last
"""
import json, sys, os, re, importlib.util
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 动态加载同目录下的 dns_validator（避免包结构约束）
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dns_validator", os.path.join(_here, "dns_validator.py"))
_dns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dns)


def _clean(s):
    return re.sub(r"[^a-z]", "", (s or "").strip().lower())


def _split_name(full_name):
    """把姓名拆成 first / last（取首末词，忽略中间名）。"""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return _clean(parts[0]), ""
    return _clean(parts[0]), _clean(parts[-1])


FORMAT_BUILDERS = {
    "first.last": lambda f, l: f"{f}.{l}" if l else f,
    "firstlast":  lambda f, l: f"{f}{l}",
    "flast":      lambda f, l: f"{f[0]}{l}" if f and l else f,
    "first_last": lambda f, l: f"{f}_{l}" if l else f,
    "f.last":     lambda f, l: f"{f[0]}.{l}" if f and l else f,
    "first":      lambda f, l: f,
    "last":       lambda f, l: l or f,
    "lastf":      lambda f, l: f"{l}{f[0]}" if f and l else f,
    "first-last": lambda f, l: f"{f}-{l}" if l else f,
}

# 默认猜测顺序（可靠性从高到低）
DEFAULT_ORDER = ["first.last", "flast", "firstlast", "first_last",
                 "f.last", "first", "lastf", "first-last", "last"]


def guess_for(contact, domain):
    first, last = _split_name(contact)
    local_parts, seen = [], set()
    for fmt in DEFAULT_ORDER:
        local = FORMAT_BUILDERS[fmt](first, last)
        if local and local not in seen:
            seen.add(local)
            local_parts.append((fmt, local))
    return [(fmt, f"{local}@{domain}") for fmt, local in local_parts]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else None

    with open(infile, encoding="utf-8-sig") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = items.get("records", items.get("items", [items]))

    mx_cache = {}
    results = []
    for item in items:
        domain = _dns._extract_domain(item)
        contact = item.get("contact_person") or item.get("contact") or ""
        if not domain or not contact:
            results.append({**item, "guessed_emails": [], "mx_valid": False,
                            "note": "missing_domain_or_contact"})
            continue

        # MX 验证（带缓存）
        if domain not in mx_cache:
            mx_cache[domain] = _dns.validate_domain(domain)
        mx = mx_cache[domain]

        known = (item.get("known_format") or "").strip().lower()
        candidates = []
        if known in FORMAT_BUILDERS:
            first, last = _split_name(contact)
            local = FORMAT_BUILDERS[known](first, last)
            if local:
                candidates.append({"format": known, "email": f"{local}@{domain}",
                                   "priority": "known_format"})
        # 补充默认格式候选
        for fmt, email in guess_for(contact, domain):
            if not any(c["email"] == email for c in candidates):
                candidates.append({"format": fmt, "email": email, "priority": "guessed"})

        results.append({
            "brand": item.get("brand", ""),
            "contact_person": contact,
            "domain": domain,
            "mx_valid": mx["valid"],
            "mx_reason": mx["reason"],
            "guessed_emails": candidates,
            "recommended": candidates[0]["email"] if candidates else "",
        })

    summary = {
        "total": len(results),
        "mx_valid_count": len([r for r in results if r.get("mx_valid")]),
        "results": results,
    }
    output = json.dumps(summary, ensure_ascii=False, indent=2)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK: 为 {len(results)} 位联系人生成候选邮箱 → {outfile}")
    else:
        print(output)


if __name__ == "__main__":
    main()
