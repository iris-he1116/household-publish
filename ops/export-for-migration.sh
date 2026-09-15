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
#   repo.bundle    … リポジトリ全体（全履歴つき）
#   README.txt     … 移行先での手順
#
# repo.bundle を入れているのは、リポジトリが会社の GitHub organization に
# あるため。個人の PC からは clone できない可能性がある。
# bundle があれば GitHub に繋がらなくても復元できる。
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

echo "[1/4] DB を書き出しています..."
if ! podman exec household_db pg_dump -U household_user household > "$WORK/household.sql" 2>/dev/null; then
  echo "失敗: コンテナ household_db が動いていません" >&2
  exit 1
fi
grep -q "CREATE TABLE" "$WORK/household.sql" || { echo "失敗: ダンプが不正です" >&2; exit 1; }

echo "[2/4] 設定を書き出しています..."
cp "$REPO/.env" "$WORK/env.txt"

echo "[3/4] リポジトリを書き出しています..."
# git bundle = 全履歴を含む1ファイル。
# 移行先から会社の GitHub に繋げなくても、ここから clone できる。
git -C "$REPO" bundle create "$WORK/repo.bundle" --all 2>/dev/null \
  || { echo "失敗: git bundle を作れませんでした" >&2; exit 1; }
git -C "$REPO" bundle verify "$WORK/repo.bundle" >/dev/null 2>&1 \
  || { echo "失敗: bundle が壊れています" >&2; exit 1; }

cat > "$WORK/README.txt" <<'TXT'
家計清算アプリ - 移行手順

【中身】
  household.sql  DB 全体のダンプ
  env.txt        .env の中身（パスワードと JWT 鍵を含む）
  repo.bundle    リポジトリ全体（全履歴つき）

  ※ repo.bundle があるので、GitHub に繋がらなくても復元できます。
     リポジトリが会社の organization にあるため、個人 PC からは
     clone できない可能性があるので同梱しています。

【移行先の Mac でやること】

■ 事前に入れておくもの

    brew install podman uv node
    pip3 install --user podman-compose
    podman machine init     # 初回のみ。10分ほどかかる
    podman machine start

■ 移行（3ステップ）

  1. この tar.gz を展開して、リポジトリを復元

       tar -xzf migration_YYYYMMDD_HHMMSS.tar.gz
       git clone repo.bundle alice_work
       cd alice_work
       git checkout main

  2. セットアップを実行（展開したフォルダのパスを渡す）

       ./ops/setup-new-machine.sh ../migration_YYYYMMDD_HHMMSS.tar.gz

     以下を通しでやります:
       設定(.env)の復元 → DB コンテナ起動 → DB 復元
       → 依存の導入 → ビルド → 常時起動の登録

  3. ブラウザで開く

       http://localhost:3000/login
       ユーザー名とパスワードは前の PC と同じ

■ 自分の GitHub に置き直す（任意だが推奨）

  会社の organization から切り離しておくと、
  異動や退職でアクセスを失っても困りません。

    1. github.com で新しい private リポジトリを作る
    2. git remote set-url origin https://github.com/<自分>/<名前>.git
    3. git push -u origin main

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

echo "[4/4] まとめています..."
tar -czf "$OUT" -C "$WORK" household.sql env.txt repo.bundle README.txt

SIZE=$(du -h "$OUT" | cut -f1)
echo ""
echo "✓ $OUT ($SIZE)"
echo ""
echo "  この中に DB とパスワード・JWT 鍵が入っています。"
echo "  USB か AirDrop で運び、移行が済んだら消してください。"
echo "  クラウドストレージやチャットには上げないこと。"
