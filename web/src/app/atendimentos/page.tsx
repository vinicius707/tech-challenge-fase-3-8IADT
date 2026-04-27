import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AtendimentosDashboard } from "@/features/atendimentos/AtendimentosDashboard";
import { getDb, runMigrations } from "@/db/client";
import { queryAtendimentosList } from "@/lib/atendimentos-list";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export default async function AtendimentosPage() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  let userId: string;
  try {
    const session = await verifySessionToken(token);
    userId = session.sub;
  } catch {
    redirect("/login");
  }

  runMigrations();
  const db = getDb();
  const initialData = queryAtendimentosList(db, userId, {
    filtro: "todas",
    page: 1,
    pageSize: 10,
    soEmergencias: false,
  });

  return <AtendimentosDashboard initialData={initialData} />;
}
