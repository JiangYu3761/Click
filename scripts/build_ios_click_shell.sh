#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

xcodebuild \
  -project "$ROOT_DIR/apps/ios/ClickShell/ClickShell.xcodeproj" \
  -scheme ClickShell \
  -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO \
  build
