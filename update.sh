#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO="$HOME/myvpn"
DL="$HOME/storage/downloads/myvpn"
BRANCH="main"

mkdir -p "$DL"

echo "[1/4] pull $BRANCH"
cd "$REPO"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "[2/4] extract profiles"
ZIP="$DL/ovpn-profiles.zip"
if [ -f "$ZIP" ]; then
  mkdir -p "$HOME/.myvpn/profiles"
  unzip -o "$ZIP" -d "$HOME/.myvpn/profiles" >/dev/null
  chmod 600 "$HOME"/.myvpn/profiles/*.ovpn 2>/dev/null || true
fi

echo "[3/4] measure latency"
python "$REPO/measure.py"

echo "[4/4] sync to Download"
cp -f "$REPO"/*.sh "$REPO"/*.py "$REPO"/*.json "$DL"/ 2>/dev/null || true
python "$REPO/hello.py"
