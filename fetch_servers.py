#!/usr/bin/env python3
"""VPN Gate 서버 목록 수집 + OpenVPN 설정 호환성 패치 후 servers.json 저장."""
import base64
import csv
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API           = "https://www.vpngate.net/api/iphone/"
MIN_SPEED     = 1_000_000      # 1 Mbps
MAX_PING      = 150            # ms
MIN_UPTIME_MS = 86_400_000     # 1일 이상
TOP_N         = 20
RETRIES       = 3

COMPAT_BLOCK = """

# ===== myvpn compatibility patch =====
data-ciphers AES-128-CBC:AES-256-CBC:AES-256-GCM
data-ciphers-fallback AES-128-CBC
auth SHA1
tls-version-min 1.0
tls-cipher DEFAULT:@SECLEVEL=0
verb 3
"""

DROP_PREFIXES = (
    "ns-cert-type",
    "verify-x509-name",
)


def fetch_text(url, timeout=30):
    last_err = None
    for i in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "myvpn/0.2"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last_err = e
            print(f"retry {i+1}/{RETRIES}: {e}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise SystemExit(f"fetch failed: {last_err}")


def parse(text):
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("*")]
    if not lines:
        return []
    header = lines[0].lstrip("#")
    return list(csv.DictReader(io.StringIO("\n".join([header] + lines[1:]))))


def to_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def patch_openvpn_config(b64_str):
    """base64 .ovpn → 호환성 패치 → base64."""
    try:
        decoded = base64.b64decode(b64_str).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ! decode failed: {e}", file=sys.stderr)
        return None

    if not decoded.strip():
        return None

    kept = []
    for line in decoded.splitlines():
        stripped = line.strip().lower()
        if any(stripped.startswith(p) for p in DROP_PREFIXES):
            continue
        kept.append(line)

    patched = "\n".join(kept) + COMPAT_BLOCK
    return base64.b64encode(patched.encode("utf-8")).decode("utf-8")


def filter_servers(rows):
    out = []
    for r in rows:
        ping      = to_int(r.get("Ping"), 9999)
        speed     = to_int(r.get("Speed"), 0)
        uptime_ms = to_int(r.get("Uptime"), 0)
        raw_b64   = (r.get("OpenVPN_ConfigData_Base64") or "").strip()

        if ping <= 0 or ping > MAX_PING:   continue
        if speed < MIN_SPEED:              continue
        if uptime_ms < MIN_UPTIME_MS:      continue
        if not raw_b64:                    continue

        patched = patch_openvpn_config(raw_b64)
        if not patched:
            continue

        out.append({
            "host": r.get("HostName", ""),
            "ip":   r.get("IP", ""),
            "country": r.get("CountryShort", ""),
            "country_long": r.get("CountryLong", ""),
            "ping_ms": ping,
            "speed_mbps": round(speed / 1_000_000, 2),
            "score": to_int(r.get("Score")),
            "uptime_days": round(uptime_ms / 86_400_000, 1),
            "sessions": to_int(r.get("NumVpnSessions")),
            "openvpn_config_base64": patched,
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
        print(
            f"  {s['country']:3} {s['ip']:16} "
            f"ping={s['ping_ms']:>3}ms "
            f"speed={s['speed_mbps']:>7.1f}M "
            f"uptime={s['uptime_days']:>5}d",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
