#!/usr/bin/env python3
"""DNS/MX mailbox-domain validator (zero external dependencies, Python standard library only)

Usage:
    python3 scripts/dns_validator.py <input.json> [output.json]

Input JSON (array; each item has at least email or website/domain):
[
  {"email": "buyer@branda.example", "brand": "Brand A"},
  {"website": "https://brandb.example", "brand": "Brand B"}
]

Output:
    valid / invalid domain lists + the MX records of each domain.
    Domains with invalid MX are marked valid=false and should not be sent to.

Implementation notes:
    - Does not depend on dnspython. Builds DNS query packets by hand (UDP, port 53)
      and asks public resolvers for MX (type=15) records.
    - If the MX query fails, falls back to an A-record lookup (socket.gethostbyname) to check that the domain exists.
    - Read-only DNS queries only: never connects to mail servers, never sends, never changes data.
    - DRY_RUN=1: only lists the de-duplicated domains that would be queried; no network requests.
"""
import json, sys, os, socket, struct, random
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Public DNS resolvers (override via environment variable)
DNS_SERVERS = os.environ.get("DNS_SERVERS", "1.1.1.1,8.8.8.8").split(",")
TIMEOUT = float(os.environ.get("DNS_TIMEOUT", "3.0"))


def _extract_domain(item):
    """Extract the bare domain from the email / website / domain fields."""
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
    """Build a DNS query packet (qtype=15 means MX)."""
    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    q = b""
    for label in domain.split("."):
        q += bytes([len(label)]) + label.encode("ascii", "ignore")
    q += b"\x00"
    q += struct.pack(">HH", qtype, 1)  # QTYPE, QCLASS=IN
    return tid, header + q


def _parse_name(data, offset):
    """Parse a DNS name (supports compression pointers); returns (name, new_offset)."""
    labels = []
    jumped = False
    orig_offset = offset
    while True:
        length = data[offset]
        if length & 0xC0 == 0xC0:  # compression pointer
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
    """Query the given DNS server for MX records; returns the list of MX hosts."""
    tid, packet = _build_query(domain, qtype=15)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(packet, (server, 53))
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()

    # Parse the header
    _, flags, qdcount, ancount, _, _ = struct.unpack(">HHHHHH", data[:12])
    offset = 12
    # Skip the question section
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
    """Validate one domain: MX first, then fall back to an A record."""
    if not domain or "." not in domain:
        return {"domain": domain, "valid": False, "mx": [], "reason": "invalid_domain_format"}

    # Try the MX query on each DNS server in turn
    for server in DNS_SERVERS:
        try:
            mx = _query_mx(domain, server.strip())
            if mx:
                return {"domain": domain, "valid": True, "mx": mx, "reason": "mx_found"}
        except Exception:
            continue

    # Fallback: A record (domain resolves but has no MX; mail capability may be limited)
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

    with open(infile, encoding="utf-8-sig") as f:
        items = json.load(f)
    if isinstance(items, dict):
        items = items.get("records", items.get("items", [items]))

    if os.environ.get("DRY_RUN", "") in ("1", "true", "yes"):
        doms = sorted({_extract_domain(it) for it in items if _extract_domain(it)})
        print(f"[DRY_RUN] would query MX for {len(doms)} domains (no network requests sent):")
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
        print(f"OK: validated {len(results)} domains, {len(valid)} valid, {len(invalid)} invalid → {outfile}")
    else:
        print(output)


if __name__ == "__main__":
    main()
