#!/bin/bash
# DB を pg_dump で backups/ に保存する。
#
#   ./ops/backup-db.sh
#
# 家計の記録が消えると復元できないので、毎日1回動かす想定。
# 30日より古いものは自動で消す（際限なく増やさない）。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO/backups"
KEEP_DAYS=30

# launchd は最小限の PATH しか渡さない。
# podman は公式インストーラ版が /opt/podman/bin に入る（brew 版は /opt/homebrew/bin）。
export PATH="/opt/podman/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

mkdir -p "$DEST"
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="$DEST/household_${STAMP}.sql"

# コンテナの中の pg_dump を使う（ホストに postgresql を入れなくてよい）
if ! podman exec household_db pg_dump -U household_user household > "$FILE" 2>/dev/null; then
  rm -f "$FILE"
  echo "[backup] 失敗: コンテナ household_db が動いていない可能性があります" >&2
  exit 1
fi

# 中身が空でないか確認してから完了とする
if [ ! -s "$FILE" ] || ! grep -q "CREATE TABLE" "$FILE"; then
  rm -f "$FILE"
  echo "[backup] 失敗: ダンプの中身が不正です" >&2
  exit 1
fi

SIZE=$(du -h "$FILE" | cut -f1)
echo "[backup] $(basename "$FILE") ($SIZE)"

# 古いものを片付ける
DELETED=$(find "$DEST" -name "household_*.sql" -mtime "+$KEEP_DAYS" -print -delete | wc -l | tr -d ' ')
[ "$DELETED" -gt 0 ] && echo "[backup] ${KEEP_DAYS}日より古い $DELETED 件を削除"

echo "[backup] 保管数: $(find "$DEST" -name 'household_*.sql' | wc -l | tr -d ' ') 件"
