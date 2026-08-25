/**
 * 支出の登録・更新・削除を行う Server Action。
 *
 * ★ サーバーでだけ動く（'use server'）★
 *
 * クライアントコンポーネントから import して呼べるが、関数の中身はサーバーで実行される。
 * ブラウザに届くのは「この関数を呼ぶための ID」だけで、コードも API の URL も渡らない。
 * そのため server-only な `@/lib/api` をここから使ってよい。
 */
"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  apiDelete,
  apiPatch,
  apiPost,
  type Expense,
} from "@/lib/api";
import {
  MESSAGE_BY_TYPE,
  toFieldErrors,
  toGeneralMessage,
} from "@/lib/apiErrors";

// ============================================================
// 型
// ============================================================

/** 入力欄の名前。`<input name="...">` と 1:1 で対応させる。 */
const FIELDS = [
  "amount",
  "occurred_on",
  "category_id",
  "payment_method",
  "paid_by",
  "note",
] as const;

export type ExpenseField = (typeof FIELDS)[number];

/** 入力欄ごとのエラー文言。欄の直下に赤字で出す用。 */
export type FieldErrors = Partial<Record<ExpenseField, string>>;

/** フォームから送られてきた生の値（すべて文字列）。 */
export type SubmittedValues = Record<ExpenseField, string>;

/**
 * Server Action の戻り値 = `useActionState` の state。
 *
 * `values` は失敗したときだけ入れる。
 * React は Server Action が終わるとフォームを自動でリセットするので、
 * これを `defaultValue` に戻さないと入力し直しになってしまう。
 */
// 注: 'use server' ファイルから export できるのは async 関数だけなので、
// 初期値（INITIAL_STATE）は呼び出し側の QuickExpenseForm.tsx に置いている。
export type ExpenseFormState = {
  /** 送信結果。まだ送信していないときは null。 */
  ok: boolean | null;
  /** 入力欄ごとのエラー。 */
  fieldErrors: FieldErrors;
  /** 画面上部に出すメッセージ（業務ルール違反・想定外のエラー）。 */
  message: string | null;
  /** 失敗時に入力を復元するための値。 */
  values: SubmittedValues | null;
};

// ============================================================
// 422（Pydantic のバリデーション違反）を日本語にする
//
// detail の歩き方そのものは lib/apiErrors.ts に置いてある（カテゴリ側と共通）。
// ここにあるのは「支出のどの欄に何と出すか」の対応表だけ。
// ============================================================

const FIELD_LABEL: Record<ExpenseField, string> = {
  amount: "金額",
  occurred_on: "日付",
  category_id: "カテゴリ",
  payment_method: "支払い手段",
  paid_by: "支払者",
  note: "メモ",
};

/** `${フィールド}:${Pydantic の type}` → 日本語。具体的に言えるものはここに書く。 */
const MESSAGE_BY_FIELD_AND_TYPE: Record<string, string> = {
  "amount:missing": "金額を入力してください",
  "amount:greater_than": "0円より大きい金額を入力してください",
  "amount:int_parsing": "金額は数字で入力してください",
  "amount:int_type": "金額は数字で入力してください",
  "amount:int_from_float": "金額は1円単位で入力してください",
  "occurred_on:missing": "日付を入力してください",
  "occurred_on:date_parsing": "日付の形式が正しくありません",
  "occurred_on:date_from_datetime_parsing": "日付の形式が正しくありません",
  "occurred_on:date_type": "日付を入力してください",
  "category_id:missing": "カテゴリを選択してください",
  "category_id:int_parsing": "カテゴリを選択してください",
  "category_id:int_type": "カテゴリを選択してください",
  "payment_method:missing": "支払い手段を選んでください",
  "payment_method:literal_error": "支払い手段を選んでください",
  "paid_by:int_parsing": "支払者を選んでください",
  "note:string_too_long": "メモは500文字以内で入力してください",
};

function isExpenseField(value: unknown): value is ExpenseField {
  return (
    typeof value === "string" && (FIELDS as readonly string[]).includes(value)
  );
}

function messageFor(field: ExpenseField, type: string): string {
  return (
    MESSAGE_BY_FIELD_AND_TYPE[`${field}:${type}`] ??
    MESSAGE_BY_TYPE[type] ??
    `${FIELD_LABEL[field]}の値が正しくありません`
  );
}

// ============================================================
// Server Action
// ============================================================

/** FormData から入力値をそのまま（文字列のまま）取り出す。 */
function readValues(formData: FormData): SubmittedValues {
  const read = (name: ExpenseField) => {
    const value = formData.get(name);
    return typeof value === "string" ? value.trim() : "";
  };

  return {
    amount: read("amount"),
    occurred_on: read("occurred_on"),
    category_id: read("category_id"),
    payment_method: read("payment_method"),
    paid_by: read("paid_by"),
    note: read("note"),
  };
}

/**
 * 未入力チェック。
 *
 * 値の妥当性（金額が正か、支払い手段が既定の4つかなど）はバックエンドに任せる。
 * ここで見るのは「空のまま送ると API に渡す型すら作れない」ものだけ。
 */
function checkRequired(values: SubmittedValues): FieldErrors {
  const fieldErrors: FieldErrors = {};
  if (values.amount === "") fieldErrors.amount = "金額を入力してください";
  if (values.occurred_on === "") fieldErrors.occurred_on = "日付を入力してください";
  if (values.category_id === "")
    fieldErrors.category_id = "カテゴリを選択してください";
  return fieldErrors;
}

/** 失敗時の state を組み立てる小さなヘルパ。 */
function failure(
  values: SubmittedValues,
  fieldErrors: FieldErrors,
  message: string | null = null,
): ExpenseFormState {
  return { ok: false, fieldErrors, message, values };
}

/**
 * 支出を1件登録する。
 *
 * `useActionState` から呼ばれるので、第1引数は直前の state。
 * 今回は直前の state を使わないが、シグネチャ上は受け取る必要がある。
 */
export async function createExpense(
  _prevState: ExpenseFormState,
  formData: FormData,
): Promise<ExpenseFormState> {
  const values = readValues(formData);

  const missing = checkRequired(values);
  if (Object.keys(missing).length > 0) {
    return failure(values, missing);
  }

  try {
    await apiPost<Expense>("/api/expenses/", {
      amount: Number(values.amount),
      occurred_on: values.occurred_on,
      category_id: Number(values.category_id),
      payment_method: values.payment_method,
      paid_by: Number(values.paid_by),
      note: values.note === "" ? null : values.note,
    });
  } catch (error) {
    return toErrorState(error, values, "登録");
  }

  // ここが肝。クライアントのルーターを更新し、
  // app/page.tsx のサーバーコンポーネント（集計・一覧）を再実行させる。
  // 画面全体をリロードせずに、サーバーで組み立て直した HTML だけが差し替わる。
  refresh();

  return { ok: true, fieldErrors: {}, message: null, values: null };
}

/**
 * 支出を1件更新する（行内編集の「保存」）。
 *
 * `createExpense` と違い `useActionState` ではなく直接呼ばれるので、
 * 引数は FormData だけ。呼び出し側（ExpenseRow）は成功したら編集モードを閉じたく、
 * そのために「直前の state」ではなく「今回の結果」だけを見たいため。
 *
 * 対象の id は `<input type="hidden" name="id">` で受け取る。
 */
export async function updateExpense(
  formData: FormData,
): Promise<ExpenseFormState> {
  const values = readValues(formData);
  const id = Number(formData.get("id"));

  if (!Number.isInteger(id) || id <= 0) {
    return failure(values, {}, "更新対象が不明です。画面を再読み込みしてください。");
  }

  const missing = checkRequired(values);
  if (Object.keys(missing).length > 0) {
    return failure(values, missing);
  }

  try {
    await apiPatch<Expense>(`/api/expenses/${id}`, {
      amount: Number(values.amount),
      occurred_on: values.occurred_on,
      category_id: Number(values.category_id),
      payment_method: values.payment_method,
      paid_by: Number(values.paid_by),
      // バックエンドの update は「値が None の項目は変更しない」ので、
      // メモを空にしたいときは null ではなく空文字を送る必要がある。
      note: values.note,
    });
  } catch (error) {
    return toErrorState(error, values, "更新");
  }

  refresh();

  return { ok: true, fieldErrors: {}, message: null, values: null };
}

/**
 * 支出を1件削除する（論理削除。バックエンドは 204 を返す）。
 *
 * 入力欄が無いので FormData ではなく id をそのまま受け取る。
 * Server Action の引数は「JSON にできる値」なら何でもよい。
 */
export async function deleteExpense(id: number): Promise<ExpenseFormState> {
  const empty: SubmittedValues = {
    amount: "",
    occurred_on: "",
    category_id: "",
    payment_method: "",
    paid_by: "",
    note: "",
  };

  if (!Number.isInteger(id) || id <= 0) {
    return failure(empty, {}, "削除対象が不明です。画面を再読み込みしてください。");
  }

  try {
    await apiDelete(`/api/expenses/${id}`);
  } catch (error) {
    return failure(empty, {}, toGeneralMessage(error, "削除"));
  }

  refresh();

  return { ok: true, fieldErrors: {}, message: null, values: null };
}

/** API のエラーを、画面に出せる state に変換する。 */
function toErrorState(
  error: unknown,
  values: SubmittedValues,
  verb: string,
): ExpenseFormState {
  // 422: Pydantic のバリデーション違反 → 入力欄ごとのエラーにする
  if (error instanceof ApiError && error.status === 422) {
    const fieldErrors = toFieldErrors(error.detail, isExpenseField, messageFor);
    if (Object.keys(fieldErrors).length > 0) {
      return failure(values, fieldErrors);
    }
    // どの欄か特定できなかったときだけ、画面上部に出す
    return failure(values, {}, "入力内容を確認してください。");
  }

  // 400 / 404 / 500 / 通信断はまとめて画面上部のメッセージにする
  return failure(values, {}, toGeneralMessage(error, verb));
}
