/**
 * ログイン後の3画面（ホーム / 支出 / PayPay 取り込み）の共通レイアウト。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * `(main)` は Route Group なので **URL には現れない**。
 * `app/(main)/page.tsx` は `/` のまま。
 * ログイン画面にナビを出さないためだけに、この階層を挟んでいる。
 *
 * ナビ自体は現在地の判定（usePathname）が要るのでクライアントだが、
 * この layout はサーバーのままなので、配下のページは影響を受けない。
 */
import { Suspense } from "react";

import { AppNav } from "@/features/navigation/AppNav";
import { AppNavSection } from "@/features/navigation/AppNavSection";

export default function MainLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      {/*
        バッジの件数とユーザー名を取る間もナビは出したいので Suspense で包み、
        fallback ではバッジ・名前なしのナビを出す。
      */}
      <Suspense fallback={<AppNav pendingCount={0} />}>
        <AppNavSection />
      </Suspense>

      {/* スマホのボトムタブに隠れないよう、下に余白を取る */}
      <div className="pb-16 sm:pb-0">{children}</div>
    </>
  );
}
