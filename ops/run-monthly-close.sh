#!/bin/bash
# 月末自動締めを1回実行する。launchd から毎日 23:59 に呼ばれる。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# launchd は最小限の PATH しか渡さない。
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

cd "$REPO/backend"
uv run python scripts/monthly_close.py
