#!/bin/bash
# 家計清算アプリを「Mac にログインしたら自動で立ち上がる」状態にする。
#
#   ./ops/install-services.sh          登録して起動
#   ./ops/install-services.sh uninstall 解除して停止
#
# sudo は要らない（システム全体ではなく、このユーザーのログイン時に動く設定）。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
SERVICES=(backend frontend)

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
  mkdir -p "$AGENTS" "$REPO/ops/logs"
  for s in "${SERVICES[@]}"; do
    label="com.household.$s"
    # 既に動いていれば一度外す（設定を入れ替えるため）
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    cp "$REPO/ops/launchd/$label.plist" "$AGENTS/$label.plist"
    launchctl bootstrap "gui/$(id -u)" "$AGENTS/$label.plist"
    echo "  登録: $label"
  done
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
