/**
 * 月次清算の詳細（モック② の PC 版に対応）。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * 集計の取得も表示も、すべてサーバーで行う。
 * ボタンだけを SettlementActionButton（クライアント）に切り出している。
 */
import Link from "next/link";

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
    <div className={done ? "rounded-lg bg-green-50 px-4 py-3" : "rounded-lg bg-gray-50 px-4 py-3"}>
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

  return (
    <div className="space-y-6">
      {/* 精算に必要な情報と操作を、読む順番どおり1つのブロックにまとめる */}
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-5 py-4">
          <h2 className="mr-1 text-base font-bold text-gray-900">今月の精算</h2>
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
          <span className="text-xs text-gray-500">
            共有支出 {s.expense_count}件
          </span>
          <Link
            href={`/expenses?ym=${yearMonth}`}
            className="ml-auto rounded-lg px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            明細を見る
          </Link>
        </div>

        {/* この画面で最も知りたい送金額を大きく出す */}
        <div className="bg-gradient-to-br from-cyan-50 to-blue-50 p-6 text-center sm:p-8">
          <p className="text-xs font-semibold tracking-wide text-cyan-700">
            現時点の精算額
          </p>
          {s.total_amount === 0 ? (
            <p className="mt-3 text-lg font-bold text-cyan-900">
              この月の共有支出はまだありません
            </p>
          ) : transferAbs === 0 ? (
            <p className="mt-3 text-xl font-bold text-cyan-900">
              ちょうど半分ずつ。送金は不要です
            </p>
          ) : (
            <>
              <p className="mt-2 text-sm text-cyan-800">
                {toAlice ? "ひつじ → ありす" : "ありす → ひつじ"}
              </p>
              <p className="mt-2 text-4xl font-bold tracking-tight text-cyan-900 sm:text-5xl">
                {yen(transferAbs)}
              </p>
              <p className="mt-2 text-xs text-cyan-700">を送金してください</p>
            </>
          )}
        </div>

        {/* 枠を増やさず、区切り線だけで3つの数字を比較する */}
        <dl className="grid divide-y divide-gray-100 border-t border-gray-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <SummaryItem
            label="共有支出の合計"
            value={yen(s.total_amount)}
            sub={`${s.expense_count}件・1人あたり ${yen(s.per_person_share)}`}
          />
          <SummaryItem
            label="ありすの立替"
            value={yen(s.user_a_paid)}
            accent="blue"
          />
          <SummaryItem
            label="ひつじの立替"
            value={yen(s.user_b_paid)}
            accent="violet"
          />
        </dl>

        {/* 双方の確認も同じ精算ブロック内の最終ステップとして置く */}
        <div className="border-t border-gray-100 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-900">双方の確認</h3>
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
        </div>
      </section>

      {/* 内訳 */}
      <div className="grid gap-4 sm:grid-cols-2">
        <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
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

        <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
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

function SummaryItem({
  label,
  value,
  sub,
  accent = "gray",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "gray" | "blue" | "violet";
}) {
  const labelStyles = {
    gray: "text-gray-500",
    blue: "text-blue-700",
    violet: "text-violet-700",
  };

  return (
    <div className="px-5 py-4">
      <dt className={`text-xs font-medium ${labelStyles[accent]}`}>{label}</dt>
      <dd className="mt-2 text-2xl font-bold tabular-nums text-gray-900">
        {value}
      </dd>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}
