/**
 * 今月の集計を表示する。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * - 関数を async にして直接 await できる（クライアントではできない）
 * - useState も useEffect も、ローディング状態の管理も要らない
 * - この JSON はブラウザの Network タブに出ない（サーバー内で完結する）
 */
import { getSummary, type SettlementSummary } from "@/lib/api";

const yen = (n: number) => `¥ ${n.toLocaleString("ja-JP")}`;

const STATUS_LABEL: Record<SettlementSummary["status"], string> = {
  in_progress: "進行中",
  closed: "締め済み・要確認",
  partially_confirmed: "片方が確認済み",
  settled: "清算済み",
};

export async function MonthSummary({ yearMonth }: { yearMonth: string }) {
  // ← ここが await できるのがサーバーコンポーネントの特権
  const s = await getSummary(yearMonth);

  const toAlice = s.transfer_from_b_to_a >= 0;
  const transferAbs = Math.abs(s.transfer_from_b_to_a);

  return (
    <section className="space-y-3">
      <div className="flex items-baseline gap-3">
        {/* 一覧のフィルタで月を移動できるので、「今月」とは言い切らない */}
        <h2 className="text-lg font-bold text-gray-900">
          {s.year_month} の集計
        </h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600">
          {STATUS_LABEL[s.status]}
        </span>
        {s.has_stale_updates && (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs text-amber-800">
            更新あり
          </span>
        )}
      </div>

      {/* KPI 3枚 */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500">共有支出の合計</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {yen(s.total_amount)}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">{s.expense_count} 件</p>
        </div>

        <div className="rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500">立替（ありす / ひつじ）</p>
          <p className="mt-1 text-lg font-bold text-gray-900">
            {yen(s.user_a_paid)}
            <span className="mx-1.5 text-gray-400">/</span>
            {yen(s.user_b_paid)}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            1人あたり {yen(s.per_person_share)}
          </p>
        </div>

        <div className="rounded-lg border border-cyan-300 bg-cyan-50 p-4">
          <p className="text-xs text-cyan-800">
            現時点の差額（{toAlice ? "ひつじ → ありす" : "ありす → ひつじ"}）
          </p>
          <p className="mt-1 text-2xl font-bold text-cyan-800">
            {yen(transferAbs)}
          </p>
          <p className="mt-0.5 text-xs text-cyan-700">月末に確定</p>
        </div>
      </div>

      {/* カテゴリ別 */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900">カテゴリ別</h3>
          {s.categories.length === 0 ? (
            <p className="mt-2 text-sm text-gray-400">
              今月の支出はまだありません
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {s.categories.map((c) => {
                const pct =
                  s.total_amount > 0
                    ? Math.round((c.amount / s.total_amount) * 100)
                    : 0;
                return (
                  <li key={c.category_id} className="text-sm">
                    <div className="flex items-baseline justify-between">
                      <span className="text-gray-700">{c.category_name}</span>
                      <span className="tabular-nums text-gray-900">
                        {yen(c.amount)}
                        <span className="ml-1.5 text-xs text-gray-400">
                          {c.count}件
                        </span>
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-gray-100">
                      <div
                        className="h-1.5 rounded-full bg-blue-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* 支払い手段別 */}
        <div className="rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900">支払い手段</h3>
          {s.payment_methods.length === 0 ? (
            <p className="mt-2 text-sm text-gray-400">—</p>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {s.payment_methods.map((m) => (
                <li
                  key={m.payment_method}
                  className="flex justify-between text-sm"
                >
                  <span className="text-gray-700">
                    {METHOD_LABEL[m.payment_method] ?? m.payment_method}
                  </span>
                  <span className="tabular-nums text-gray-900">
                    {yen(m.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

const METHOD_LABEL: Record<string, string> = {
  cash: "現金",
  credit_card: "クレジットカード",
  paypay: "PayPay",
  wechatpay: "WeChat Pay",
};
