/**
 * /settlement に直接来たときは、今月の清算画面へ飛ばす。
 *
 * ★ サーバーコンポーネント ★
 * リダイレクト先をサーバーで決めるので、ブラウザに JavaScript は不要。
 */
import { redirect } from "next/navigation";

export default function SettlementIndexPage() {
  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  redirect(`/settlement/${ym}`);
}
