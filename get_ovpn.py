#!/usr/bin/env python3
"""servers.json의 서버들에 대해 .ovpn 프로필을 추출해 out/에 저장."""
import base64, csv, io, json, sys, urllib.request
from pathlib import Path

API       = "https://www.vpngate.net/api/iphone/"
OUT_DIR   = Path(__file__).resolve().parent / "out"
SERVERS   = Path(__file__).resolve().parent / "servers.json"
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
    raise SystemExit(f"fetch failed: {last_err}")

def parse(text):
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("*")]
    if not lines:
        return []
    header = lines[0].lstrip("#")
    return list(csv.DictReader(io.StringIO("\n".join([header] + lines[1:]))))

def main():
    wanted = {s["ip"] for s in json.loads(SERVERS.read_text())["servers"]}
    rows   = parse(fetch_text(API))
    OUT_DIR.mkdir(exist_ok=True)

    saved = 0
    for r in rows:
        ip = r.get("IP")
        if ip not in wanted:
            continue
        b64 = r.get("OpenVPN_ConfigData_Base64", "")
        if not b64:
            continue
        path = OUT_DIR / f"{r.get('CountryShort','XX')}_{ip}.ovpn"
        path.write_bytes(base64.b64decode(b64))
        path.chmod(0o600)
        saved += 1
        print(f"saved: {path.name}", file=sys.stderr)

    print(f"total saved: {saved}", file=sys.stderr)
    if saved == 0:
        raise SystemExit("no profiles saved")

if __name__ == "__main__":
    main()
