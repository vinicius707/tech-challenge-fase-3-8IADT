import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import crypto from "crypto";
import { getDb, runMigrations } from "@/db/client";
import {
  deriveCategoria,
  fontesCountFromExplain,
  isViolenceFlow,
  redactResposta,
} from "@/lib/atendimento-helpers";
import { parseAtendimentoFiltro, queryAtendimentosList } from "@/lib/atendimentos-list";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";
import type { AtendimentoCreateBody } from "@/types/atendimento";
import type { ClinicalFlowId } from "@/types/assistant";
import type { ExplainBlock } from "@/types/assistant";

export const runtime = "nodejs";

const FLOW_IDS: ClinicalFlowId[] = [
  "triagemGinecologica",
  "violenciaDomestica",
  "obstetrico",
  "prevencao",
];

function isFlowId(v: unknown): v is ClinicalFlowId {
  return typeof v === "string" && (FLOW_IDS as string[]).includes(v);
}

async function requireUserId(): Promise<string> {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) throw new Error("unauthorized");
  const session = await verifySessionToken(token);
  return session.sub;
}

export async function GET(req: Request) {
  try {
    const userId = await requireUserId();
    runMigrations();
    const db = getDb();

    const url = new URL(req.url);
    const filtro = parseAtendimentoFiltro(url.searchParams.get("filtro"));
    const page = Math.max(1, Number(url.searchParams.get("page") || "1") || 1);
    const pageSize = Math.min(50, Math.max(1, Number(url.searchParams.get("pageSize") || "10") || 10));
    const soEmergencias = url.searchParams.get("so_emergencias") === "1";

    const payload = queryAtendimentosList(db, userId, {
      filtro,
      page,
      pageSize,
      soEmergencias,
    });

    return NextResponse.json(payload);
  } catch (e) {
    if (e instanceof Error && e.message === "unauthorized") {
      return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
    }
    const msg = e instanceof Error ? e.message : "Erro";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const userId = await requireUserId();
    let body: unknown;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
    }
    const b = body as Partial<AtendimentoCreateBody>;
    if (!b.requestId || typeof b.requestId !== "string") {
      return NextResponse.json({ error: "requestId obrigatório" }, { status: 400 });
    }
    if (!isFlowId(b.flowId)) return NextResponse.json({ error: "flowId inválido" }, { status: 400 });
    if (!b.perguntaText || typeof b.perguntaText !== "string") {
      return NextResponse.json({ error: "perguntaText obrigatório" }, { status: 400 });
    }
    if (typeof b.duracaoMs !== "number" || !Number.isFinite(b.duracaoMs)) {
      return NextResponse.json({ error: "duracaoMs inválido" }, { status: 400 });
    }
    if (!b.promptText || typeof b.promptText !== "string") {
      return NextResponse.json({ error: "promptText obrigatório" }, { status: 400 });
    }
    if (!b.respostaBruta || typeof b.respostaBruta !== "string") {
      return NextResponse.json({ error: "respostaBruta obrigatório" }, { status: 400 });
    }

    const requestId = b.requestId;
    const flowId = b.flowId;
    const perguntaText = b.perguntaText;
    const duracaoMs = b.duracaoMs;
    const promptText = b.promptText;
    const respostaBruta = b.respostaBruta;
    const urgencia = typeof b.urgencia === "string" ? b.urgencia : "nenhuma";
    let explain: ExplainBlock | null = null;
    if (typeof b.classificacaoJson === "string" && b.classificacaoJson.trim()) {
      try {
        explain = JSON.parse(b.classificacaoJson) as ExplainBlock;
      } catch {
        explain = null;
      }
    }

    const derived =
      b.categoria && typeof b.categoriaConfidence === "number"
        ? { categoria: b.categoria, confidence: b.categoriaConfidence }
        : deriveCategoria(flowId, urgencia, explain);

    const fontesCount =
      typeof b.fontesCount === "number" && Number.isFinite(b.fontesCount)
        ? b.fontesCount
        : fontesCountFromExplain(explain);

    const segurancaStatus =
      typeof b.segurancaStatus === "string" ? b.segurancaStatus : "ok";
    const bloqueado = b.bloqueado ? 1 : 0;
    const sensitive = isViolenceFlow(flowId) ? 1 : 0;

    const promptStored = sensitive
      ? "[REDACTED] Prompt omitido (fluxo violência doméstica; MVP)."
      : promptText;
    const respostaStored = redactResposta(flowId, respostaBruta);

    runMigrations();
    const db = getDb();

    const existing = db
      .prepare(`SELECT id FROM atendimentos WHERE request_id = ? LIMIT 1`)
      .get(requestId) as { id: string } | undefined;
    if (existing) {
      return NextResponse.json({ ok: true, id: existing.id, idempotent: true });
    }

    const id = crypto.randomUUID();
    const now = Date.now();

    const tx = db.transaction(() => {
      db.prepare(
        `INSERT INTO atendimentos (
          id, user_id, created_at, flow_id, pergunta_text, categoria, categoria_confidence,
          seguranca_status, fontes_count, duracao_ms, request_id, urgencia, bloqueado, sensitive_redacted
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      ).run(
        id,
        userId,
        now,
        flowId,
        perguntaText.slice(0, 4000),
        derived.categoria,
        derived.confidence,
        segurancaStatus,
        fontesCount,
        Math.max(0, Math.floor(duracaoMs)),
        requestId,
        urgencia,
        bloqueado,
        sensitive,
      );

      db.prepare(
        `INSERT INTO atendimento_detalhes (
          atendimento_id, prompt_text, resposta_bruta, classificacao_json, langgraph_trace_json
        ) VALUES (?,?,?,?,?)`,
      ).run(
        id,
        promptStored.slice(0, 200_000),
        respostaStored.slice(0, 200_000),
        b.classificacaoJson ?? null,
        b.langgraphTraceJson ?? null,
      );
    });

    try {
      tx();
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      if (m.includes("UNIQUE") || m.includes("SQLITE_CONSTRAINT")) {
        const row = db
          .prepare(`SELECT id FROM atendimentos WHERE request_id = ? LIMIT 1`)
          .get(requestId) as { id: string } | undefined;
        if (row) {
          return NextResponse.json({ ok: true, id: row.id, idempotent: true });
        }
      }
      throw e;
    }

    return NextResponse.json({ ok: true, id }, { status: 201 });
  } catch (e) {
    if (e instanceof Error && e.message === "unauthorized") {
      return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
    }
    const msg = e instanceof Error ? e.message : "Erro";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
