import type Database from "better-sqlite3";
import type { AtendimentoFiltro, AtendimentoListItem } from "@/types/atendimento";
import type { ClinicalFlowId } from "@/types/assistant";

export type AtendimentosListResult = {
  page: number;
  pageSize: number;
  total: number;
  agregados: { total: number; emergencias: number; bloqueados: number };
  items: AtendimentoListItem[];
};

export function parseAtendimentoFiltro(v: string | null): AtendimentoFiltro {
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

export function queryAtendimentosList(
  db: Database.Database,
  userId: string,
  opts: {
    filtro: AtendimentoFiltro;
    page: number;
    pageSize: number;
    soEmergencias: boolean;
  },
): AtendimentosListResult {
  const { filtro, page, pageSize, soEmergencias } = opts;

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

  return {
    page,
    pageSize,
    total,
    agregados: {
      total: ag.total ?? 0,
      emergencias: ag.emergencias ?? 0,
      bloqueados: ag.bloqueados ?? 0,
    },
    items,
  };
}
