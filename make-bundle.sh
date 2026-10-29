#!/bin/bash
# 生成可 AirDrop 的装机包：桌面/新Mac装机包/ + 新Mac装机包.zip
# 用法：bash make-bundle.sh [输出目录]
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HOME/Desktop/新Mac装机包}"
REPO="https://github.com/cx8cool/lucas-write.git"

if [ -e "$OUT" ] && [ ! -f "$OUT/看我.txt" ]; then echo "$OUT 已存在且不是装机包，不敢删"; exit 1; fi
rm -rf "$OUT" "$OUT.zip"
mkdir -p "$OUT"
cp "$HERE/setup-mac.sh" "$HERE/bundle/装机.command" "$HERE/bundle/看我.txt" "$OUT/"
chmod +x "$OUT/装机.command" "$OUT/setup-mac.sh"
git clone -q "$HERE" "$OUT/lucas-write"
git -C "$OUT/lucas-write" remote set-url origin "$REPO"
ditto -c -k --keepParent "$OUT" "$OUT.zip"
echo "装好了："
echo "  $OUT"
echo "  $OUT.zip  ($(du -h "$OUT.zip" | cut -f1))"
