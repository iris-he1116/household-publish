/**
 * 月次清算画面（モック② に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * URL の `[ym]` が対象の年月になる（例: /settlement/2026-08）。
 * 月を切り替えるのは <Link> による遷移で、状態を持たない。
 *
 * 注意: このバージョンの Next.js では `params` は Promise なので await が要る。
 * （node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/dynamic-routes.md）
 */
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { MonthNav } from "@/features/settlement/MonthNav";
import { SettlementDetail } from "@/features/settlement/SettlementDetail";
import { SettlementHistory } from "@/features/settlement/SettlementHistory";

function Skeleton({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-8 text-center text-sm text-gray-400">
      {label}を読み込んでいます…
    </div>
  );
}

export default async function SettlementPage({
  params,
}: {
  params: Promise<{ ym: string }>;
}) {
  const { ym } = await params;

  // 不正な年月で API を叩かないよう、ここで弾く
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(ym)) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="space-y-6">
        <MonthNav yearMonth={ym} />

        <Suspense key={ym} fallback={<Skeleton label="集計" />}>
          <SettlementDetail yearMonth={ym} />
        </Suspense>

        <Suspense fallback={<Skeleton label="過去の清算" />}>
          <SettlementHistory currentYearMonth={ym} />
        </Suspense>
      </div>
    </main>
  );
}
