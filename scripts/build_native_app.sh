#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/FCP Shotcut.app"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -parse-as-library "$ROOT/native/FCPShotcutApp.swift" \
  -o "$APP/Contents/MacOS/FCP Shotcut" \
  -framework Cocoa

cp "$ROOT/fcp_shotcut.py" "$APP/Contents/Resources/"
cp "$ROOT/FCP Shotcut.app/Contents/Resources/FCPShotcut.icns" "$APP/Contents/Resources/" 2>/dev/null || true
chmod +x "$APP/Contents/MacOS/FCP Shotcut"
