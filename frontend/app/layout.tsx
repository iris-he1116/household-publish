/**
 * 全画面共通の最小レイアウト。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * ここには html / body と全体のスタイルだけを置く。
 * ナビはログイン後の画面にしか要らないので `app/(main)/layout.tsx` に移した。
 * ログイン画面（app/login）はナビなしで表示される。
 */
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "家計清算アプリ",
  description: "ありす ／ ひつじ の共有支出を記録して月次で清算する",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full bg-white text-gray-900">{children}</body>
    </html>
  );
}
