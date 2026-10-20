#!/usr/bin/env python3
"""Customs import-record summary (standard library only; b2b-customer-dev-kit v3.2,
same logic as customer-background-investigation).

Export import bills of lading (ImportYeti / 52wmb etc.) to CSV and get:
shipment count, date span, last shipment and days since, average and monthly TEU,
origin-country and supplier shares, HS chapters, median purchase interval, next
purchase window (inferred), scale tier, and automatic signals: import stoppage,
single-supplier dependence, new category, small sample.

CSV headers are case-insensitive; aliases accepted (Chinese headers too):
  date      : date, arrival_date, shipment_date, 日期, 到港日期
  origin    : origin, country, origin_country, 供应国, 起运国
  supplier  : supplier, shipper, 供应商, 发货人
  hs        : hs, hs_code, hscode, HS编码
  teu       : teu, containers, 柜量
  product   : product, description, 品名, 货物描述

Usage:
    python3 scripts/customs_summary.py shipments.csv
    python3 scripts/customs_summary.py shipments.csv --inquiry-hs 6301,5806 --md
    python3 scripts/customs_summary.py shipments.csv --today 2026-10-21
    python3 scripts/customs_summary.py --selftest

Every "next purchase window" is an inference from past intervals; label it "inferred".
"""
import argparse
import csv
import datetime as dt
import io
import json
import statistics
import sys
from collections import Counter

ALIASES = {
    "date": ["date", "arrival_date", "shipment_date", "arrival date", "日期", "到港日期"],
    "origin": ["origin", "country", "origin_country", "origin country", "供应国", "起运国"],
    "supplier": ["supplier", "shipper", "供应商", "发货人"],
    "hs": ["hs", "hs_code", "hscode", "hs code", "hs编码"],
    "teu": ["teu", "containers", "柜量"],
    "product": ["product", "description", "品名", "货物描述"],
}


def _map_header(fields):
    m = {}
    for f in fields or []:
        k = (f or "").strip().lower()
        for std, al in ALIASES.items():
            if k in al and std not in m:
                m[std] = f
    return m


def _date(s):
    s = (s or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _float(s):
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return None


def load(text):
    rd = csv.DictReader(io.StringIO(text))
    hm = _map_header(rd.fieldnames)
    if "date" not in hm:
        raise ValueError("CSV has no date column (date / arrival_date / 日期)")
    rows = []
    for r in rd:
        d = _date(r.get(hm["date"]))
        if not d:
            continue
        rows.append({
            "date": d,
            "origin": (r.get(hm.get("origin", ""), "") or "").strip() or "unknown",
            "supplier": (r.get(hm.get("supplier", ""), "") or "").strip() or "unknown",
            "hs": "".join(c for c in (r.get(hm.get("hs", ""), "") or "") if c.isdigit())[:6],
            "teu": _float(r.get(hm.get("teu", ""), "")),
            "product": (r.get(hm.get("product", ""), "") or "").strip(),
        })
    rows.sort(key=lambda x: x["date"])
    return rows


def _share(counter, n):
    return [(k, v, round(100 * v / n)) for k, v in counter.most_common(3)]


def summarize(rows, today=None, inquiry_hs=None):
    today = today or dt.date.today()
    n = len(rows)
    out = {"shipments": n, "signals": []}
    if n == 0:
        out["signals"].append(("ℹ️", "No usable records: write customs data as \"not obtained\"; it does not mean the buyer never imports"))
        return out
    first, last = rows[0]["date"], rows[-1]["date"]
    span_days = max((last - first).days, 1)
    months = max(span_days / 30.44, 1)
    teus = [r["teu"] for r in rows if r["teu"] is not None]
    total_teu = sum(teus) if teus else None
    gaps = [(b["date"] - a["date"]).days for a, b in zip(rows, rows[1:]) if (b["date"] - a["date"]).days > 0]
    med = statistics.median(gaps) if gaps else None
    since = (today - last).days
    monthly_teu = round(total_teu / months, 2) if total_teu is not None else None
    if monthly_teu is None:
        tier = "not obtained (no TEU column)"
    elif monthly_teu < 0.5:
        tier = "small-batch"
    elif monthly_teu <= 3:
        tier = "mid-volume"
    else:
        tier = "bulk"
    hs_counter = Counter(r["hs"][:4] for r in rows if r["hs"])
    out.update({
        "first": first.isoformat(), "last": last.isoformat(), "days_since_last": since,
        "avg_teu": round(total_teu / len(teus), 2) if teus else None,
        "monthly_teu": monthly_teu, "tier": tier,
        "origins": _share(Counter(r["origin"] for r in rows), n),
        "suppliers": _share(Counter(r["supplier"] for r in rows), n),
        "hs4": hs_counter.most_common(5),
        "median_gap_days": med,
        "next_window": None,
    })
    if med:
        nxt = last + dt.timedelta(days=int(med))
        lo, hi = nxt - dt.timedelta(days=int(med * 0.25)), nxt + dt.timedelta(days=int(med * 0.25))
        out["next_window"] = f"{lo.isoformat()} ~ {hi.isoformat()} (inferred)"
    if n < 3:
        out["signals"].append(("ℹ️", f"Small sample ({n} shipments): treat the statistics as indicative only"))
    if med and since > 2 * med and since > 180:
        out["signals"].append(("🟡", f"Import stoppage: {since} days since the last shipment, more than twice the median interval ({int(med)} days); ask why"))
    top_sup = out["suppliers"][0]
    if n >= 3 and top_sup[2] > 70:
        out["signals"].append(("ℹ️", f"Single-supplier dependence: {top_sup[0]} holds {top_sup[2]}%; harder to break in"))
    if inquiry_hs:
        hist = {r["hs"] for r in rows if r["hs"]}
        missing = [h for h in inquiry_hs if not any(x.startswith(h[:4]) for x in hist)]
        if missing:
            out["signals"].append(("ℹ️", f"New category: {','.join(missing)} not in past imports; no purchase history to compare"))
    return out


def to_md(s):
    if s["shipments"] == 0:
        return "| Import records | not obtained |\n|---|---|\n" + "\n".join(f"\n- {a} {b}" for a, b in s["signals"])
    fmt = lambda lst: "; ".join(f"{k} {p}%" for k, _, p in lst)
    lines = [
        "| Item | Result |", "|---|---|",
        f"| Shipments / span | {s['shipments']}, {s['first']} ~ {s['last']} |",
        f"| Last shipment | {s['last']} ({s['days_since_last']} days ago) |",
        f"| Avg TEU per shipment / monthly TEU | {s['avg_teu'] if s['avg_teu'] is not None else 'not obtained'} / {s['monthly_teu'] if s['monthly_teu'] is not None else 'not obtained'} |",
        f"| Scale tier | {s['tier']} |",
        f"| Origin share (top 3) | {fmt(s['origins'])} |",
        f"| Supplier share (top 3) | {fmt(s['suppliers'])} |",
        f"| HS chapters (4-digit) | {', '.join(f'{k}×{v}' for k, v in s['hs4']) or 'not obtained'} |",
        f"| Median purchase interval | {str(int(s['median_gap_days'])) + ' days' if s['median_gap_days'] else 'not obtained'} |",
        f"| Next purchase window | {s['next_window'] or 'not obtained'} |",
    ]
    if s["signals"]:
        lines.append("")
        lines += [f"- {a} {b}" for a, b in s["signals"]]
    return "\n".join(lines)


def _selftest():
    T = dt.date(2026, 10, 21)
    csv1 = "Arrival Date,Country,Shipper,HS Code,TEU\n" + "\n".join(
        f"2025-{m:02d}-10,China,Mill A,630140,0.2" for m in range(1, 13, 2)) + "\n2025-11-20,India,Mill B,580610,0.1\n"
    csv2 = "日期,供应国,供应商,HS编码,柜量\n2023-01-05,越南,厂甲,6301,2\n2023-02-05,越南,厂甲,6301,2\n2023-03-07,越南,厂甲,6301,2\n2023-04-06,越南,厂甲,6301,2\n"
    csv3 = "date,origin,supplier,hs,teu\n" + "\n".join(f"2026-{m:02d}-01,China,Big Co,940490,5" for m in range(1, 11))
    s1 = summarize(load(csv1), T, ["6301", "6006"])
    s2 = summarize(load(csv2), T)
    s3 = summarize(load(csv3), T)
    s0 = summarize([], T)
    cases = [
        ("English header aliases recognised", s1["shipments"] == 7),
        ("monthly TEU < 0.5 -> small-batch", s1["tier"] == "small-batch"),
        ("inquiry HS not in history -> new-category signal", any("6006" in b for _, b in s1["signals"])),
        ("Chinese headers recognised + single-supplier dependence", s2["shipments"] == 4 and any("Single-supplier" in b for _, b in s2["signals"])),
        ("stopped 3 years ago -> import stoppage", any("Import stoppage" in b for _, b in s2["signals"])),
        ("monthly TEU > 3 -> bulk", s3["tier"] == "bulk"),
        ("steady recent buying -> no stoppage", not any("Import stoppage" in b for _, b in s3["signals"])),
        ("next window labelled inferred", "inferred" in (s3["next_window"] or "")),
        ("no records -> not obtained, not 'never imports'", s0["shipments"] == 0 and "not obtained" in s0["signals"][0][1]),
        ("Markdown output has scale tier", "Scale tier" in to_md(s1)),
    ]
    fails = 0
    for name, ok in cases:
        fails += not ok
        print(("PASS " if ok else "FAIL ") + name)
    print("\nALL PASS" if not fails else f"\n{fails} failed")
    return fails


def main():
    ap = argparse.ArgumentParser(description="Customs import-record summary")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--inquiry-hs", help="inquiry HS codes, comma-separated")
    ap.add_argument("--today", help="reference date YYYY-MM-DD, default today")
    ap.add_argument("--md", action="store_true", help="print a Markdown table")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if _selftest() else 0)
    if not a.csv:
        ap.error("a CSV file is required, or use --selftest")
    with open(a.csv, encoding="utf-8-sig", errors="ignore") as f:
        rows = load(f.read())
    today = _date(a.today) if a.today else None
    hs = [h.strip() for h in a.inquiry_hs.split(",")] if a.inquiry_hs else None
    s = summarize(rows, today, hs)
    print(to_md(s) if a.md else json.dumps(s, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
