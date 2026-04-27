"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@exemplo.org");
  const [password, setPassword] = useState("demo12345");
  const [showPassword, setShowPassword] = useState(false);
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
        <div className="passwordField">
          <input
            id="password"
            className="input"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
          />
          <button
            type="button"
            className="passwordFieldToggle"
            onClick={() => setShowPassword((v) => !v)}
            disabled={busy}
            aria-pressed={showPassword}
            aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"}
            title={showPassword ? "Ocultar" : "Mostrar"}
          >
            {showPassword ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>
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
