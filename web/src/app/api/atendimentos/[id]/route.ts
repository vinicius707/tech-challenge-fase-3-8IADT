import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { getDb, runMigrations } from "@/db/client";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";
import type { ClinicalFlowId } from "@/types/assistant";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  ctx: { params: { id: string } },
) {
  try {
    const token = cookies().get(SESSION_COOKIE)?.value;
    if (!token) return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
    const session = await verifySessionToken(token);
    const id = ctx.params.id;
    runMigrations();
    const db = getDb();
    const row = db
      .prepare(
        `SELECT
          a.id, a.created_at as createdAt, a.flow_id as flowId, a.pergunta_text as perguntaText,
          a.categoria, a.categoria_confidence as categoriaConfidence, a.seguranca_status as segurancaStatus,
          a.fontes_count as fontesCount, a.duracao_ms as duracaoMs, a.request_id as requestId,
          a.urgencia, a.bloqueado, a.sensitive_redacted as sensitiveRedacted,
          d.prompt_text as promptText, d.resposta_bruta as respostaBruta,
          d.classificacao_json as classificacaoJson, d.langgraph_trace_json as langgraphTraceJson
        FROM atendimentos a
        JOIN atendimento_detalhes d ON d.atendimento_id = a.id
        WHERE a.id = ? AND a.user_id = ?
        LIMIT 1`,
      )
      .get(id, session.sub) as
      | {
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
          promptText: string | null;
          respostaBruta: string | null;
          classificacaoJson: string | null;
          langgraphTraceJson: string | null;
        }
      | undefined;

    if (!row) return NextResponse.json({ error: "Não encontrado" }, { status: 404 });

    return NextResponse.json({
      id: row.id,
      createdAt: row.createdAt,
      flowId: row.flowId,
      perguntaText: row.perguntaText,
      categoria: row.categoria,
      categoriaConfidence: row.categoriaConfidence,
      segurancaStatus: row.segurancaStatus,
      fontesCount: row.fontesCount,
      duracaoMs: row.duracaoMs,
      requestId: row.requestId,
      urgencia: row.urgencia,
      bloqueado: Boolean(row.bloqueado),
      sensitiveRedacted: Boolean(row.sensitiveRedacted),
      promptText: row.promptText,
      respostaBruta: row.respostaBruta,
      classificacaoJson: row.classificacaoJson,
      langgraphTraceJson: row.langgraphTraceJson,
    });
  } catch {
    return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
  }
}
