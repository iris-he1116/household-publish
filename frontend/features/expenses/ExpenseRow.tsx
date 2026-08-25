/**
 * 支出一覧の1行（モック① の「編集 / 削除」と行内編集に対応）。
 *
 * ★ 一覧の中で、ここだけがクライアントコンポーネント ★
 *
 * 「今この行を編集中かどうか」はブラウザ側でしか意味を持たない一時的な状態なので、
 * URL ではなく useState で持つ。
 * （フィルタやページ番号を URL に置くのとは逆。あちらは共有・リロードしたい状態）
 *
 * 親の RecentExpenses.tsx はサーバーコンポーネントのまま。
 * 表の枠・見出し・件数はサーバーで組み立てられ、
 * ブラウザに届く JavaScript はこの行の分だけで済む。
 */
"use client";

import { useState, useTransition } from "react";

import {
  deleteExpense,
  updateExpense,
  type ExpenseField,
  type ExpenseFormState,
  type SubmittedValues,
} from "./actions";
import { METHOD_LABEL, PAYERS, PAYMENT_METHODS, USER_LABEL } from "./constants";
// `import type` はコンパイル時に消えるので、
// server-only な @/lib/api がブラウザ側のバンドルに入ることはない。
import type { Category, Expense } from "@/lib/api";

/** 表の列数。エラー行の colSpan に使う。 */
const COLUMN_COUNT = 7;

const yen = (n: number) => `¥${n.toLocaleString("ja-JP")}`;

type Props = {
  expense: Expense;
  /** 編集時のプルダウン用。表示中のカテゴリ名もここから引く。 */
  categories: Category[];
};

export function ExpenseRow({ expense, categories }: Props) {
  const [editing, setEditing] = useState(false);
  /** 直近の保存／削除の結果。成功したら null に戻す。 */
  const [result, setResult] = useState<ExpenseFormState | null>(null);
  const [pending, startTransition] = useTransition();

  // 行ごとに違う id。入力欄と <form> を結びつけるのに使う（下のコメント参照）。
  const formId = `expense-edit-${expense.id}`;

  /**
   * 保存。
   *
   * QuickExpenseForm は `useActionState` を使っているが、ここでは使わない。
   * 「成功したら編集モードを閉じる」を、直前の state ではなく
   * 今回の結果を見て決めたいため。
   */
  const save = (formData: FormData) => {
    startTransition(async () => {
      const next = await updateExpense(formData);
      if (next.ok) {
        setEditing(false);
        setResult(null);
      } else {
        setResult(next);
      }
    });
  };

  const cancel = () => {
    setEditing(false);
    setResult(null);
  };

  const remove = () => {
    const label = `${expense.occurred_on} の ${yen(expense.amount)}`;
    if (!window.confirm(`${label} を削除します。よろしいですか？`)) return;

    startTransition(async () => {
      const next = await deleteExpense(expense.id);
      // 成功すれば refresh() でこの行自体が消える。失敗したときだけ理由を出す。
      if (!next.ok) setResult(next);
    });
  };

  const failure = result && result.ok === false ? result : null;

  // 保存に失敗したら、送った値を入力欄に戻す（元の値に巻き戻さない）。
  // React は Server Action が終わるとフォームを自動リセットするため、
  // defaultValue 側をこう作り替えておく必要がある。
  const defaults: SubmittedValues = failure?.values ?? {
    amount: String(expense.amount),
    occurred_on: expense.occurred_on,
    category_id: String(expense.category_id),
    payment_method: expense.payment_method,
    paid_by: String(expense.paid_by),
    note: expense.note ?? "",
  };

  const errorOf = (field: ExpenseField) => failure?.fieldErrors[field];

  const categoryName =
    categories.find((c) => c.id === expense.category_id)?.name ?? "—";

  return (
    <>
      <tr className={editing ? "bg-blue-50/40" : "hover:bg-gray-50"}>
        {editing ? (
          <>
            {/*
              入力欄には form 属性で <form> の id を指定している。
              <tr> の子に置けるのは <td>/<th> だけで <form> を挟めないため、
              <form> 本体は右端の操作列に置き、各欄はこの属性で紐づける。
              こうすると列の位置を保ったまま、1つのフォームとして送信できる。
            */}
            <Cell>
              <input
                type="date"
                name="occurred_on"
                form={formId}
                defaultValue={defaults.occurred_on}
                aria-invalid={Boolean(errorOf("occurred_on"))}
                className={inputClass(Boolean(errorOf("occurred_on")))}
              />
              <FieldError message={errorOf("occurred_on")} />
            </Cell>

            <Cell>
              {/*
                key を付けているのは、React が <select> の defaultValue の変更を
                DOM に反映しないため。key が変わると作り直され、
                失敗時に選んでいた値が正しく復元される。
              */}
              <select
                key={defaults.category_id}
                name="category_id"
                form={formId}
                defaultValue={defaults.category_id}
                aria-label="カテゴリ"
                aria-invalid={Boolean(errorOf("category_id"))}
                className={inputClass(Boolean(errorOf("category_id")))}
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <FieldError message={errorOf("category_id")} />
            </Cell>

            <Cell>
              <input
                type="text"
                name="note"
                form={formId}
                maxLength={500}
                placeholder="メモ"
                defaultValue={defaults.note}
                aria-label="メモ"
                aria-invalid={Boolean(errorOf("note"))}
                className={inputClass(Boolean(errorOf("note")))}
              />
              <FieldError message={errorOf("note")} />
            </Cell>

            <Cell>
              <select
                key={defaults.payment_method}
                name="payment_method"
                form={formId}
                defaultValue={defaults.payment_method}
                aria-label="支払い手段"
                aria-invalid={Boolean(errorOf("payment_method"))}
                className={inputClass(Boolean(errorOf("payment_method")))}
              >
                {PAYMENT_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
              <FieldError message={errorOf("payment_method")} />
            </Cell>

            <Cell>
              <input
                type="number"
                name="amount"
                form={formId}
                inputMode="numeric"
                step={1}
                defaultValue={defaults.amount}
                aria-label="金額"
                aria-invalid={Boolean(errorOf("amount"))}
                className={`${inputClass(Boolean(errorOf("amount")))} text-right tabular-nums`}
              />
              <FieldError message={errorOf("amount")} />
            </Cell>

            <Cell>
              <select
                key={defaults.paid_by}
                name="paid_by"
                form={formId}
                defaultValue={defaults.paid_by}
                aria-label="支払者"
                aria-invalid={Boolean(errorOf("paid_by"))}
                className={inputClass(Boolean(errorOf("paid_by")))}
              >
                {PAYERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
              <FieldError message={errorOf("paid_by")} />
            </Cell>

            <Cell>
              <form id={formId} action={save} className="flex gap-2">
                <input type="hidden" name="id" value={expense.id} />
                <button
                  type="submit"
                  disabled={pending}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                >
                  {pending ? "保存中…" : "保存"}
                </button>
                <button
                  type="button"
                  onClick={cancel}
                  disabled={pending}
                  className="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed"
                >
                  取消
                </button>
              </form>
            </Cell>
          </>
        ) : (
          <>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums text-gray-600">
              {expense.occurred_on.slice(5).replace("-", "/")}
            </td>
            <td className="whitespace-nowrap px-3 py-2 text-gray-900">
              {categoryName}
            </td>
            {/* メモは空文字にもなり得る（編集で消したとき）ので || で拾う */}
            <td className="px-3 py-2 text-gray-600">{expense.note || "—"}</td>
            <td className="whitespace-nowrap px-3 py-2 text-gray-600">
              {METHOD_LABEL[expense.payment_method] ?? expense.payment_method}
            </td>
            <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums font-medium text-gray-900">
              {yen(expense.amount)}
            </td>
            <td className="whitespace-nowrap px-3 py-2 text-gray-600">
              {USER_LABEL[expense.paid_by] ?? `user${expense.paid_by}`}
            </td>
            <td className="whitespace-nowrap px-3 py-2">
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  disabled={pending}
                  className="text-xs text-blue-600 hover:underline disabled:text-gray-300 disabled:no-underline"
                >
                  編集
                </button>
                <button
                  type="button"
                  onClick={remove}
                  disabled={pending}
                  className="text-xs text-red-600 hover:underline disabled:text-gray-300 disabled:no-underline"
                >
                  {pending ? "処理中…" : "削除"}
                </button>
              </div>
            </td>
          </>
        )}
      </tr>

      {/* 欄を特定できなかったエラー（400・500・通信断など）は行の下に出す */}
      {failure?.message && (
        <tr>
          <td colSpan={COLUMN_COUNT} className="px-3 pb-2">
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs text-red-700">
              {failure.message}
            </p>
          </td>
        </tr>
      )}
    </>
  );
}

// ============================================================
// 画面の部品（このファイルの中だけで使う）
// ============================================================

const inputClass = (hasError: boolean) =>
  [
    "w-full rounded-md border px-2 py-1 text-sm text-gray-900",
    "focus:outline-none focus:ring-2 focus:ring-blue-400",
    hasError ? "border-red-400" : "border-gray-200",
  ].join(" ");

/** 編集モードのセル。入力欄とその下のエラーを縦に並べる。 */
function Cell({ children }: { children: React.ReactNode }) {
  return <td className="px-3 py-2 align-top">{children}</td>;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <span className="mt-1 block text-xs text-red-600">{message}</span>;
}
