"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function AppHeader() {
  const router = useRouter();
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
    <header
      className="card"
      style={{
        margin: "1rem auto",
        maxWidth: 1200,
        display: "flex",
        gap: "1rem",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
      }}
    >
      <div className="row" style={{ gap: "0.75rem" }}>
        <strong>Assistente — saúde da mulher</strong>
        <Link className="pill" href="/atendimentos">
          Atendimentos
        </Link>
        <Link className="pill" href="/atendimentos/novo">
          Novo atendimento
        </Link>
      </div>
      <button className="btnSecondary" type="button" onClick={logout} disabled={busy}>
        Sair
      </button>
    </header>
  );
}
