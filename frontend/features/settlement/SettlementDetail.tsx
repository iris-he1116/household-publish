/**
 * 月次清算の詳細（モック② の PC 版に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 集計の取得も表示も、すべてサーバーで行う。
 * ボタンだけを SettlementActionButton（クライアント）に切り出している。
 */
import { getSummary, type SettlementSummary } from "@/lib/api";

import { closeMonth, confirmMonth } from "./actions";
import { SettlementActionButton } from "./SettlementActionButton";

const yen = (n: number) => `¥ ${n.toLocaleString("ja-JP")}`;

const STATUS: Record<
  SettlementSummary["status"],
  { label: string; className: string; hint: string }
> = {
  in_progress: {
    label: "進行中",
    className: "bg-gray-100 text-gray-700",
    hint: "この月はまだ締めていません。月末に締めると確認に進めます。",
  },
  closed: {
    label: "締め済み・要確認",
    className: "bg-amber-100 text-amber-800",
    hint: "2人が内容を確認すると清算済みになります。",
  },
  partially_confirmed: {
    label: "片方が確認済み",
    className: "bg-blue-100 text-blue-800",
    hint: "もう1人の確認を待っています。",
  },
  settled: {
    label: "清算済み",
    className: "bg-green-100 text-green-800",
    hint: "この月の清算は完了しています。",
  },
};

const METHOD_LABEL: Record<string, string> = {
  cash: "現金",
  credit_card: "クレジットカード",
  paypay: "PayPay",
  wechatpay: "WeChat Pay",
};

/** ISO 文字列を "MM-DD HH:mm" にする。 */
function shortTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(
    d.getMinutes(),
  )}`;
}

function ConfirmCard({
  name,
  confirmedAt,
}: {
  name: string;
  confirmedAt: string | null;
}) {
  const done = Boolean(confirmedAt);
  return (
    <div
      className={`rounded-lg border p-4 ${
        done ? "border-green-300 bg-green-50" : "border-gray-300 bg-gray-50"
      }`}
    >
      <p className="text-sm font-semibold text-gray-900">{name}</p>
      <p
        className={`mt-1 text-xs ${
          done ? "text-green-800" : "text-gray-500"
        }`}
      >
        {done ? `✓ 確認済み（${shortTime(confirmedAt)}）` : "未確認"}
      </p>
    </div>
  );
}

export async function SettlementDetail({ yearMonth }: { yearMonth: string }) {
  const s = await getSummary(yearMonth);
  const meta = STATUS[s.status];

  const toAlice = s.transfer_from_b_to_a >= 0;
  const transferAbs = Math.abs(s.transfer_from_b_to_a);
  const [year, month] = yearMonth.split("-");

  return (
    <div className="space-y-6">
      {/* 見出しと状態 */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">
          {year}年{Number(month)}月の清算
        </h1>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${meta.className}`}
        >
          {meta.label}
        </span>
        {s.has_stale_updates && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
            更新あり
          </span>
        )}
        <span className="text-xs text-gray-500">{s.expense_count} 件</span>
      </div>

      {/* 送金額。この画面で一番知りたい情報なので最初に大きく出す */}
      <section className="rounded-lg border-2 border-cyan-300 bg-cyan-50 p-6 text-center">
        {s.total_amount === 0 ? (
          <p className="text-sm text-cyan-800">この月の支出はまだありません</p>
        ) : transferAbs === 0 ? (
          <p className="text-lg font-bold text-cyan-800">
            ちょうど半分ずつ。送金は不要です
          </p>
        ) : (
          <>
            <p className="text-sm text-cyan-800">
              {toAlice ? "ひつじ → ありす" : "ありす → ひつじ"}
            </p>
            <p className="mt-2 text-4xl font-bold text-cyan-800">
              {yen(transferAbs)}
            </p>
            <p className="mt-2 text-xs text-cyan-700">を送金してください</p>
          </>
        )}
      </section>

      {/* 集計 */}
      <section className="rounded-lg border border-gray-200">
        <dl className="divide-y divide-gray-100">
          {[
            ["共有支出の合計", yen(s.total_amount), true],
            ["1人あたりの負担", yen(s.per_person_share), true],
            ["ありすの立替", yen(s.user_a_paid), false],
            ["ひつじの立替", yen(s.user_b_paid), false],
          ].map(([label, value, strong]) => (
            <div
              key={String(label)}
              className="flex items-baseline justify-between px-4 py-3"
            >
              <dt className="text-sm text-gray-600">{label}</dt>
              <dd
                className={`tabular-nums ${
                  strong
                    ? "text-base font-bold text-gray-900"
                    : "text-sm text-gray-900"
                }`}
              >
                {value}
              </dd>
            </div>
          ))}
        </dl>
        <p className="border-t border-gray-100 px-4 py-2 text-xs text-gray-500">
          端数の1円は、その月に立替が少なかった側が負担します（DESIGN.md §4）
        </p>
      </section>

      {/* 双方の確認 */}
      <section className="rounded-lg border border-gray-200 p-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-gray-900">双方の確認</h2>
          <p className="text-xs text-gray-500">{meta.hint}</p>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <ConfirmCard name="ありす" confirmedAt={s.confirmed_at_user_a} />
          <ConfirmCard name="ひつじ" confirmedAt={s.confirmed_at_user_b} />
        </div>

        <div className="mt-4">
          {s.status === "in_progress" ? (
            <SettlementActionButton
              yearMonth={yearMonth}
              action={closeMonth}
              label="この月を締める"
              pendingLabel="締めています…"
              disabledReason={
                s.total_amount === 0
                  ? "支出が1件も無いため、まだ締められません"
                  : undefined
              }
            />
          ) : s.status === "settled" ? (
            <p className="text-sm text-green-800">
              ✓ この月の清算は完了しています
            </p>
          ) : (
            <SettlementActionButton
              yearMonth={yearMonth}
              action={confirmMonth}
              label="内容を確認して清算する"
              pendingLabel="確認しています…"
            />
          )}
        </div>
      </section>

      {/* 内訳 */}
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-900">
            カテゴリ別内訳
          </h2>
          {s.categories.length === 0 ? (
            <p className="mt-2 text-sm text-gray-400">—</p>
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
        </section>

        <section className="rounded-lg border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-900">支払い手段</h2>
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
        </section>
      </div>
    </div>
  );
}
