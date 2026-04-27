"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@exemplo.org");
  const [password, setPassword] = useState("demo12345");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) {
        setError(data.error || "Falha no login");
        return;
      }
      const params = new URLSearchParams(window.location.search);
      const from = params.get("from") || "/atendimentos";
      router.replace(from.startsWith("/") ? from : "/atendimentos");
      router.refresh();
    } catch {
      setError("Erro de rede");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="appShell" style={{ maxWidth: 480 }}>
      <h1>Entrar</h1>
      <p className="muted">
        Credenciais demo após <code>npm run db:seed</code> (ver README).
      </p>
      <form className="card" onSubmit={onSubmit}>
        <label className="muted" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          className="input"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={busy}
        />
        <label className="muted" htmlFor="password" style={{ display: "block", marginTop: "0.75rem" }}>
          Palavra-passe
        </label>
        <input
          id="password"
          className="input"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={busy}
        />
        {error ? (
          <p role="alert" style={{ color: "#b91c1c", marginTop: "0.75rem" }}>
            {error}
          </p>
        ) : null}
        <div className="row" style={{ marginTop: "1rem" }}>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "A entrar…" : "Entrar"}
          </button>
        </div>
      </form>
    </div>
  );
}
