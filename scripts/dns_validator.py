#!/usr/bin/env python3
"""DNS/MX 邮箱域名验证脚本（零外部依赖，仅用 Python 标准库）

用法:
    python3 scripts/dns_validator.py <input.json> [output.json]

输入 JSON（数组，每项至少含 email 或 website/domain）:
[
  {"email": "buyer@branda.example", "brand": "Brand A"},
  {"website": "https://brandb.example", "brand": "Brand B"}
]

输出:
    有效/无效域名列表 + 每个域名的 MX 记录。
    MX 无效的域名标记 valid=false，不应向其发信。

实现说明:
    - 不依赖 dnspython。手工构造 DNS 查询报文（UDP，端口53），
      向公共 DNS 解析器查询 MX（type=15）记录。
    - 若 MX 查询失败，回退查询 A 记录（socket.gethostbyname）判断域名是否存在。
    - 只做只读 DNS 查询，不连接邮件服务器、不发信、不改数据。
    - DRY_RUN=1：只列出将要查询的去重域名，不发出任何网络请求。
"""
import json, sys, os, socket, struct, random

# 公共 DNS 解析器（可用环境变量覆盖）
DNS_SERVERS = os.environ.get("DNS_SERVERS", "1.1.1.1,8.8.8.8").split(",")
TIMEOUT = float(os.environ.get("DNS_TIMEOUT", "3.0"))


def _extract_domain(item):
    """从 email / website / domain 字段提取纯域名。"""
    if item.get("domain"):
        d = item["domain"]
    elif item.get("email") and "@" in item["email"]:
        d = item["email"].split("@")[-1]
    elif item.get("website"):
        d = item["website"]
    else:
        return ""
    d = d.strip().lower()
    for pre in ("https://", "http://"):
        if d.startswith(pre):
            d = d[len(pre):]
    d = d.split("/")[0].split(":")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def _build_query(domain, qtype=15):
    """构造一个 DNS 查询报文（qtype=15 表示 MX）。"""
    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    q = b""
    for label in domain.split("."):
        q += bytes([len(label)]) + label.encode("ascii", "ignore")
    q += b"\x00"
    q += struct.pack(">HH", qtype, 1)  # QTYPE, QCLASS=IN
    return tid, header + q


def _parse_name(data, offset):
    """解析 DNS 名称（支持压缩指针），返回 (name, new_offset)。"""
    labels = []
    jumped = False
    orig_offset = offset
    while True:
        length = data[offset]
        if length & 0xC0 == 0xC0:  # 压缩指针
            pointer = struct.unpack(">H", data[offset:offset + 2])[0] & 0x3FFF
            if not jumped:
                orig_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        if length == 0:
            offset += 1
            break
        labels.append(data[offset + 1:offset + 1 + length].decode("ascii", "ignore"))
        offset += 1 + length
    return ".".join(labels), (orig_offset if jumped else offset)


def _query_mx(domain, server):
    """向指定 DNS 服务器查询 MX 记录，返回 MX 主机列表。"""
    tid, packet = _build_query(domain, qtype=15)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()

    # 解析报文头
    _, flags, qdcount, ancount, _, _ = struct.unpack(">HHHHHH", data[:12])
    offset = 12
    # 跳过 question 段
    for _ in range(qdcount):
        _, offset = _parse_name(data, offset)
        offset += 4  # QTYPE + QCLASS

    mx_hosts = []
    for _ in range(ancount):
        _, offset = _parse_name(data, offset)
        rtype, rclass, ttl, rdlength = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        if rtype == 15:  # MX
            preference = struct.unpack(">H", data[offset:offset + 2])[0]
            exchange, _ = _parse_name(data, offset + 2)
            mx_hosts.append((preference, exchange))
        offset += rdlength
    mx_hosts.sort()
    return [h for _, h in mx_hosts]


def validate_domain(domain):
    """验证单个域名：先查 MX，再回退查 A 记录。"""
    if not domain or "." not in domain:
        return {"domain": domain, "valid": False, "mx": [], "reason": "invalid_domain_format"}

    # 逐个 DNS 服务器尝试 MX 查询
    for server in DNS_SERVERS:
        try:
            mx = _query_mx(domain, server.strip())
            if mx:
                return {"domain": domain, "valid": True, "mx": mx, "reason": "mx_found"}
        except Exception:
            continue

    # 回退：A 记录（域名能解析但没有 MX，可能收发能力受限）
    try:
        socket.setdefaulttimeout(TIMEOUT)
        socket.gethostbyname(domain)
        return {"domain": domain, "valid": False, "mx": [],
                "reason": "no_mx_but_a_record"}
    except Exception:
        return {"domain": domain, "valid": False, "mx": [], "reason": "domain_not_resolvable"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else None

    with open(infile, encoding="utf-8") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = items.get("records", items.get("items", [items]))

    if os.environ.get("DRY_RUN", "") in ("1", "true", "yes"):
        doms = sorted({_extract_domain(it) for it in items if _extract_domain(it)})
        print(f"[DRY_RUN] 将查询 {len(doms)} 个域名的 MX（未发出网络请求）：")
        for d in doms:
            print("  ", d)
        return

    seen = {}
    results = []
    for item in items:
        domain = _extract_domain(item)
        if domain in seen:
            res = dict(seen[domain])
        else:
            res = validate_domain(domain)
            seen[domain] = res
        out = dict(item)
        out.update({"domain": domain, "mx_valid": res["valid"],
                    "mx_records": res["mx"], "mx_reason": res["reason"]})
        results.append(out)

    valid = [r for r in results if r["mx_valid"]]
    invalid = [r for r in results if not r["mx_valid"]]
    summary = {
        "total": len(results),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "valid": valid,
        "invalid": invalid,
    }

    output = json.dumps(summary, ensure_ascii=False, indent=2)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK: 验证 {len(results)} 个域名，有效 {len(valid)}，无效 {len(invalid)} → {outfile}")
    else:
        print(output)


if __name__ == "__main__":
    main()
