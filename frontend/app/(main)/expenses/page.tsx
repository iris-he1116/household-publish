/**
 * 支出画面。
 *
 * 支出の追加・検索・編集を一か所にまとめる。
 * 絞り込み状態は URL に持ち、一覧はサーバーコンポーネントのまま描画する。
 */
import { Suspense } from "react";

import { QuickExpenseForm } from "@/features/expenses/QuickExpenseForm";
import { RecentExpenses } from "@/features/expenses/RecentExpenses";
import { parseQueryState } from "@/features/expenses/query";
import { getCategories } from "@/lib/api";

export const metadata = { title: "支出｜家計清算" };

function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function today(): string {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

async function QuickExpenseSection() {
  const categories = await getCategories();
  return <QuickExpenseForm categories={categories} today={today()} />;
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
      <header className="mb-6">
        <p className="text-xs font-semibold tracking-wide text-blue-600">
          明細管理
        </p>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">支出</h1>
        <p className="mt-1 text-sm text-gray-500">
          共有支出の追加、絞り込み、修正をまとめて行えます
        </p>
      </header>

      <div className="space-y-8">
        <Suspense fallback={<SectionSkeleton label="入力フォーム" />}>
          <QuickExpenseSection />
        </Suspense>

        <Suspense fallback={<SectionSkeleton label="支出一覧" />}>
          <RecentExpenses state={state} />
        </Suspense>
      </div>
    </main>
  );
}
