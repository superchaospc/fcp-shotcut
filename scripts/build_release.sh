#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-v0.1.0}"
DIST="$ROOT/dist"
STAGE="$DIST/FCP-Shotcut"

rm -rf "$DIST"
mkdir -p "$STAGE"

cp -R "$ROOT/FCP Shotcut.app" "$STAGE/"
cp "$ROOT/README.md" "$STAGE/"

find "$STAGE" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$STAGE" -type f -name '*.pyc' -delete
chmod +x "$STAGE/FCP Shotcut.app/Contents/MacOS/FCP Shotcut"

(
  cd "$DIST"
  zip -qry "FCP-Shotcut-macOS-${VERSION}.zip" "FCP-Shotcut"
)

if command -v hdiutil >/dev/null 2>&1; then
  hdiutil create \
    -volname "FCP Shotcut" \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$DIST/FCP-Shotcut-macOS-${VERSION}.dmg" >/dev/null
  echo "$DIST/FCP-Shotcut-macOS-${VERSION}.dmg"
fi

echo "$DIST/FCP-Shotcut-macOS-${VERSION}.zip"
