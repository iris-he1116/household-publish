/**
 * ホーム画面（モック① の PC 版に対応）。
 *
 * ★ サーバーコンポーネント ★
 * このファイルに 'use client' は無い。付けると配下の MonthSummary /
 * RecentExpenses までクライアントになってしまうので、絶対に付けない。
 * ブラウザに届く JavaScript は入力フォーム・フィルタ・一覧の行（葉）の分だけ。
 *
 * DESIGN.md §1.7 の3画面構成のうち、①ホームを実装したもの。
 *
 * ## 絞り込みは URL のクエリで受け取る
 *
 *   /?ym=2026-08&category=1&method=cash&payer=2&page=2
 *
 * `searchParams` はここ（サーバー）で読み、絞り込んだ結果を組み立てて返す。
 * そのおかげで一覧はサーバーコンポーネントのままでいられる。
 * 詳しい理由は features/expenses/query.ts の冒頭コメントに書いた。
 */
import { Suspense } from "react";

import { QuickExpenseForm } from "@/features/expenses/QuickExpenseForm";
import { RecentExpenses } from "@/features/expenses/RecentExpenses";
import { parseQueryState } from "@/features/expenses/query";
import { MonthSummary } from "@/features/settlement/MonthSummary";
import { getCategories } from "@/lib/api";

/** 今日の日付から "YYYY-MM" を作る。 */
function currentYearMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** 今日の日付を "YYYY-MM-DD" で返す。 */
function today(): string {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

/**
 * 入力フォームにカテゴリを渡すためのラッパ（サーバーコンポーネント）。
 *
 * API を叩くのはここまで。フォーム本体はブラウザで動くので、
 * 必要なデータは props で渡し切る。
 * 既定の日付もここで決める（サーバーとブラウザで new Date() の結果がずれて
 * hydration が壊れるのを防ぐため）。
 */
async function QuickExpenseSection() {
  const categories = await getCategories();
  return <QuickExpenseForm categories={categories} today={today()} />;
}

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-8 text-center text-sm text-gray-400">
      {label}を読み込んでいます…
    </div>
  );
}

export default async function HomePage({ searchParams }: PageProps<"/">) {
  // Next.js 16 では searchParams は Promise。await して初めて中身が読める。
  // 型は Next.js が生成する PageProps<"/"> をそのまま使う（import 不要のグローバル）。
  const raw = await searchParams;

  // 壊れた値を弾いてから使う。詳細は query.ts の parseQueryState を参照。
  const state = parseQueryState(raw, currentYearMonth());

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">家計清算</h1>
        <p className="mt-1 text-sm text-gray-500">
          ありす ／ ひつじ の共有支出
        </p>
      </header>

      {/* 唯一の「新規入力」部分。 */}
      <div className="mb-8">
        <Suspense fallback={<SectionSkeleton label="入力フォーム" />}>
          <QuickExpenseSection />
        </Suspense>
      </div>

      <div className="space-y-8">
        {/*
          Suspense で囲むと、この中の await を待たずに
          周囲の HTML を先に送れる（ストリーミング）。
        */}
        {/*
          集計も一覧と同じ月を見る。
          カテゴリ・手段・支払者の絞り込みは一覧だけに掛かる
          （集計はその月ぜんぶが対象なので、絞り込むと意味が変わってしまう）。
        */}
        <Suspense fallback={<SectionSkeleton label="今月の集計" />}>
          <MonthSummary yearMonth={state.yearMonth} />
        </Suspense>

        <Suspense fallback={<SectionSkeleton label="支出一覧" />}>
          <RecentExpenses state={state} />
        </Suspense>
      </div>
    </main>
  );
}
