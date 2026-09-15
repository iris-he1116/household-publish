/**
 * 月を前後に移動するナビゲーション。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 「前の月へ / 次の月へ」はホームの ym クエリを変えるだけなので、<Link> で足りる。
 * useState で月を持つとクライアントコンポーネントになり、
 * さらに「その月の集計を取り直す」ために useEffect + fetch が要る。
 * URL に持たせれば、遷移先のページがサーバー側で集計済みの HTML を返せる。
 */
import Link from "next/link";

/** "2026-08" を n ヶ月ずらす。 */
function shiftMonth(yearMonth: string, delta: number): string {
  const [y, m] = yearMonth.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function MonthNav({ yearMonth }: { yearMonth: string }) {
  const prev = shiftMonth(yearMonth, -1);
  const next = shiftMonth(yearMonth, 1);
  const [year, month] = yearMonth.split("-");

  const linkClass =
    "rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:border-gray-300 hover:bg-gray-50";

  return (
    <nav
      aria-label="表示月を切り替える"
      className="grid grid-cols-[auto_1fr_auto] items-center gap-3"
    >
      <Link
        href={`/?ym=${prev}`}
        className={linkClass}
        aria-label={`${prev}を表示`}
      >
        <span className="sm:hidden">◂ 前月</span>
        <span className="hidden sm:inline">◂ {prev}</span>
      </Link>
      <div className="min-w-0 text-center">
        <p className="text-xs font-semibold tracking-wide text-blue-600">
          ホーム
        </p>
        <h1 className="truncate text-xl font-bold text-gray-900 sm:text-2xl">
          {year}年{Number(month)}月の精算
        </h1>
      </div>
      <Link
        href={`/?ym=${next}`}
        className={linkClass}
        aria-label={`${next}を表示`}
      >
        <span className="sm:hidden">次月 ▸</span>
        <span className="hidden sm:inline">{next} ▸</span>
      </Link>
    </nav>
  );
}
