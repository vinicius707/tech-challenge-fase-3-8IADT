import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LoginForm } from "@/features/auth/LoginForm";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export const metadata: Metadata = {
  title: "Entrar",
  description:
    "Autenticação na área de auditoria e assistente clínico (demo). Usuário de teste após npm run db:seed.",
};

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
