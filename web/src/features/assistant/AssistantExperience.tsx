"use client";

import { useCallback, useEffect, useMemo, useRef, useState, startTransition } from "react";
import type {
  ChatMessage,
  ChatStreamRequest,
  ClinicalFlowId,
  ExplainBlock,
  PatientContextPayload,
  TraceSummary,
  UrgenciaLevel,
} from "@/types/assistant";
import { AssistantExplainPanel } from "./AssistantExplainPanel";
import { AssistantLogPanel } from "./AssistantLogPanel";
import { AssistantMessageBubble } from "./AssistantMessageBubble";
import { ClinicalDisclaimerBanner } from "./ClinicalDisclaimerBanner";
import { flowChipClass } from "@/lib/flow-ui";
import { consumeSse } from "./chatStream";

function newId(): string {
  return crypto.randomUUID();
}

const FLOW_LABELS: Record<ClinicalFlowId, string> = {
  triagemGinecologica: "Triagem ginecológica",
  violenciaDomestica: "Violência doméstica (sensível)",
  obstetrico: "Obstétrico",
  prevencao: "Prevenção / rastreamento",
};

export type AssistantExperienceProps = {
  persist?: boolean;
  embedded?: boolean;
};

export function AssistantExperience({
  persist = false,
  embedded = false,
}: AssistantExperienceProps) {
  const [flowId, setFlowId] = useState<ClinicalFlowId>("triagemGinecologica");
  const [professionalVerified, setProfessionalVerified] = useState(false);
  const [patientContextText, setPatientContextText] = useState(
    '{\n  "resumo": "Paciente fictícia, 34 anos, sem PII real."\n}',
  );
  const [input, setInput] = useState(
    "Relato fictício: dor pélvica leve há 2 dias, sem febre.",
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [explain, setExplain] = useState<ExplainBlock | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const abortRef = useRef<AbortController | null>(null);
  const urgenciaRef = useRef<UrgenciaLevel | null>(null);
  const startedAtRef = useRef<number>(0);
  const latestExplainRef = useRef<ExplainBlock | null>(null);
  const latestTraceRef = useRef<TraceSummary | null>(null);

  const assistantDraftRef = useRef("");
  const streamingAssistantIdRef = useRef("");
  const tokenFlushRafRef = useRef<number | null>(null);

  const logBufferRef = useRef<string[]>([]);
  const logFlushRafRef = useRef<number | null>(null);

  const needsProfessionalGate = flowId === "violenciaDomestica";
  const canSend = useMemo(() => {
    if (busy) return false;
    if (!input.trim()) return false;
    if (needsProfessionalGate && !professionalVerified) return false;
    return true;
  }, [busy, input, needsProfessionalGate, professionalVerified]);

  const flushLogsNow = useCallback(() => {
    if (logFlushRafRef.current != null) {
      cancelAnimationFrame(logFlushRafRef.current);
      logFlushRafRef.current = null;
    }
    const batch = logBufferRef.current;
    logBufferRef.current = [];
    if (batch.length === 0) return;
    startTransition(() => {
      setLogs((prev) =>
        [...batch.map((l) => `${new Date().toISOString()} ${l}`), ...prev].slice(0, 200),
      );
    });
  }, []);

  const appendLog = useCallback(
    (line: string) => {
      logBufferRef.current.push(line);
      if (logFlushRafRef.current != null) return;
      logFlushRafRef.current = requestAnimationFrame(() => {
        logFlushRafRef.current = null;
        const batch = logBufferRef.current;
        logBufferRef.current = [];
        if (batch.length === 0) return;
        startTransition(() => {
          setLogs((prev) =>
            [...batch.map((l) => `${new Date().toISOString()} ${l}`), ...prev].slice(0, 200),
          );
        });
      });
    },
    [],
  );

  const cancelTokenFlush = useCallback(() => {
    if (tokenFlushRafRef.current != null) {
      cancelAnimationFrame(tokenFlushRafRef.current);
      tokenFlushRafRef.current = null;
    }
  }, []);

  const scheduleAssistantFlush = useCallback(() => {
    if (tokenFlushRafRef.current != null) return;
    tokenFlushRafRef.current = requestAnimationFrame(() => {
      tokenFlushRafRef.current = null;
      const text = assistantDraftRef.current;
      const aid = streamingAssistantIdRef.current;
      const urg = urgenciaRef.current ?? undefined;
      setMessages((prev) => {
        const withoutTail = prev.filter((m) => m.id !== aid);
        return [
          ...withoutTail,
          { id: aid, role: "assistant" as const, content: text, urgencia: urg },
        ];
      });
    });
  }, []);

  const send = useCallback(async () => {
    setError(null);
    if (!canSend) {
      setError(
        needsProfessionalGate
          ? "Confirme o perfil profissional para usar este fluxo (demo)."
          : "Digite uma mensagem.",
      );
      return;
    }

    let patientContext: PatientContextPayload | undefined;
    const trimmed = patientContextText.trim();
    if (trimmed) {
      try {
        patientContext = JSON.parse(trimmed) as PatientContextPayload;
      } catch {
        setError("JSON inválido em contexto da paciente.");
        return;
      }
    }

    const userContent = input.trim();
    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: userContent,
    };

    const prev = messagesRef.current;
    const nextThread: ChatMessage[] = [...prev, userMsg];
    setMessages(nextThread);
    setInput("");
    setBusy(true);
    setExplain(null);
    urgenciaRef.current = null;
    latestExplainRef.current = null;
    latestTraceRef.current = null;
    startedAtRef.current = Date.now();

    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const rid = crypto.randomUUID();
    setRequestId(rid);

    const body: ChatStreamRequest = {
      flowId,
      messages: nextThread.map((m) => ({ role: m.role, content: m.content })),
      patientContext,
    };

    const assistantId = newId();
    streamingAssistantIdRef.current = assistantId;
    assistantDraftRef.current = "";

    const timeoutMs = 120_000;
    const timeoutId = window.setTimeout(() => {
      abortRef.current?.abort();
    }, timeoutMs);

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-request-id": rid,
        },
        body: JSON.stringify(body),
        signal: abortRef.current.signal,
      });

      if (!res.ok || !res.body) {
        const t = await res.text().catch(() => "");
        throw new Error(t || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      await consumeSse(reader, (event, dataJson) => {
        if (event === "meta") {
          const meta = JSON.parse(dataJson) as {
            requestId?: string;
            urgencia?: UrgenciaLevel;
          };
          if (meta.requestId) setRequestId(meta.requestId);
          if (meta.urgencia) urgenciaRef.current = meta.urgencia;
          appendLog(`meta: ${dataJson}`);
          return;
        }
        if (event === "token") {
          const { delta } = JSON.parse(dataJson) as { delta: string };
          assistantDraftRef.current += delta;
          scheduleAssistantFlush();
          return;
        }
        if (event === "explain") {
          const ex = JSON.parse(dataJson) as ExplainBlock;
          latestExplainRef.current = ex;
          setExplain(ex);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingAssistantIdRef.current ? { ...m, explain: ex } : m,
            ),
          );
          appendLog(`explain: ${dataJson}`);
          return;
        }
        if (event === "log") {
          appendLog(`log: ${dataJson}`);
          return;
        }
        if (event === "trace") {
          try {
            latestTraceRef.current = JSON.parse(dataJson) as TraceSummary;
          } catch {
            // trace ainda nao crítico para a UI; mantém logs mas não bloqueia.
          }
          appendLog(`trace: ${dataJson}`);
          return;
        }
        if (event === "error") {
          const err = JSON.parse(dataJson) as { message?: string };
          throw new Error(err.message || "Erro no stream");
        }
        if (event === "done") {
          appendLog("done");
        }
      });

      cancelTokenFlush();
      const assistantText = assistantDraftRef.current;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: assistantText,
                urgencia: urgenciaRef.current ?? m.urgencia,
              }
            : m,
        ),
      );

      const durationMs = Date.now() - startedAtRef.current;
      const explainSnap = latestExplainRef.current;
      const promptObj = {
        flowId,
        patientContext,
        messages: [...body.messages, { role: "assistant" as const, content: assistantText }],
      };
      const promptText = JSON.stringify(promptObj, null, 2);

      if (persist) {
        try {
          const pres = await fetch("/api/atendimentos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              requestId: rid,
              flowId,
              perguntaText: userMsg.content,
              duracaoMs: durationMs,
              urgencia: urgenciaRef.current ?? "nenhuma",
              promptText,
              respostaBruta: assistantText,
              classificacaoJson: explainSnap ? JSON.stringify(explainSnap) : undefined,
              langgraphTraceJson: latestTraceRef.current
                ? JSON.stringify(latestTraceRef.current)
                : null,
            }),
          });
          if (!pres.ok) {
            const t = await pres.text().catch(() => "");
            appendLog(`persist_failed: ${t}`);
          } else {
            appendLog("persist_ok");
          }
        } catch (pe) {
          appendLog(`persist_error: ${pe instanceof Error ? pe.message : "?"}`);
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Falha desconhecida";
      setError(msg);
      appendLog(`error: ${msg}`);
    } finally {
      window.clearTimeout(timeoutId);
      cancelTokenFlush();
      flushLogsNow();
      setBusy(false);
    }
  }, [
    appendLog,
    cancelTokenFlush,
    canSend,
    flushLogsNow,
    flowId,
    needsProfessionalGate,
    patientContextText,
    persist,
    scheduleAssistantFlush,
    input,
  ]);

  useEffect(() => () => cancelTokenFlush(), [cancelTokenFlush]);

  return (
    <div className="appShell">
      <header className="pageHeader">
        {embedded ? (
          <h1 className="pageTitle">Novo atendimento</h1>
        ) : (
          <>
            <h1 className="pageTitle">Assistente (demo) — saúde da mulher</h1>
            <p className="muted">
              BFF Next.js → orquestração Python (LangChain/LangGraph). Modo atual:{" "}
              <a className="pillLink" href="/api/health" target="_blank" rel="noopener noreferrer">
                ver /api/health
              </a>
            </p>
          </>
        )}
      </header>

      <ClinicalDisclaimerBanner />

      <div className="appGrid">
        <section className="card" aria-labelledby="chatHeading">
          <h2 id="chatHeading" className="cardTitle">
            Conversa
          </h2>

          <div className="chatLog" aria-live="polite">
            {messages.length === 0 ? (
              <p className="muted">Nenhuma mensagem ainda.</p>
            ) : (
              messages.map((m) => (
                <AssistantMessageBubble
                  key={m.id}
                  role={m.role}
                  content={m.content}
                  urgencia={m.urgencia}
                />
              ))
            )}
          </div>

          <label className="sectionLabel sectionLabel--field muted" htmlFor="msg">
            Mensagem
          </label>
          <textarea
            id="msg"
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />

          {error ? (
            <p role="alert" className="formAlert">
              {error}
            </p>
          ) : null}

          <div className="btnRow row">
            <button className="btn" type="button" onClick={send} disabled={!canSend}>
              {busy ? "Gerando…" : "Enviar"}
            </button>
            <button
              className="btnSecondary"
              type="button"
              onClick={() => abortRef.current?.abort()}
              disabled={!busy}
            >
              Cancelar
            </button>
          </div>
        </section>

        <aside className="card" aria-label="Painel clínico e integrações">
          <h2 className="cardTitle">Fluxo e contexto</h2>

          <p id="flowLabel" className="sectionLabel sectionLabel--field muted">
            Fluxo LangGraph (FE-INT-02)
          </p>
          <div
            className="filtroChips flowChips"
            role="radiogroup"
            aria-labelledby="flowLabel"
          >
            {(Object.keys(FLOW_LABELS) as ClinicalFlowId[]).map((id) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={flowId === id}
                className={flowChipClass(id, flowId === id)}
                disabled={busy}
                onClick={() => {
                  setFlowId(id);
                  setProfessionalVerified(false);
                }}
              >
                {FLOW_LABELS[id]}
              </button>
            ))}
          </div>

          {needsProfessionalGate ? (
            <div className="callout callout--alert">
              <strong>Gate de identidade (FE-SEC-01 / RF-SEC-02):</strong> confirme que representa
              um <strong>profissional autorizado</strong> neste ambiente de demonstração.
              <div className="btnRow row gateActionRow">
                <button
                  type="button"
                  className={professionalVerified ? "btn" : "filtroChip filtroChip--emergencia"}
                  onClick={() => setProfessionalVerified(true)}
                  disabled={busy || professionalVerified}
                >
                  {professionalVerified ? "Confirmado" : "Confirmo perfil profissional (demo)"}
                </button>
              </div>
            </div>
          ) : null}

          <h3 id="patientContextLabel" className="sectionLabel sectionLabel--block">
            Contexto da paciente (opcional)
          </h3>
          <p id="patientContextHelp" className="muted">
            JSON livre — sem PII real (FE-INT-03 / RF-LC-03).
          </p>
          <textarea
            id="patientContext"
            className="input"
            value={patientContextText}
            onChange={(e) => setPatientContextText(e.target.value)}
            disabled={busy}
            spellCheck={false}
            aria-labelledby="patientContextLabel"
            aria-describedby="patientContextHelp"
          />

          <h3 className="sectionLabel sectionLabel--block">Explainability (FE-UI-01 / RF-SEC-04)</h3>
          <AssistantExplainPanel explain={explain} />

          <AssistantLogPanel requestId={requestId} logs={logs} />
        </aside>
      </div>
    </div>
  );
}
