/** 旧URL。年月を保ったままホームの精算表示へ転送する。 */
import { notFound, redirect } from "next/navigation";

export default async function LegacySettlementPage({
  params,
}: PageProps<"/settlement/[ym]">) {
  const { ym } = await params;

  if (!/^[12]\d{3}-(0[1-9]|1[0-2])$/.test(ym)) {
    notFound();
  }

  redirect(`/?ym=${ym}`);
}
