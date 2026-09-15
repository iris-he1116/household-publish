/**
 * ホーム画面。
 *
 * ホームは「今月、誰が誰にいくら送るか」を確認する場所に絞る。
 * 支出の追加・検索・編集は /expenses に分け、月次集計との重複をなくす。
 */
import { Suspense } from "react";

import { MonthNav } from "@/features/settlement/MonthNav";
import { SettlementDetail } from "@/features/settlement/SettlementDetail";
import { SettlementHistory } from "@/features/settlement/SettlementHistory";

export const metadata = { title: "ホーム｜家計清算" };

function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function validYearMonth(value: string | string[] | undefined): string {
  const text = Array.isArray(value) ? value[0] : value;
  return text && /^[12]\d{3}-(0[1-9]|1[0-2])$/.test(text)
    ? text
    : currentYearMonth();
}

function Skeleton({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400">
      {label}を読み込んでいます…
    </div>
  );
}

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const raw = await searchParams;
  const yearMonth = validYearMonth(raw.ym);

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="space-y-6">
        <MonthNav yearMonth={yearMonth} />

        <Suspense key={yearMonth} fallback={<Skeleton label="精算状況" />}>
          <SettlementDetail yearMonth={yearMonth} />
        </Suspense>

        <Suspense fallback={<Skeleton label="過去の清算" />}>
          <SettlementHistory currentYearMonth={yearMonth} />
        </Suspense>
      </div>
    </main>
  );
}
