"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

export function AppHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const [busy, setBusy] = useState(false);

  async function logout() {
    setBusy(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <header className="appHeader card">
      <nav className="navChips" aria-label="Navegação principal">
        <span className="appHeaderBrand">Assistente — saúde da mulher</span>
        <Link
          className={`navChip${pathname === "/atendimentos" ? " navChip--active" : ""}`}
          href="/atendimentos"
        >
          Atendimentos
        </Link>
        <Link
          className={`navChip${pathname === "/atendimentos/novo" ? " navChip--active" : ""}`}
          href="/atendimentos/novo"
        >
          Novo atendimento
        </Link>
      </nav>
      <button className="btnSecondary" type="button" onClick={logout} disabled={busy}>
        Sair
      </button>
    </header>
  );
}
