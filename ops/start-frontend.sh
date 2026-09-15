#!/bin/bash
# フロント（Next.js）を本番モードで起動する。
#
# next dev ではなく next start を使う:
#   dev  … ファイル監視あり。重く、長時間動かすと落ちることがある
#   start … ビルド済みを配信するだけ。常時起動向き
#
# ビルドは起動前に1回だけ行う。コードを変えたら再ビルドが要る。
set -euo pipefail

cd "$(dirname "$0")/../frontend"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export NODE_ENV=production

# .next が無い（初回）か、ソースの方が新しいときだけビルドし直す
if [ ! -d .next ] || [ -n "$(find app features lib -newer .next -name '*.ts*' -print -quit 2>/dev/null)" ]; then
  echo "[start-frontend] ビルドします"
  npm run build
fi

exec npm run start -- --port 3000
