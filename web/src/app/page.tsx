import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/session";

export default function HomePage() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (token) redirect("/atendimentos");
  redirect("/login");
}
