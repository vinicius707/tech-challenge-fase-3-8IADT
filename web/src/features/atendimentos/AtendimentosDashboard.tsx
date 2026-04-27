"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AtendimentoDetail, AtendimentoFiltro, AtendimentoListItem } from "@/types/atendimento";

type ListResponse = {
  page: number;
  pageSize: number;
  total: number;
  agregados: { total: number; emergencias: number; bloqueados: number };
  items: AtendimentoListItem[];
};

function fmtDate(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleString("pt-PT", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AtendimentosDashboard() {
  const router = useRouter();
  const [filtro, setFiltro] = useState<AtendimentoFiltro>("todas");
  const [soEmergencias, setSoEmergencias] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AtendimentoDetail | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    p.set("filtro", filtro);
    p.set("page", String(page));
    if (soEmergencias) p.set("so_emergencias", "1");
    return p.toString();
  }, [filtro, page, soEmergencias]);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/atendimentos?${query}`, { method: "GET" });
      if (res.status === 401) {
        router.replace("/login");
        return;
      }
      const json = (await res.json()) as ListResponse & { error?: string };
      if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
      setData(json as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }, [query, router]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDetailBusy(true);
      try {
        const res = await fetch(`/api/atendimentos/${selectedId}`);
        const json = (await res.json()) as AtendimentoDetail & { error?: string };
        if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
        if (!cancelled) setDetail(json as AtendimentoDetail);
      } catch {
        if (!cancelled) setDetail(null);
      } finally {
        if (!cancelled) setDetailBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="appShell">
      <header>
        <h1 style={{ marginTop: 0 }}>Auditoria de interações</h1>
        <p className="muted">
          Prompts, respostas e metadados persistidos após cada atendimento concluído (MVP SQLite).
        </p>
      </header>

      <div className="auditGrid">
        <section aria-label="Resumo">
          <div className="kpiRow">
            <div className="kpi kpiBlue">
              <div className="kpiValue">{data?.agregados.total ?? "—"}</div>
              <div className="kpiLabel">Total de interações</div>
            </div>
            <div className="kpi kpiRed">
              <div className="kpiValue">{data?.agregados.emergencias ?? "—"}</div>
              <div className="kpiLabel">Emergências detetadas</div>
            </div>
            <div className="kpi kpiYellow">
              <div className="kpiValue">{data?.agregados.bloqueados ?? "—"}</div>
              <div className="kpiLabel">Bloqueadas por segurança</div>
            </div>
          </div>
        </section>

        <section className="auditMain" aria-label="Lista e detalhe">
          <div className="card">
            <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
              {(
                [
                  ["todas", "Todas"],
                  ["medico", "Médico"],
                  ["fora_escopo", "Fora do escopo"],
                  ["emergencia", "Emergência"],
                  ["bloqueado", "Bloqueado"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={filtro === id ? "btn" : "btnSecondary"}
                  onClick={() => {
                    setFiltro(id);
                    setPage(1);
                  }}
                  disabled={busy}
                >
                  {label}
                </button>
              ))}
              <label className="row" style={{ gap: "0.35rem", marginLeft: "auto" }}>
                <input
                  type="checkbox"
                  checked={soEmergencias}
                  onChange={(e) => {
                    setSoEmergencias(e.target.checked);
                    setPage(1);
                  }}
                />
                <span className="muted">Somente emergências</span>
              </label>
            </div>

            {error ? (
              <p role="alert" style={{ color: "#b91c1c", marginTop: "0.75rem" }}>
                {error}
              </p>
            ) : null}

            <div className="tableWrap" style={{ marginTop: "0.75rem" }}>
              <table className="table" role="table">
                <thead>
                  <tr>
                    <th scope="col">Data/Hora</th>
                    <th scope="col">Pergunta</th>
                    <th scope="col">Categoria</th>
                    <th scope="col">Segurança</th>
                    <th scope="col">Fontes</th>
                    <th scope="col">Duração</th>
                  </tr>
                </thead>
                <tbody>
                  {busy && !data ? (
                    <tr>
                      <td colSpan={6} className="muted">
                        A carregar…
                      </td>
                    </tr>
                  ) : null}
                  {data?.items.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="muted">
                        Sem registos.
                      </td>
                    </tr>
                  ) : null}
                  {data?.items.map((row) => (
                    <tr
                      key={row.id}
                      className={selectedId === row.id ? "rowSelected" : undefined}
                    >
                      <td>
                        <button
                          type="button"
                          className="linkButton"
                          onClick={() => setSelectedId(row.id)}
                        >
                          {fmtDate(row.createdAt)}
                        </button>
                      </td>
                      <td style={{ maxWidth: 420 }}>{row.perguntaText}</td>
                      <td>
                        <span className="pill">
                          {row.categoria}{" "}
                          {row.categoriaConfidence != null
                            ? `${Math.round(row.categoriaConfidence * 100)}%`
                            : ""}
                        </span>
                      </td>
                      <td>{row.segurancaStatus === "ok" ? "✓ OK" : row.segurancaStatus}</td>
                      <td>{row.fontesCount}</td>
                      <td>{(row.duracaoMs / 1000).toFixed(1)}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="row" style={{ justifyContent: "space-between", marginTop: "0.75rem" }}>
              <button
                className="btnSecondary"
                type="button"
                disabled={busy || page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <span className="muted">
                Página {page} / {totalPages}
              </span>
              <button
                className="btnSecondary"
                type="button"
                disabled={busy || page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </button>
            </div>
          </div>

          <aside className="card detailPanel" aria-label="Detalhe da interação">
            {!selectedId ? (
              <p className="muted">Selecione uma linha para ver detalhes.</p>
            ) : detailBusy ? (
              <p className="muted">A carregar detalhe…</p>
            ) : !detail ? (
              <p className="muted">Detalhe indisponível.</p>
            ) : (
              <>
                <h2 style={{ marginTop: 0 }}>Detalhe</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  <strong>Pergunta:</strong> {detail.perguntaText}
                </p>
                <div className="row" style={{ gap: "0.5rem" }}>
                  <span className="pill">{detail.categoria}</span>
                  <span className="pill">{(detail.duracaoMs / 1000).toFixed(1)}s</span>
                  {detail.sensitiveRedacted ? <span className="pillUrgent">Redigido</span> : null}
                </div>

                <h3>Classificação (JSON)</h3>
                <pre className="codeBlock">
                  {detail.classificacaoJson || "{}"}
                </pre>

                <h3>PROMPT enviado ao LLM</h3>
                <pre className="codeBlock">{detail.promptText || "—"}</pre>

                <h3>Resposta bruta do LLM</h3>
                <pre className="codeBlock">{detail.respostaBruta || "—"}</pre>

                <h3>Trace LangGraph (MVP)</h3>
                <pre className="codeBlock">
                  {detail.langgraphTraceJson || "// vazio no stub — preencher quando o Python expuser o trace"}
                </pre>
              </>
            )}
          </aside>
        </section>
      </div>
    </div>
  );
}
