#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO="$HOME/myvpn"
DL="$HOME/storage/downloads/myvpn"
BRANCH="main"

mkdir -p "$DL"

echo "[1/3] pull $BRANCH"
cd "$REPO"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "[2/3] copy to Download"
cp -f "$REPO"/*.sh "$REPO"/*.py "$DL"/ 2>/dev/null || true

echo "[3/3] run in Termux"
chmod +x "$REPO"/*.sh 2>/dev/null || true
python "$REPO/hello.py"
