/**
 * API のエラーを、画面に出せる日本語に変換する共通処理。
 *
 * ## なぜ lib/ に置くか
 *
 * 同じ変換を支出（features/expenses）とカテゴリ（features/categories）の
 * 両方の Server Action が必要とする。
 * 'use server' なファイルからは async 関数しか export できないので、
 * ヘルパはこちらの「ただのモジュール」に置く。
 *
 * ここに置くのは **どの機能でも同じ部分** だけ。
 * 「どのフィールドにどの文言を出すか」は機能ごとに違うので、
 * 対応表は各機能の actions.ts（features 配下）に置き、関数で受け取る。
 */
import { ApiError } from "@/lib/api";

/**
 * フィールド名まで特定できないとき用の、Pydantic の type だけの対応表。
 *
 * バックエンドは
 *   {"detail": [{"type": "greater_than", "loc": ["body", "amount"], ...}]}
 * という形で返す。msg は英語なのでそのまま出さず、type から日本語を引く。
 */
export const MESSAGE_BY_TYPE: Record<string, string> = {
  missing: "入力してください",
  greater_than: "0より大きい値を入力してください",
  int_parsing: "数字で入力してください",
  int_type: "数字で入力してください",
  literal_error: "選べない値です",
  string_too_short: "入力してください",
  string_too_long: "文字数が多すぎます",
};

/**
 * 422 の detail 配列を、入力欄ごとのエラーに畳み込む。
 *
 * @param isField    loc[1] が「自分が知っているフィールド名」かを判定する
 * @param messageFor フィールド名と Pydantic の type から日本語を作る
 */
export function toFieldErrors<F extends string>(
  detail: unknown,
  isField: (value: unknown) => value is F,
  messageFor: (field: F, type: string) => string,
): Partial<Record<F, string>> {
  const fieldErrors: Partial<Record<F, string>> = {};
  if (!Array.isArray(detail)) return fieldErrors;

  for (const item of detail) {
    if (typeof item !== "object" || item === null) continue;
    const { loc, type } = item as { loc?: unknown; type?: unknown };

    // loc は ["body", "amount"] の形。2番目の要素がフィールド名。
    const field = Array.isArray(loc) ? loc[1] : undefined;
    if (!isField(field)) continue;

    // 同じ欄に複数エラーが来ることがあるので、最初の1件だけ出す。
    if (fieldErrors[field]) continue;
    fieldErrors[field] = messageFor(field, typeof type === "string" ? type : "");
  }

  return fieldErrors;
}

/**
 * 422 以外のエラーを、画面上部に出す1行のメッセージにする。
 *
 * 422 は「どの入力欄が悪いか」まで言えるので呼び出し側で扱う。
 * ここで扱うのはそれ以外（業務ルール違反・想定外・通信断）。
 *
 * @param verb 「登録」「更新」「削除」など。400 の文言に埋め込む。
 */
export function toGeneralMessage(error: unknown, verb: string): string {
  if (!(error instanceof ApiError)) {
    // fetch 自体が失敗した場合など（バックエンドが落ちている等）
    return "サーバーに接続できませんでした。時間をおいて試してください。";
  }

  // 400: 業務ルール違反
  if (error.status === 400) {
    const detail = typeof error.detail === "string" ? error.detail : null;
    return detail
      ? `${verb}できませんでした: ${detail}`
      : `${verb}できませんでした。`;
  }

  // 404: 対象がすでに消えている等
  if (error.status === 404) {
    return "対象が見つかりませんでした。画面を再読み込みしてください。";
  }

  // 500 など: request_id を添えてサーバーログと突き合わせられるようにする
  return error.requestId
    ? `エラーが発生しました（ID: ${error.requestId}）`
    : "エラーが発生しました。時間をおいて試してください。";
}
