/** 支出入力フォームへ、サーバー側でカテゴリと今日の日付を渡す。 */
import { QuickExpenseForm } from "./QuickExpenseForm";
import { getCategories } from "@/lib/api";

function today(): string {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

export async function QuickExpenseSection() {
  const categories = await getCategories();
  return <QuickExpenseForm categories={categories} today={today()} />;
}
