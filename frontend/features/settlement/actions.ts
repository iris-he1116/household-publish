/**
 * 月次清算の状態を進める Server Action。
 *
 * ★ サーバーでだけ動く（'use server'）★
 *
 * 支出の登録（features/expenses/actions.ts）と違い、フォームの入力値が無い。
 * 押すのはボタン1つで、対象の年月だけが分かればよい。
 * そのため戻り値も入力欄ごとのエラーを持たず、メッセージ1本だけにしている。
 */
"use server";

import { refresh } from "next/cache";

import { ApiError, apiPost, type Settlement } from "@/lib/api";

/**
 * Server Action の戻り値 = `useActionState` の state。
 *
 * 注: 'use server' ファイルから export できるのは async 関数だけなので、
 * 初期値は呼び出し側（ConfirmButton.tsx）に置いている。
 */
export type SettlementActionState = {
  /** 送信結果。まだ押していないときは null。 */
  ok: boolean | null;
  /** 画面に出すメッセージ。 */
  message: string | null;
};

/** API のエラーを画面に出せる文言に変換する。 */
function toMessage(error: unknown, verb: string): SettlementActionState {
  if (!(error instanceof ApiError)) {
    return {
      ok: false,
      message: "サーバーに接続できませんでした。時間をおいて試してください。",
    };
  }

  // 400: 状態遷移が不正（締める前に確認しようとした等）
  if (error.status === 400) {
    const detail = typeof error.detail === "string" ? error.detail : null;
    return {
      ok: false,
      message: detail
        ? `${verb}できませんでした: ${detail}`
        : `${verb}できませんでした。画面を再読み込みしてください。`,
    };
  }

  if (error.status === 404) {
    return {
      ok: false,
      message: "対象の月が見つかりませんでした。",
    };
  }

  // 500: サーバー側の不具合。request_id を添えて調査できるようにする
  const id = error.requestId ? `（ID: ${error.requestId}）` : "";
  return {
    ok: false,
    message: `エラーが発生しました${id}`,
  };
}

/**
 * その月を「締め済み」にする。
 *
 * 本来は月末に自動で走る処理（DESIGN.md §1.4）。
 * 自動締めジョブが未実装なので、当面は手動で叩く。
 */
export async function closeMonth(
  _prevState: SettlementActionState,
  formData: FormData,
): Promise<SettlementActionState> {
  const yearMonth = String(formData.get("year_month") ?? "");
  if (!/^\d{4}-\d{2}$/.test(yearMonth)) {
    return { ok: false, message: "対象の年月が不正です。" };
  }

  try {
    await apiPost<Settlement>(`/api/settlements/${yearMonth}/close`, {});
  } catch (error) {
    return toMessage(error, "締め");
  }

  refresh();
  return { ok: true, message: `${yearMonth} を締めました。` };
}

/**
 * その月を「確認済み」にする。
 *
 * 2人とも押すと `settled`（清算済）になる。
 * 誰として確認するかは、サーバー側が Cookie の JWT で判定する
 * （Phase 3 の暫定認証。Phase 5 で JWT に差し替える）。
 */
export async function confirmMonth(
  _prevState: SettlementActionState,
  formData: FormData,
): Promise<SettlementActionState> {
  const yearMonth = String(formData.get("year_month") ?? "");
  if (!/^\d{4}-\d{2}$/.test(yearMonth)) {
    return { ok: false, message: "対象の年月が不正です。" };
  }

  try {
    const result = await apiPost<Settlement>(
      `/api/settlements/${yearMonth}/confirm`,
      {},
    );
    refresh();
    return {
      ok: true,
      message:
        result.status === "settled"
          ? "2人とも確認しました。清算済みになりました。"
          : "確認しました。相手の確認を待っています。",
    };
  } catch (error) {
    return toMessage(error, "確認");
  }
}
