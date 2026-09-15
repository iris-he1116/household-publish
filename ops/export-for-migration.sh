#!/bin/bash
# 別の PC へ引っ越すための一式を書き出す。
#
#   ./ops/export-for-migration.sh
#
# 出力: migration_YYYYMMDD_HHMMSS.tar.gz
#
# 中身:
#   household.sql  … DB 全体（支出・カテゴリ・ユーザー・PayPay 取り込み）
#   env.txt        … .env の設定値（パスワードと鍵を含む）
#   README.txt     … 移行先での手順
#
# ★ この tar.gz は秘密情報を含む。
#   USB か AirDrop で運び、移行が済んだら消すこと。
#   クラウドストレージやチャットに上げない。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/podman/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

STAMP=$(date +%Y%m%d_%H%M%S)
WORK=$(mktemp -d)
OUT="$REPO/migration_${STAMP}.tar.gz"

trap 'rm -rf "$WORK"' EXIT

echo "[1/3] DB を書き出しています..."
if ! podman exec household_db pg_dump -U household_user household > "$WORK/household.sql" 2>/dev/null; then
  echo "失敗: コンテナ household_db が動いていません" >&2
  exit 1
fi
grep -q "CREATE TABLE" "$WORK/household.sql" || { echo "失敗: ダンプが不正です" >&2; exit 1; }

echo "[2/3] 設定を書き出しています..."
cp "$REPO/.env" "$WORK/env.txt"

cat > "$WORK/README.txt" <<'TXT'
家計清算アプリ - 移行手順

【中身】
  household.sql  DB 全体のダンプ
  env.txt        .env の中身（パスワードと JWT 鍵を含む）

【移行先の PC でやること】

1. リポジトリを clone
     git clone <リポジトリURL> alice_work
     cd alice_work

2. env.txt を .env として置く
     cp /path/to/env.txt .env

3. Podman をインストールして起動
     brew install podman
     podman machine init
     podman machine start
     pip3 install --user podman-compose
     podman-compose up -d

4. DB を復元（マイグレーションは実行しない。ダンプに全部入っている）
     cat household.sql | podman exec -i household_db psql -U household_user -d household

5. バックエンドの依存を入れる
     cd backend && uv sync

6. フロントの依存を入れてビルド
     cd ../frontend && npm install && npm run build

7. 常時起動を登録
     cd .. && ./ops/install-services.sh
     ※ plist 内のパス /Users/sibei.he/alice_work を
       移行先の実際のパスに書き換えてから実行すること

8. 動作確認
     http://localhost:3000/login を開いてログイン

【注意】
  - このフォルダは秘密情報を含む。移行が済んだら消すこと
  - JWT_SECRET を引き継ぐので、既存のログインはそのまま使える
    （新しく作りたい場合は openssl rand -base64 48 で作り直す）
TXT

echo "[3/3] まとめています..."
tar -czf "$OUT" -C "$WORK" household.sql env.txt README.txt

SIZE=$(du -h "$OUT" | cut -f1)
echo ""
echo "✓ $OUT ($SIZE)"
echo ""
echo "  この中に DB とパスワード・JWT 鍵が入っています。"
echo "  USB か AirDrop で運び、移行が済んだら消してください。"
echo "  クラウドストレージやチャットには上げないこと。"
