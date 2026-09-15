/**
 * 支出の入力フォーム（モック① の「支出を記録」に対応）。
 *
 * ★ このアプリで唯一のクライアントコンポーネント ★
 *
 * DESIGN.md の方針「'use client' は葉に付ける。根に付けない」に従い、
 * 'use client' はこのファイルだけに付ける。
 * 支出ページやその配下の RecentExpenses はサーバーのまま。
 *
 * カテゴリは自分では取りに行かず props で受け取る。
 * （API を叩くのはサーバー側の責務。ここはブラウザで動くため `@/lib/api` を実行できない）
 */
"use client";

import { useActionState, useState, type ReactNode } from "react";

import {
  createExpense,
  type ExpenseField,
  type ExpenseFormState,
  type SubmittedValues,
} from "./actions";
import { PAYERS, PAYMENT_METHODS } from "./constants";
import { NewCategoryButton } from "@/features/categories/NewCategoryButton";
// `import type` はコンパイル時に消えるので、
// server-only な @/lib/api がブラウザ側のバンドルに入ることはない。
import type { Category } from "@/lib/api";

/** `useActionState` の初期値。まだ一度も送信していない状態。 */
const INITIAL_STATE: ExpenseFormState = {
  ok: null,
  fieldErrors: {},
  message: null,
  values: null,
};

type Props = {
  /** サーバー側で getCategories() した結果。 */
  categories: Category[];
  /** サーバー側で求めた今日（"YYYY-MM-DD"）。日付欄の既定値。 */
  today: string;
};

export function QuickExpenseForm({ categories, today }: Props) {
  const [state, formAction, pending] = useActionState(
    createExpense,
    INITIAL_STATE,
  );

  // React は Server Action が終わるとフォームを自動リセットする。
  // リセット先は「今の defaultValue」なので、
  //   - 失敗したとき … 送信した値を defaultValue に戻す → 入力し直しにならない
  //   - 成功したとき … 初期値に戻る → フォームが空になる
  // という挙動をこの1行で作れる。
  const defaults: SubmittedValues = state.values ?? {
    amount: "",
    occurred_on: today,
    category_id: "",
    payment_method: "cash",
    paid_by: "1",
    note: "",
  };

  // 「+ 新規」で足したカテゴリを、そのまま選択状態にするための state。
  // null の間は上の defaults に従う。
  const [pickedCategoryId, setPickedCategoryId] = useState<string | null>(null);
  const categoryValue = pickedCategoryId ?? defaults.category_id;

  // 送信したら「+ 新規で選んだカテゴリ」の保持は解除する。
  // 成功したらフォームは空に戻したいし、失敗したときは state.values 側に
  // 送信した category_id が入っていて、そちらで復元されるため。
  const handleAction = (formData: FormData) => {
    setPickedCategoryId(null);
    formAction(formData);
  };

  const errorOf = (field: ExpenseField) => state.fieldErrors[field];

  return (
    <section className="rounded-lg border border-gray-200 p-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-lg font-bold text-gray-900">支出を記録</h2>
        <p className="text-xs text-gray-500">使ったらすぐ入力（PayPay 以外）</p>
      </div>

      {/* 業務ルール違反・想定外エラーはここにまとめて出す */}
      {state.message && (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {state.message}
        </p>
      )}
      {state.ok && (
        <p className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          記録しました
        </p>
      )}

      <form action={handleAction} className="mt-4 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="日付" error={errorOf("occurred_on")}>
            <input
              type="date"
              name="occurred_on"
              defaultValue={defaults.occurred_on}
              aria-invalid={Boolean(errorOf("occurred_on"))}
              className={inputClass(Boolean(errorOf("occurred_on")))}
            />
          </Field>

          <Field label="金額" error={errorOf("amount")}>
            <div className="relative">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-gray-400">
                ¥
              </span>
              <input
                type="number"
                name="amount"
                inputMode="numeric"
                step={1}
                placeholder="0"
                defaultValue={defaults.amount}
                aria-invalid={Boolean(errorOf("amount"))}
                className={`${inputClass(Boolean(errorOf("amount")))} pl-7 tabular-nums`}
              />
            </div>
          </Field>

          {/* カテゴリ欄だけ「+ 新規」を横に置くので group（外側を <div>）にする */}
          <Field label="カテゴリ" error={errorOf("category_id")} group>
            {/* flex-wrap にしてあるので、「+ 新規」の入力欄は次の行に回り込む */}
            <div className="flex flex-wrap items-center gap-2">
              {/*
                key を付けているのは、React が <select> の defaultValue の変更を
                DOM に反映しないため。key が変わると作り直され、
                送信に失敗したときに選んでいたカテゴリが復元される。

                key に選択肢の数も混ぜているのは「+ 新規」のため。
                追加直後は「新しい id を選びたいのに、categories にはまだ
                そのカテゴリが無い」状態で一度描画される。
                value だけを key にすると、そこで無い選択肢を指したまま固定され、
                選択肢が届いても選ばれない。
                選択肢が増えた時点でもう一度作り直させて、追加分を選ばせる。
              */}
              <select
                key={`${categoryValue}:${categories.length}`}
                name="category_id"
                defaultValue={categoryValue}
                aria-label="カテゴリ"
                aria-invalid={Boolean(errorOf("category_id"))}
                className={`${inputClass(Boolean(errorOf("category_id")))} min-w-0 flex-1`}
              >
                <option value="">選択</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <NewCategoryButton
                onCreated={(id) => setPickedCategoryId(String(id))}
              />
            </div>
          </Field>

          <Field label="メモ（任意）" error={errorOf("note")}>
            <input
              type="text"
              name="note"
              maxLength={500}
              placeholder="スーパー など"
              defaultValue={defaults.note}
              aria-invalid={Boolean(errorOf("note"))}
              className={inputClass(Boolean(errorOf("note")))}
            />
          </Field>
        </div>

        <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
          <Field label="手段" error={errorOf("payment_method")} group>
            <div className="flex flex-wrap gap-2">
              {PAYMENT_METHODS.map((m) => (
                <Choice
                  key={m.value}
                  name="payment_method"
                  value={m.value}
                  label={m.label}
                  defaultChecked={defaults.payment_method === m.value}
                />
              ))}
            </div>
          </Field>

          <Field label="支払者" error={errorOf("paid_by")} group>
            <div className="flex gap-2">
              {PAYERS.map((p) => (
                <Choice
                  key={p.value}
                  name="paid_by"
                  // PAYERS の value は users.id（数値）。ラジオの値は文字列にする。
                  value={String(p.value)}
                  label={p.label}
                  defaultChecked={defaults.paid_by === String(p.value)}
                />
              ))}
            </div>
          </Field>

          <button
            type="submit"
            disabled={pending}
            className="ml-auto rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {pending ? "記録中…" : "記録"}
          </button>
        </div>
      </form>
    </section>
  );
}

// ============================================================
// 画面の部品（このファイルの中だけで使う）
// ============================================================

const inputClass = (hasError: boolean) =>
  [
    "w-full rounded-md border px-3 py-2 text-sm text-gray-900",
    "focus:outline-none focus:ring-2 focus:ring-blue-400",
    hasError ? "border-red-400" : "border-gray-200",
  ].join(" ");

/**
 * ラベル＋入力欄＋（あれば）その欄のエラー。
 *
 * `group` はラジオボタンの集まり用。<label> の中に <label> は置けないので、
 * そのときだけ外側を <div> にする。
 */
function Field({
  label,
  error,
  children,
  group = false,
}: {
  label: string;
  error?: string;
  children: ReactNode;
  group?: boolean;
}) {
  const Wrapper = group ? "div" : "label";
  return (
    <Wrapper className="block">
      <span className="mb-1 block text-xs text-gray-500">{label}</span>
      {children}
      {/* エラーは画面上部ではなく、該当する欄の直下に出す */}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </Wrapper>
  );
}

/** ボタンに見えるラジオボタン（手段・支払者で使う）。 */
function Choice({
  name,
  value,
  label,
  defaultChecked,
}: {
  name: string;
  value: string;
  label: string;
  defaultChecked: boolean;
}) {
  return (
    <label className="cursor-pointer">
      <input
        type="radio"
        name={name}
        value={value}
        defaultChecked={defaultChecked}
        className="peer sr-only"
      />
      <span className="block rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-600 peer-checked:border-blue-500 peer-checked:bg-blue-50 peer-checked:text-blue-700 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-400">
        {label}
      </span>
    </label>
  );
}
