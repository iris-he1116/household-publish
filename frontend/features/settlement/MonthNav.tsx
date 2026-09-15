/**
 * 月を前後に移動するナビゲーション。
 *
 * 前後ボタンに加えて、数か月離れた月へ直接移動できる月選択を置く。
 * 選んだ月は URL の ym に反映し、遷移先をサーバー側で集計する。
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

/** "2026-08" を n ヶ月ずらす。 */
function shiftMonth(yearMonth: string, delta: number): string {
  const [y, m] = yearMonth.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function MonthNav({ yearMonth }: { yearMonth: string }) {
  const router = useRouter();
  const prev = shiftMonth(yearMonth, -1);
  const next = shiftMonth(yearMonth, 1);
  const [year, month] = yearMonth.split("-");

  const linkClass =
    "flex size-10 shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white text-sm font-medium text-gray-700 transition hover:border-gray-300 hover:bg-gray-50 sm:h-auto sm:w-auto sm:px-3 sm:py-1.5";

  return (
    <nav
      aria-label="表示月を切り替える"
      className="grid grid-cols-[2.5rem_minmax(0,1fr)_2.5rem] items-center gap-2 border-b border-gray-100 px-3 py-3 sm:grid-cols-[auto_1fr_auto] sm:gap-3 sm:px-5 sm:py-4"
    >
      <Link
        href={`/?ym=${prev}`}
        className={linkClass}
        aria-label={`${prev}を表示`}
      >
        <span aria-hidden="true" className="sm:hidden">◂</span>
        <span className="hidden sm:inline">◂ {prev}</span>
      </Link>
      <div className="min-w-0 text-center">
        <h1 className="whitespace-nowrap text-[15px] font-bold text-gray-900 sm:text-xl">
          {year}年{Number(month)}月の精算
        </h1>
        <label className="mt-1 inline-flex items-center gap-1.5 text-xs text-gray-500">
          <span>月を選択</span>
          <input
            type="month"
            value={yearMonth}
            onChange={(event) => {
              if (event.target.value) router.push(`/?ym=${event.target.value}`);
            }}
            className="min-w-0 rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs text-gray-700"
            aria-label="表示する月を選択"
          />
        </label>
      </div>
      <Link
        href={`/?ym=${next}`}
        className={linkClass}
        aria-label={`${next}を表示`}
      >
        <span aria-hidden="true" className="sm:hidden">▸</span>
        <span className="hidden sm:inline">{next} ▸</span>
      </Link>
    </nav>
  );
}
