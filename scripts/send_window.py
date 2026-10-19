#!/usr/bin/env python3
"""Decide "can we send now" by the recipient's local time (zero external dependencies, read-only, sends nothing)

Usage:
    python3 scripts/send_window.py table [--window 09:00-11:00,14:00-16:00] [--me Asia/Shanghai]
        print each market's local time, whether it is inside the sending window, and the window in your local time
        (daylight saving is computed live by zoneinfo, not from a hard-coded offset table)
    python3 scripts/send_window.py check <REGION> [--window ...]
        single market: returns JSON {region, tz, local_time, in_window}

Sending-window source (highest priority first):
    --window argument > SEND_WINDOW environment variable > profile rules.local_send_window
    > default "09:00-11:00,14:00-16:00"

Called by batch_sender.py / decision_maker_sender.py: a contact with region whose local time is outside
the window → skipped this round (recorded in the report as deferred_window, not written to send history, sent in a later round inside the window).
SEND_WINDOW_ENFORCE=0 disables it (not recommended). Unknown regions are not blocked, only flagged.
"""
import datetime
import json
import os
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_WINDOW = "09:00-11:00,14:00-16:00"

# Market code → IANA time zone (the market's main business zone; for multi-zone countries such as the US / Australia the most common one;
# a contact may override it in the list with "tz": "America/Los_Angeles")
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

# Python 3.8 has no zoneinfo: fall back to fixed standard-time offsets (no daylight saving; flagged in the output)
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
            off = 1  # continental Europe defaults to CET
        return datetime.timezone(datetime.timedelta(hours=off)), False


def tz_for(region, explicit_tz=""):
    """Return the IANA zone name; '' when unknown."""
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
    """Return (allowed: bool|None, info: dict). None = zone unknown, not blocked."""
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
    print(f"Sending window (recipient local): {spec}   your local time: {me.strftime('%a %H:%M %Z')}")
    print(f"{'market':<12}{'time zone':<32}{'local now':<12}{'send?':<6}window start = your local time")
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
        flag = "yes" if ok else "no"
        print(f"{region:<12}{name:<32}{lt.strftime('%a %H:%M'):<12}{flag:<7}{' / '.join(starts)}"
              + ("" if exact else "  (no zoneinfo: daylight saving not included)"))


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
