#!/bin/bash
# Tailscale Funnel でアプリをインターネットに公開する。
#
#   ./ops/setup-funnel.sh          公開する
#   ./ops/setup-funnel.sh status   今の状態を見る
#   ./ops/setup-funnel.sh off      公開をやめる
#
# 前提:
#   1. Tailscale アプリをインストール済み（brew install --cask tailscale）
#   2. アプリを開いてサインイン済み
#
# 公開すると、ひつじさんは URL を開くだけで使える（アプリのインストール不要）。
# HTTPS の証明書は Tailscale が自動で用意する。
set -euo pipefail

TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
[ -x "$TS" ] || TS="$(command -v tailscale || true)"

if [ -z "$TS" ] || [ ! -x "$TS" ]; then
  echo "Tailscale が見つかりません。先にインストールしてください:" >&2
  echo "  brew install --cask tailscale" >&2
  exit 1
fi

# サインイン済みか確認
if ! "$TS" status >/dev/null 2>&1; then
  echo "Tailscale にサインインしていません。" >&2
  echo "Tailscale アプリを開いてサインインしてから、もう一度実行してください。" >&2
  exit 1
fi

case "${1:-on}" in
  status)
    echo "=== Funnel の状態 ==="
    "$TS" funnel status || echo "（公開していません）"
    echo ""
    echo "=== この端末の名前 ==="
    "$TS" status --json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('  ' + d.get('Self',{}).get('DNSName','(不明)').rstrip('.'))" 2>/dev/null || true
    ;;

  off)
    "$TS" funnel --https=443 off 2>/dev/null || true
    echo "✓ 公開をやめました"
    ;;

  on)
    echo "フロント（localhost:3000）を公開します..."
    # 443 で受けて、ローカルの 3000 に流す
    "$TS" funnel --bg --https=443 http://127.0.0.1:3000

    echo ""
    echo "=== 公開 URL ==="
    "$TS" funnel status 2>/dev/null | grep -Eo 'https://[^ ]+' | head -1 | sed 's/^/  /'
    echo ""
    echo "この URL をひつじさんに渡してください。"
    echo "アプリのインストールは不要で、ブラウザで開いてログインするだけです。"
    ;;

  *)
    echo "使い方: $0 [on|off|status]" >&2
    exit 1
    ;;
esac
