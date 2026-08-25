/**
 * ナビに未判定バッジの件数を渡すためのラッパ。
 *
 * ★ サーバーコンポーネント（'use client' なし）★
 *
 * API を叩くのはここまで。AppNav 本体はブラウザで動くので、
 * 必要な数字は props で渡し切る。
 *
 * 取得に失敗してもナビは出したいので、エラーは握って 0 件として扱う
 * （バックエンドが落ちていても画面遷移はできるべき）。
 */
import { getStagingRows } from "@/lib/api";

import { AppNav } from "./AppNav";

export async function AppNavSection() {
  let pendingCount = 0;
  try {
    const rows = await getStagingRows("pending");
    pendingCount = rows.length;
  } catch {
    // バッジが出ないだけ。ナビの表示自体は続ける。
    pendingCount = 0;
  }

  return <AppNav pendingCount={pendingCount} />;
}
