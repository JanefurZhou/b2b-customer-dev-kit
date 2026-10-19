#!/usr/bin/env python3
"""按收件人当地时间判断「现在能不能发」（零外部依赖，只读，不发任何东西）

用法:
    python3 scripts/send_window.py table [--window 09:00-11:00,14:00-16:00] [--me Asia/Shanghai]
        打印各市场的当地时间、是否在发信窗口内、窗口对应的「你本机时间」
        （夏令时由 zoneinfo 实时计算，不靠写死的时差表）
    python3 scripts/send_window.py check <REGION> [--window ...]
        单个市场：返回 JSON {region, tz, local_time, in_window}

发信窗口来源（优先级从高到低）:
    --window 参数 > 环境变量 SEND_WINDOW > 档案 rules.local_send_window
    > 默认 "09:00-11:00,14:00-16:00"

被 batch_sender.py / decision_maker_sender.py 调用：联系人带 region 且当地时间不在
窗口内 → 本轮跳过（记入报告 deferred_window，不写发送历史，下一轮窗口内再发）。
设 SEND_WINDOW_ENFORCE=0 可关闭（不推荐）。region 不认识时不拦截，只提示。
"""
import datetime
import json
import os
import sys
for _s in (sys.stdout, sys.stderr):  # Windows 重定向/GBK 终端下中文不乱码不报错
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_WINDOW = "09:00-11:00,14:00-16:00"

# 市场代码 → IANA 时区（取该市场的主要商务时区；美国/澳洲等多时区用最常见的一个，
# 联系人可在清单里直接写 "tz": "America/Los_Angeles" 覆盖）
REGION_TZ = {
    "US": "America/New_York", "USA": "America/New_York", "US-EAST": "America/New_York",
    "US-WEST": "America/Los_Angeles", "US-CENTRAL": "America/Chicago",
    "CA": "America/Toronto", "MX": "America/Mexico_City", "BR": "America/Sao_Paulo",
    "AR": "America/Argentina/Buenos_Aires", "CL": "America/Santiago", "CO": "America/Bogota",
    "UK": "Europe/London", "GB": "Europe/London", "IE": "Europe/Dublin",
    "DE": "Europe/Berlin", "FR": "Europe/Paris", "IT": "Europe/Rome", "ES": "Europe/Madrid",
    "NL": "Europe/Amsterdam", "BE": "Europe/Brussels", "CH": "Europe/Zurich",
    "AT": "Europe/Vienna", "PT": "Europe/Lisbon", "SE": "Europe/Stockholm",
    "NO": "Europe/Oslo", "DK": "Europe/Copenhagen", "FI": "Europe/Helsinki",
    "PL": "Europe/Warsaw", "CZ": "Europe/Prague", "GR": "Europe/Athens",
    "TR": "Europe/Istanbul", "RU": "Europe/Moscow",
    "AE": "Asia/Dubai", "UAE": "Asia/Dubai", "SA": "Asia/Riyadh", "QA": "Asia/Qatar",
    "IL": "Asia/Jerusalem", "EG": "Africa/Cairo", "ZA": "Africa/Johannesburg",
    "NG": "Africa/Lagos", "KE": "Africa/Nairobi",
    "IN": "Asia/Kolkata", "PK": "Asia/Karachi", "BD": "Asia/Dhaka",
    "TH": "Asia/Bangkok", "VN": "Asia/Ho_Chi_Minh", "ID": "Asia/Jakarta",
    "MY": "Asia/Kuala_Lumpur", "SG": "Asia/Singapore", "PH": "Asia/Manila",
    "CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong", "TW": "Asia/Taipei",
    "JP": "Asia/Tokyo", "KR": "Asia/Seoul",
    "AU": "Australia/Sydney", "AU-WEST": "Australia/Perth", "NZ": "Pacific/Auckland",
}

# Python 3.8 没有 zoneinfo：退回「标准时间」固定偏移（不含夏令时，会提示）
_FIXED_OFFSET_H = {
    "America/New_York": -5, "America/Los_Angeles": -8, "America/Chicago": -6,
    "America/Toronto": -5, "America/Mexico_City": -6, "America/Sao_Paulo": -3,
    "Europe/London": 0, "Europe/Dublin": 0, "Europe/Lisbon": 0, "Europe/Moscow": 3,
    "Europe/Istanbul": 3, "Asia/Dubai": 4, "Asia/Riyadh": 3, "Asia/Kolkata": 5.5,
    "Asia/Bangkok": 7, "Asia/Jakarta": 7, "Asia/Ho_Chi_Minh": 7, "Asia/Singapore": 8,
    "Asia/Kuala_Lumpur": 8, "Asia/Manila": 8, "Asia/Shanghai": 8, "Asia/Hong_Kong": 8,
    "Asia/Taipei": 8, "Asia/Tokyo": 9, "Asia/Seoul": 9, "Australia/Sydney": 10,
    "Australia/Perth": 8, "Pacific/Auckland": 12, "Africa/Johannesburg": 2,
}


def _tz(name):
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        return ZoneInfo(name), True
    except Exception:
        off = _FIXED_OFFSET_H.get(name)
        if off is None:
            off = 1  # 欧洲大陆默认 CET
        return datetime.timezone(datetime.timedelta(hours=off)), False


def tz_for(region, explicit_tz=""):
    """返回 IANA 时区名；认不出返回 ''。"""
    if explicit_tz:
        return explicit_tz
    return REGION_TZ.get((region or "").strip().upper().replace(" ", "-"), "")


def parse_window(spec):
    """'09:00-11:00,14:00-16:00' → [((9,0),(11,0)), ((14,0),(16,0))]"""
    out = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part or "-" not in part:
            continue
        a, b = part.split("-", 1)
        try:
            ha, ma = (int(x) for x in a.strip().split(":"))
            hb, mb = (int(x) for x in b.strip().split(":"))
        except ValueError:
            continue
        out.append(((ha, ma), (hb, mb)))
    return out


def window_spec(profile=None, cli=""):
    if cli:
        return cli
    if os.environ.get("SEND_WINDOW"):
        return os.environ["SEND_WINDOW"]
    try:
        spec = ((profile or {}).get("rules") or {}).get("local_send_window") or ""
    except AttributeError:
        spec = ""
    return spec or DEFAULT_WINDOW


def local_now(tzname, now_utc=None):
    tz, exact = _tz(tzname)
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    return now_utc.astimezone(tz), exact


def in_window(region, spec, explicit_tz="", now_utc=None):
    """返回 (allowed: bool|None, info: dict)。None = 认不出时区，不拦截。"""
    name = tz_for(region, explicit_tz)
    if not name:
        return None, {"region": region, "tz": "", "reason": "unknown region; not enforced"}
    lt, exact = local_now(name, now_utc)
    if lt.weekday() >= 5:
        return False, {"region": region, "tz": name, "local_time": lt.strftime("%a %H:%M"),
                       "reason": "local weekend", "dst_exact": exact}
    cur = (lt.hour, lt.minute)
    ok = any(a <= cur < b for a, b in parse_window(spec))
    return ok, {"region": region, "tz": name, "local_time": lt.strftime("%a %H:%M"),
                "window": spec, "dst_exact": exact}


def enforce_enabled():
    return os.environ.get("SEND_WINDOW_ENFORCE", "1") not in ("0", "false", "no")


def _load_profile_quiet():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import config as _c
        return _c.load_profile(require_complete=False)
    except Exception:
        return {}


def cmd_table(spec, me_tz=""):
    now = datetime.datetime.now(datetime.timezone.utc)
    me = now.astimezone(_tz(me_tz)[0]) if me_tz else datetime.datetime.now().astimezone()
    print(f"发信窗口（收件人当地）：{spec}   你的本机时间：{me.strftime('%a %H:%M %Z')}")
    print(f"{'市场':<12}{'时区':<32}{'当地现在':<12}{'可发?':<6}窗口起点 = 你本机时间")
    shown = set()
    for region, name in REGION_TZ.items():
        if name in shown:
            continue
        shown.add(name)
        ok, info = in_window(region, spec, now_utc=now)
        lt, exact = local_now(name, now)
        starts = []
        for (ha, ma), _ in parse_window(spec):
            start_local = lt.replace(hour=ha, minute=ma, second=0, microsecond=0)
            starts.append(start_local.astimezone(me.tzinfo).strftime("%H:%M"))
        flag = "是" if ok else "否"
        print(f"{region:<12}{name:<32}{lt.strftime('%a %H:%M'):<12}{flag:<7}{' / '.join(starts)}"
              + ("" if exact else "  (无 zoneinfo：未含夏令时)"))


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0 if args else 1)
    cli = ""
    if "--window" in args:
        i = args.index("--window")
        cli = args[i + 1] if i + 1 < len(args) else ""
        args = args[:i] + args[i + 2:]
    me_tz = ""
    if "--me" in args:
        i = args.index("--me")
        me_tz = args[i + 1] if i + 1 < len(args) else ""
        args = args[:i] + args[i + 2:]
    spec = window_spec(_load_profile_quiet(), cli)
    if args[0] == "table":
        cmd_table(spec, me_tz)
    elif args[0] == "check" and len(args) > 1:
        ok, info = in_window(args[1], spec)
        info["in_window"] = ok
        print(json.dumps(info, ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
