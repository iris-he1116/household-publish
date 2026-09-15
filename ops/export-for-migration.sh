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

【移行先の Mac でやること】

■ 事前に入れておくもの

    brew install podman uv node
    pip3 install --user podman-compose
    podman machine init     # 初回のみ。10分ほどかかる
    podman machine start

■ 移行（3ステップ）

  1. リポジトリを取得
       git clone <リポジトリURL> alice_work
       cd alice_work

  2. この tar.gz を渡して実行
       ./ops/setup-new-machine.sh /path/to/migration_YYYYMMDD_HHMMSS.tar.gz

     以下を通しでやります:
       設定(.env)の復元 → DB コンテナ起動 → DB 復元
       → 依存の導入 → ビルド → 常時起動の登録

  3. ブラウザで開く
       http://localhost:3000/login
       ユーザー名とパスワードは前の PC と同じ

■ 外から使えるようにする（ひつじさんの端末用）

    brew install --cask tailscale
    → アプリを開いてサインイン
    → ./ops/setup-funnel.sh

  発行された https://～.ts.net を渡せば、
  相手はアプリのインストールなしでブラウザから使えます。

【注意】
  - このフォルダは DB とパスワードと署名鍵を含みます。
    USB か AirDrop で運び、移行が済んだら消してください。
    クラウドストレージやチャットには上げないこと。
  - JWT_SECRET を引き継ぐので、既存のログインはそのまま使えます。
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
