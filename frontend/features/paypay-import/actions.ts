/**
 * PayPay 取り込みの Server Action。
 *
 * ★ サーバーでだけ動く（'use server'）★
 *
 * CSV ファイルの中身がブラウザから Next.js サーバーに渡り、
 * そこから FastAPI に転送される。ブラウザは FastAPI を直接叩かない。
 */
"use server";

import { refresh } from "next/cache";
import { cookies } from "next/headers";

import {
  ApiError,
  SESSION_COOKIE,
  apiPost,
  type BatchActionResult,
  type CsvImportResult,
  type StagingRow,
} from "@/lib/api";

// ============================================================
// 共通
// ============================================================

export type ImportState = {
  ok: boolean | null;
  message: string | null;
  /** アップロード結果の内訳。成功時だけ入る。 */
  result: CsvImportResult | null;
};

/** API のエラーを画面に出せる文言にする。 */
function toMessage(error: unknown, verb: string): string {
  if (!(error instanceof ApiError)) {
    return "サーバーに接続できませんでした。時間をおいて試してください。";
  }
  if (error.status === 400) {
    const detail = typeof error.detail === "string" ? error.detail : null;
    return detail ? `${verb}できませんでした: ${detail}` : `${verb}できませんでした。`;
  }
  if (error.status === 404) {
    return "対象の行が見つかりませんでした。画面を再読み込みしてください。";
  }
  if (error.status === 422) {
    return "CSV の形式が想定と違います。列（取引日 / 金額 / 店舗名 / 取引ID）を確認してください。";
  }
  const id = error.requestId ? `（ID: ${error.requestId}）` : "";
  return `エラーが発生しました${id}`;
}

// ============================================================
// CSV アップロード
// ============================================================

/**
 * PayPay の履歴 CSV を取り込む。
 *
 * ここだけ multipart/form-data なので、JSON 用の `apiPost` ではなく
 * `fetch` を直接使う（Content-Type はブラウザ側の境界文字列が必要なので指定しない）。
 */
export async function importCsv(
  _prevState: ImportState,
  formData: FormData,
): Promise<ImportState> {
  const file = formData.get("file");

  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, message: "CSV ファイルを選んでください。", result: null };
  }
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return { ok: false, message: "CSV ファイル（.csv）を選んでください。", result: null };
  }

  const upstream = new FormData();
  upstream.append("file", file);

  try {
    // ファイル送信なので lib/api.ts の JSON 用ラッパは使えない。
    // Cookie の転送だけ同じことをする。
    const jar = await cookies();
    const session = jar.get(SESSION_COOKIE)?.value;

    const res = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/paypay-import/csv`,
      {
        method: "POST",
        // Content-Type は指定しない。FormData を渡すと境界文字列付きで自動設定される。
        headers: session ? { Cookie: `${SESSION_COOKIE}=${session}` } : {},
        body: upstream,
        cache: "no-store",
      },
    );

    if (!res.ok) {
      const requestId = res.headers.get("X-Request-Id");
      let detail: unknown = null;
      try {
        detail = (await res.json())?.detail ?? null;
      } catch {
        detail = null;
      }
      throw new ApiError(res.status, detail, requestId);
    }

    const result = (await res.json()) as CsvImportResult;
    refresh();
    return {
      ok: true,
      message:
        result.new_rows === 0
          ? "新しい行はありませんでした（すべて取り込み済み）。"
          : `${result.new_rows} 件を取り込みました。`,
      result,
    };
  } catch (error) {
    return { ok: false, message: toMessage(error, "取り込み"), result: null };
  }
}

// ============================================================
// 1行ごとの判定
// ============================================================

export type RowActionState = {
  ok: boolean | null;
  message: string | null;
};

export type BatchActionState = RowActionState & {
  processedCount: number;
};

function readStagingIds(formData: FormData): number[] | null {
  const rawIds = formData.getAll("staging_id");
  const ids = rawIds.map(Number);
  if (
    ids.length === 0 ||
    ids.length > 100 ||
    ids.some((id) => !Number.isInteger(id) || id <= 0) ||
    new Set(ids).size !== ids.length
  ) {
    return null;
  }
  return ids;
}

/** 選択した行をまとめて「個人」として除外する。 */
export async function excludeRows(
  _prevState: BatchActionState,
  formData: FormData,
): Promise<BatchActionState> {
  const ids = readStagingIds(formData);
  if (ids === null) {
    return { ok: false, message: "個人にする行を選んでください。", processedCount: 0 };
  }

  try {
    const result = await apiPost<BatchActionResult>("/api/paypay-import/batch-exclude", {
      staging_ids: ids,
      reason: "個人利用（一括判定）",
    });
    refresh();
    return {
      ok: true,
      message: `${result.processed_count} 件を個人の支出として除外しました。`,
      processedCount: result.processed_count,
    };
  } catch (error) {
    return { ok: false, message: toMessage(error, "一括除外"), processedCount: 0 };
  }
}

/** 選択した行を、指定された1カテゴリの共有支出としてまとめて登録する。 */
export async function adoptRows(
  _prevState: BatchActionState,
  formData: FormData,
): Promise<BatchActionState> {
  const ids = readStagingIds(formData);
  const categoryId = Number(formData.get("category_id"));
  if (ids === null) {
    return {
      ok: false,
      message: "共有にする行を選んでください。",
      processedCount: 0,
    };
  }
  if (!Number.isInteger(categoryId) || categoryId <= 0) {
    return { ok: false, message: "カテゴリを選んでください。", processedCount: 0 };
  }

  const items = ids.map((stagingId) => ({
    staging_id: stagingId,
    category_id: categoryId,
    note: null,
  }));

  try {
    const result = await apiPost<BatchActionResult>("/api/paypay-import/batch-adopt", { items });
    refresh();
    return {
      ok: true,
      message: `${result.processed_count} 件を共有支出として登録しました。`,
      processedCount: result.processed_count,
    };
  } catch (error) {
    return { ok: false, message: toMessage(error, "一括登録"), processedCount: 0 };
  }
}

/**
 * その行を「共有」として採用し、支出に昇格させる。
 *
 * カテゴリは必須。バックエンドが Expense を作り、
 * staging 側に linked_expense_id を書いて adopted にする（同一トランザクション）。
 */
export async function adoptRow(
  _prevState: RowActionState,
  formData: FormData,
): Promise<RowActionState> {
  const id = Number(formData.get("staging_id"));
  const categoryId = Number(formData.get("category_id"));
  const note = String(formData.get("note") ?? "").trim();

  if (!Number.isInteger(id) || id <= 0) {
    return { ok: false, message: "対象の行が不正です。" };
  }
  if (!Number.isInteger(categoryId) || categoryId <= 0) {
    return { ok: false, message: "カテゴリを選んでください。" };
  }

  try {
    await apiPost<StagingRow>(`/api/paypay-import/staging/${id}/adopt`, {
      category_id: categoryId,
      note: note === "" ? null : note,
    });
  } catch (error) {
    return { ok: false, message: toMessage(error, "登録") };
  }

  refresh();
  return { ok: true, message: "共有支出として登録しました。" };
}

/** その行を「個人」として除外する（集計に含めない）。 */
export async function excludeRow(
  _prevState: RowActionState,
  formData: FormData,
): Promise<RowActionState> {
  const id = Number(formData.get("staging_id"));
  const reason = String(formData.get("reason") ?? "").trim();

  if (!Number.isInteger(id) || id <= 0) {
    return { ok: false, message: "対象の行が不正です。" };
  }

  try {
    await apiPost<StagingRow>(`/api/paypay-import/staging/${id}/exclude`, {
      reason: reason === "" ? null : reason,
    });
  } catch (error) {
    return { ok: false, message: toMessage(error, "除外") };
  }

  refresh();
  return { ok: true, message: "個人の支出として除外しました。" };
}
