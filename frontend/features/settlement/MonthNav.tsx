/**
 * 月を前後に移動するナビゲーション。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 「前の月へ / 次の月へ」は URL が変わるだけなので、<Link> で足りる。
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
    "rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50";

  return (
    <nav className="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
      <Link href={`/settlement/${prev}`} className={linkClass}>
        ◂ {prev}
      </Link>
      <span className="text-sm font-semibold text-gray-900">
        {year}年{Number(month)}月
      </span>
      <Link href={`/settlement/${next}`} className={linkClass}>
        {next} ▸
      </Link>
    </nav>
  );
}
