#!/bin/bash
# 家計清算アプリを「Mac にログインしたら自動で立ち上がる」状態にする。
#
#   backend  … FastAPI（常駐）
#   frontend … Next.js（常駐）
#   backup       … DB のバックアップ（毎日 3:00）
#   monthly-close … 月末自動締めの判定（毎日 23:59）
#
#   ./ops/install-services.sh          登録して起動
#   ./ops/install-services.sh uninstall 解除して停止
#
# sudo は要らない（システム全体ではなく、このユーザーのログイン時に動く設定）。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
SERVICES=(backend frontend backup monthly-close)

uninstall() {
  for s in "${SERVICES[@]}"; do
    label="com.household.$s"
    if launchctl list | grep -q "$label"; then
      launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$AGENTS/$label.plist" 2>/dev/null || true
      echo "  停止: $label"
    fi
    rm -f "$AGENTS/$label.plist"
  done
  echo "✓ 自動起動を解除しました"
}

install() {
  local failed=0
  mkdir -p "$AGENTS" "$REPO/ops/logs"
  for s in "${SERVICES[@]}"; do
    label="com.household.$s"
    # 既に動いていれば一度外す（設定を入れ替えるため）。
    # bootout は非同期なので、実際に消えるまで待つ。
    # 待たずに bootstrap すると "Bootstrap failed: 5: Input/output error" になる。
    if launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; then
      launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
      for _ in $(seq 1 20); do
        launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1 || break
        sleep 0.5
      done
    fi

    # テンプレートの __REPO__ を、今いる場所に置き換えて書き出す。
    # これで別の PC に移しても、パスを手で直す必要がない。
    sed "s|__REPO__|$REPO|g" "$REPO/ops/launchd/$s.plist.template" > "$AGENTS/$label.plist"
    plutil -lint "$AGENTS/$label.plist" >/dev/null || {
      echo "  plist の生成に失敗: $label" >&2; failed=1; continue
    }
    if launchctl bootstrap "gui/$(id -u)" "$AGENTS/$label.plist" 2>/dev/null; then
      echo "  登録: $label"
    else
      echo "  ⚠️  登録に失敗: $label（既に読み込まれている可能性）" >&2
      failed=1
    fi
  done
  if [ "$failed" -ne 0 ]; then
    echo ""
    echo "一部の登録に失敗しました。もう一度実行してください。" >&2
    return 1
  fi

  echo ""
  echo "✓ 登録しました。Mac にログインすると自動で起動します。"
  echo "  状態を見る : launchctl list | grep household"
  echo "  ログを見る : tail -f $REPO/ops/logs/backend.log"
  echo "  解除する   : ./ops/install-services.sh uninstall"
}

case "${1:-install}" in
  uninstall) uninstall ;;
  install)   install ;;
  *) echo "使い方: $0 [install|uninstall]"; exit 1 ;;
esac
