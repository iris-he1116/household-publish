#!/bin/bash
# バックエンド（FastAPI）を本番モードで起動する。
# launchd から呼ばれる。手動で動かすときは直接実行してもよい。
set -euo pipefail

cd "$(dirname "$0")/../backend"

# launchd は最小限の PATH しか渡さないので、uv の場所を通す
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# --reload を付けない（本番）。ワーカー1つで十分（利用者2人）
exec uv run uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info
