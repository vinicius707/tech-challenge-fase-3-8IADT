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
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";
import type { AtendimentoCreateBody, AtendimentoFiltro } from "@/types/atendimento";
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

function parseFiltro(v: string | null): AtendimentoFiltro {
  const allowed: AtendimentoFiltro[] = [
    "todas",
    "medico",
    "fora_escopo",
    "emergencia",
    "bloqueado",
  ];
  if (v && (allowed as string[]).includes(v)) return v as AtendimentoFiltro;
  return "todas";
}

export async function GET(req: Request) {
  try {
    const userId = await requireUserId();
    runMigrations();
    const db = getDb();

    const url = new URL(req.url);
    const filtro = parseFiltro(url.searchParams.get("filtro"));
    const page = Math.max(1, Number(url.searchParams.get("page") || "1") || 1);
    const pageSize = Math.min(50, Math.max(1, Number(url.searchParams.get("pageSize") || "10") || 10));
    const soEmergencias = url.searchParams.get("so_emergencias") === "1";

    const args: unknown[] = [userId];
    let where = "WHERE a.user_id = ?";
    if (soEmergencias) {
      where += " AND a.urgencia IN ('alta','emergencia')";
    }
    switch (filtro) {
      case "medico":
        where +=
          " AND (a.categoria LIKE '%Saúde%' OR a.categoria LIKE '%GO%' OR a.categoria LIKE '%Obst%' OR a.categoria LIKE '%Prevenção%')";
        break;
      case "fora_escopo":
        where += " AND a.categoria LIKE '%Fora%'";
        break;
      case "emergencia":
        where +=
          " AND (a.urgencia IN ('alta','emergencia') OR a.categoria LIKE '%Emergência%')";
        break;
      case "bloqueado":
        where += " AND a.bloqueado = 1";
        break;
      default:
        break;
    }

    const total = (
      db.prepare(`SELECT COUNT(1) as c FROM atendimentos a ${where}`).get(...args) as {
        c: number;
      }
    ).c;

    const ag = db
      .prepare(
        `SELECT
          COUNT(1) as total,
          SUM(CASE WHEN urgencia IN ('alta','emergencia') OR categoria LIKE '%Emergência%' THEN 1 ELSE 0 END) as emergencias,
          SUM(CASE WHEN bloqueado = 1 THEN 1 ELSE 0 END) as bloqueados
        FROM atendimentos a
        WHERE a.user_id = ?`,
      )
      .get(userId) as { total: number; emergencias: number | null; bloqueados: number | null };

    const offset = (page - 1) * pageSize;
    const rows = db
      .prepare(
        `SELECT
          a.id, a.created_at as createdAt, a.flow_id as flowId, a.pergunta_text as perguntaText,
          a.categoria, a.categoria_confidence as categoriaConfidence, a.seguranca_status as segurancaStatus,
          a.fontes_count as fontesCount, a.duracao_ms as duracaoMs, a.request_id as requestId,
          a.urgencia, a.bloqueado, a.sensitive_redacted as sensitiveRedacted
        FROM atendimentos a
        ${where}
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?`,
      )
      .all(...args, pageSize, offset) as Array<{
      id: string;
      createdAt: number;
      flowId: ClinicalFlowId;
      perguntaText: string;
      categoria: string;
      categoriaConfidence: number | null;
      segurancaStatus: string;
      fontesCount: number;
      duracaoMs: number;
      requestId: string;
      urgencia: string;
      bloqueado: number;
      sensitiveRedacted: number;
    }>;

    const items = rows.map((r) => ({
      id: r.id,
      createdAt: r.createdAt,
      flowId: r.flowId,
      perguntaText: r.perguntaText,
      categoria: r.categoria,
      categoriaConfidence: r.categoriaConfidence,
      segurancaStatus: r.segurancaStatus,
      fontesCount: r.fontesCount,
      duracaoMs: r.duracaoMs,
      requestId: r.requestId,
      urgencia: r.urgencia,
      bloqueado: Boolean(r.bloqueado),
      sensitiveRedacted: Boolean(r.sensitiveRedacted),
    }));

    return NextResponse.json({
      page,
      pageSize,
      total,
      agregados: {
        total: ag.total ?? 0,
        emergencias: ag.emergencias ?? 0,
        bloqueados: ag.bloqueados ?? 0,
      },
      items,
    });
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
