import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LoginForm } from "@/features/auth/LoginForm";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export default async function LoginPage() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (token) {
    try {
      await verifySessionToken(token);
      redirect("/atendimentos");
    } catch {
      // token inválido: mostrar login
    }
  }
  return <LoginForm />;
}
