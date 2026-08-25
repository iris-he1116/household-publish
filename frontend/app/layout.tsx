/**
 * 全画面共通のレイアウト。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * ここにナビを置くことで、3画面すべてに一度で反映される。
 * ナビ自体は現在地の判定（usePathname）が要るのでクライアントだが、
 * この layout はサーバーのままなので、配下のページは影響を受けない。
 */
import type { Metadata } from "next";
import { Suspense } from "react";

import { AppNav } from "@/features/navigation/AppNav";
import { AppNavSection } from "@/features/navigation/AppNavSection";

import "./globals.css";

export const metadata: Metadata = {
  title: "家計清算アプリ",
  description: "ありす ／ ひつじ の共有支出を記録して月次で清算する",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full bg-white text-gray-900">
        {/*
          バッジの件数を取る間もナビは出したいので Suspense で包み、
          fallback ではバッジ無しのナビを出す。
        */}
        <Suspense fallback={<AppNav pendingCount={0} />}>
          <AppNavSection />
        </Suspense>

        {/* スマホのボトムタブに隠れないよう、下に余白を取る */}
        <div className="pb-16 sm:pb-0">{children}</div>
      </body>
    </html>
  );
}
