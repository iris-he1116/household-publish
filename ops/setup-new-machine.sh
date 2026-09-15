#!/bin/bash
# 新しい Mac に家計清算アプリを立ち上げる。
#
#   ./ops/setup-new-machine.sh /path/to/migration_YYYYMMDD_HHMMSS.tar.gz
#
# 前の PC で ./ops/export-for-migration.sh が作った tar.gz を渡すと、
# 設定の復元・DB の復元・依存の導入・常時起動の登録まで通しでやる。
#
# 何度実行しても同じ結果になる（途中で失敗したら直して再実行できる）。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PKG="${1:-}"

# 使いそうな場所を PATH に足す。
#   /opt/podman/bin        podman（公式インストーラ版）
#   /opt/homebrew/bin      brew で入れたもの
#   ~/Library/Python/*/bin pip3 install --user で入れたもの（podman-compose など）
export PATH="/opt/podman/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
for d in "$HOME/Library/Python"/*/bin; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
export PATH

die() { echo "" >&2; echo "✗ $1" >&2; exit 1; }
step() { echo ""; echo "── $1"; }

[ -n "$PKG" ] || die "移行パッケージを指定してください:
  ./ops/setup-new-machine.sh ~/Downloads/migration_20260915_175703.tar.gz"
[ -f "$PKG" ] || die "ファイルが見つかりません: $PKG"

# ---------------------------------------------------------------
step "1/7 必要なツールが揃っているか"
# ---------------------------------------------------------------
MISSING=()
command -v podman >/dev/null || MISSING+=("podman        → brew install podman")
command -v podman-compose >/dev/null || MISSING+=("podman-compose → pip3 install --user podman-compose")
command -v uv >/dev/null || MISSING+=("uv            → brew install uv")
command -v node >/dev/null || MISSING+=("node          → brew install node")
command -v npm >/dev/null || MISSING+=("npm           → node に同梱")

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "次のツールが足りません:"
  printf '  %s\n' "${MISSING[@]}"
  die "上記を入れてから、もう一度実行してください"
fi
echo "  ✓ podman / podman-compose / uv / node"

# ---------------------------------------------------------------
step "2/7 移行パッケージを展開"
# ---------------------------------------------------------------
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xzf "$PKG" -C "$WORK"
[ -f "$WORK/household.sql" ] || die "household.sql が入っていません"
[ -f "$WORK/env.txt" ] || die "env.txt が入っていません"
echo "  ✓ household.sql / env.txt"

# ---------------------------------------------------------------
step "3/7 .env を復元"
# ---------------------------------------------------------------
if [ -f "$REPO/.env" ]; then
  echo "  既に .env があります。上書きせず .env.migrated として置きます"
  cp "$WORK/env.txt" "$REPO/.env.migrated"
  echo "  → 中身を見比べて、必要なら手で反映してください"
else
  cp "$WORK/env.txt" "$REPO/.env"
  echo "  ✓ .env を作成"
fi

# ---------------------------------------------------------------
step "4/7 DB コンテナを起動"
# ---------------------------------------------------------------
if ! podman machine list --format "{{.Running}}" 2>/dev/null | grep -q true; then
  echo "  podman machine が動いていません。起動します..."
  podman machine start 2>/dev/null || die "podman machine start に失敗しました。
初回は  podman machine init  が必要です"
fi

cd "$REPO"
podman-compose up -d >/dev/null 2>&1 || die "コンテナの起動に失敗しました"

echo -n "  DB が応答するまで待っています"
for i in $(seq 1 60); do
  if podman exec household_db pg_isready -U household_user >/dev/null 2>&1; then
    echo " ✓"; break
  fi
  echo -n "."; sleep 2
  [ "$i" = "60" ] && { echo ""; die "DB が起動しませんでした"; }
done

# ---------------------------------------------------------------
step "5/7 DB を復元"
# ---------------------------------------------------------------
EXISTING=$(podman exec household_db psql -U household_user -d household -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo 0)

if [ "$EXISTING" -gt 0 ]; then
  echo "  既にテーブルが $EXISTING 個あります。復元を飛ばします"
  echo "  （作り直す場合は  podman-compose down -v  してから再実行）"
else
  podman exec -i household_db psql -U household_user -d household < "$WORK/household.sql" >/dev/null 2>&1 \
    || die "DB の復元に失敗しました"
  for t in users categories expenses paypay_import_staging; do
    n=$(podman exec household_db psql -U household_user -d household -tAc "SELECT count(*) FROM $t" 2>/dev/null || echo "?")
    printf "  %-24s %s 行\n" "$t" "$n"
  done
fi

# ---------------------------------------------------------------
step "6/7 依存を入れてビルド"
# ---------------------------------------------------------------
echo "  バックエンド..."
(cd "$REPO/backend" && uv sync >/dev/null 2>&1) || die "uv sync に失敗しました"
echo "  フロントエンド（数分かかります）..."
(cd "$REPO/frontend" && npm install >/dev/null 2>&1) || die "npm install に失敗しました"
(cd "$REPO/frontend" && npm run build >/dev/null 2>&1) || die "npm run build に失敗しました"
echo "  ✓ 完了"

# ---------------------------------------------------------------
step "7/7 常時起動を登録"
# ---------------------------------------------------------------
"$REPO/ops/install-services.sh"

echo ""
echo "─────────────────────────────────────────"
echo "✓ 移行が完了しました"
echo ""
echo "  ブラウザで開く : http://localhost:3000/login"
echo "  ログイン       : 前の PC と同じユーザー名・パスワード"
echo ""
echo "  外から使えるようにする（ひつじさんの端末用）:"
echo "    brew install --cask tailscale"
echo "    → アプリを開いてサインイン"
echo "    → ./ops/setup-funnel.sh"
echo ""
echo "  移行パッケージ（$PKG）には"
echo "  パスワードと署名鍵が入っています。確認できたら削除してください。"
echo "─────────────────────────────────────────"
