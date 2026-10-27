#!/usr/bin/env python3
"""servers.json의 각 서버에 TCP connect 3회 → measured_ms 병합."""
import json, re, socket, statistics, time
from pathlib import Path

HOME     = Path.home()
SERVERS  = HOME / "myvpn" / "servers.json"
PROFILES = HOME / ".myvpn" / "profiles"
ROUNDS   = 3
TIMEOUT  = 5.0

def parse_remote(ovpn: Path):
    proto, host, port = None, None, None
    for line in ovpn.read_text(errors="ignore").splitlines():
        m = re.match(r'^proto\s+(\w+)', line)
        if m: proto = m.group(1).lower()
        m = re.match(r'^remote\s+(\S+)\s+(\d+)', line)
        if m: host, port = m.group(1), int(m.group(2))
    return proto, host, port

def tcp_connect_ms(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    t0 = time.perf_counter()
    try:
        s.connect((host, port))
        return (time.perf_counter() - t0) * 1000
    except Exception:
        return None
    finally:
        s.close()

def main():
    data = json.loads(SERVERS.read_text())
    for s in data["servers"]:
        prof = PROFILES / f"{s['country']}_{s['ip']}.ovpn"
        if not prof.exists():
            s["measured_ms"] = None
            continue
        proto, host, port = parse_remote(prof)
        if proto != "tcp" or not host:
            s["measured_ms"] = None
            s["note"] = "udp-or-noport"
            continue
        samples = [tcp_connect_ms(host, port) for _ in range(ROUNDS)]
        ok = [x for x in samples if x is not None]
        s["measured_ms"] = round(statistics.mean(ok), 1) if ok else None
        print(f"{s['country']} {s['ip']:15} tcp/{port} measured={s['measured_ms']}ms")

    SERVERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for s in data["servers"] if s.get("measured_ms"))
    print(f"measured: {ok}/{len(data['servers'])}")

if __name__ == "__main__":
    main()
