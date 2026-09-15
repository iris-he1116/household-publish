/**
 * 支出画面。
 *
 * 支出の検索・編集に絞り、入力はホームのクイック入力に一本化する。
 * 絞り込み状態は URL に持ち、一覧はサーバーコンポーネントのまま描画する。
 */
import { Suspense } from "react";

import { RecentExpenses } from "@/features/expenses/RecentExpenses";
import { parseQueryState } from "@/features/expenses/query";

export const metadata = { title: "支出一覧｜家計清算" };

function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400">
      {label}を読み込んでいます…
    </div>
  );
}

export default async function ExpensesPage({
  searchParams,
}: PageProps<"/expenses">) {
  const raw = await searchParams;
  const state = parseQueryState(raw, currentYearMonth());

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
      <Suspense fallback={<SectionSkeleton label="支出一覧" />}>
        <RecentExpenses state={state} />
      </Suspense>
    </main>
  );
}
