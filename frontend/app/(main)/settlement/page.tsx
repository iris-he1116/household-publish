/**
 * 旧URL。清算をホームへ移したため、ホームへ転送する。
 *
 * ★ サーバーコンポーネント ★
 * リダイレクト先をサーバーで決めるので、ブラウザに JavaScript は不要。
 */
import { redirect } from "next/navigation";

export default function SettlementIndexPage() {
  redirect("/");
}
