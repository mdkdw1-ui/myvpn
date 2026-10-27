#!/usr/bin/env python3
"""VPN Gate 서버 목록을 받아 품질 필터 후 servers.json으로 저장."""
import csv, io, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API       = "https://www.vpngate.net/api/iphone/"
MIN_SPEED = 1_000_000   # 1 Mbps
MAX_PING  = 150         # ms
TOP_N     = 20
RETRIES   = 3

def fetch_text(url, timeout=30):
    last_err = None
    for i in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "myvpn/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last_err = e
            print(f"retry {i+1}/{RETRIES}: {e}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise SystemExit(f"fetch failed after {RETRIES} tries: {last_err}")

def parse(text):
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("*")]
    if not lines:
        return []
    header = lines[0].lstrip("#")
    return list(csv.DictReader(io.StringIO("\n".join([header] + lines[1:]))))

def to_int(v, default=0):
    try:    return int(v)
    except: return default

def filter_servers(rows):
    out = []
    for r in rows:
        ping  = to_int(r.get("Ping"), 9999)
        speed = to_int(r.get("Speed"), 0)
        if ping <= 0 or ping > MAX_PING:  continue
        if speed < MIN_SPEED:             continue
        out.append({
            "host": r.get("HostName", ""),
            "ip":   r.get("IP", ""),
            "country": r.get("CountryShort", ""),
            "country_long": r.get("CountryLong", ""),
            "ping_ms": ping,
            "speed_mbps": round(speed / 1_000_000, 2),
            "score": to_int(r.get("Score")),
            "uptime_days": to_int(r.get("Uptime")),
            "sessions": to_int(r.get("NumVpnSessions")),
        })
    out.sort(key=lambda s: (s["ping_ms"], -s["speed_mbps"]))
    return out[:TOP_N]

def main():
    rows = parse(fetch_text(API))
    print(f"total: {len(rows)}", file=sys.stderr)
    filtered = filter_servers(rows)
    print(f"passed: {len(filtered)}", file=sys.stderr)

    out_path = Path(__file__).resolve().parent / "servers.json"
    out_path.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "servers": filtered,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {out_path}", file=sys.stderr)

    for s in filtered:
        print(f"  {s['country']:3} {s['ip']:15} "
              f"ping={s['ping_ms']:>4}ms speed={s['speed_mbps']:>7.2f}Mbps "
              f"uptime={s['uptime_days']}d")

if __name__ == "__main__":
    main()
