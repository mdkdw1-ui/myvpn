#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="$HOME/myvpn"
DL="$HOME/storage/downloads/myvpn"
BRANCH="main"

mkdir -p "$DL"
cd "$REPO"

echo "═══ [1/5] pull origin/$BRANCH ═══"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "═══ [2/5] patches check ═══"
python - <<'PY'
import json
from pathlib import Path

p = Path.home() / "myvpn" / "servers.json"
if not p.exists():
    print("  servers.json 없음 → Actions가 먼저 돌아야 함")
    raise SystemExit(0)

d = json.loads(p.read_text())
total = len(d.get("servers", []))
with_cfg = sum(1 for s in d.get("servers", []) if s.get("openvpn_config_base64"))
patched = 0
for s in d.get("servers", []):
    cfg_b64 = s.get("openvpn_config_base64", "")
    if not cfg_b64:
        continue
    try:
        import base64
        decoded = base64.b64decode(cfg_b64).decode("utf-8", errors="ignore")
        if "myvpn compatibility patch" in decoded:
            patched += 1
    except Exception:
        pass

print(f"  servers    : {total}")
print(f"  with_config: {with_cfg}")
print(f"  patched    : {patched}  (compat block 포함)")
if patched == 0:
    print("  ⚠️  패치된 설정이 없음 → Actions refresh 재실행 필요")
PY

echo "═══ [3/5] latency measure ═══"
if [ -f "$REPO/measure.py" ]; then
    python "$REPO/measure.py" || echo "  measure.py 실패 (무시)"
else
    echo "  measure.py 없음 → skip"
fi

echo "═══ [4/5] sync to Download ═══"
cp -f "$REPO"/*.sh  "$DL"/ 2>/dev/null || true
cp -f "$REPO"/*.py  "$DL"/ 2>/dev/null || true
cp -f "$REPO"/*.json "$DL"/ 2>/dev/null || true
ls -la "$DL"/ | sed 's/^/  /'

echo "═══ [5/5] summary ═══"
python - <<'PY'
import json
from pathlib import Path

p = Path.home() / "myvpn" / "servers.json"
d = json.loads(p.read_text())
print(f"  updated: {d.get('updated')}")
print(f"  count  : {len(d.get('servers', []))}")
print("  top5:")
for s in d.get("servers", [])[:5]:
    m = s.get("measured_ms")
    m_str = f"{m:.1f}ms" if m else "n/a"
    print(f"    {s['country']} {s['ip']:16} ping={s['ping_ms']}ms measured={m_str} speed={s['speed_mbps']}M")
PY

echo ""
echo "✅ done. 다음 단계:"
echo "   hivpn 앱에서 서버 재선택 → 연결 테스트"
echo ""
