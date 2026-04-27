import type { ClinicalFlowId } from "@/types/assistant";

export type AtendimentoFiltro =
  | "todas"
  | "medico"
  | "fora_escopo"
  | "emergencia"
  | "bloqueado";

export type AtendimentoListItem = {
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
  bloqueado: boolean;
  sensitiveRedacted: boolean;
};

export type AtendimentoDetail = AtendimentoListItem & {
  promptText: string | null;
  respostaBruta: string | null;
  classificacaoJson: string | null;
  langgraphTraceJson: string | null;
};

export type AtendimentoCreateBody = {
  requestId: string;
  flowId: ClinicalFlowId;
  perguntaText: string;
  duracaoMs: number;
  urgencia?: string;
  promptText: string;
  respostaBruta: string;
  classificacaoJson?: string;
  langgraphTraceJson?: string | null;
  categoria?: string;
  categoriaConfidence?: number;
  segurancaStatus?: string;
  fontesCount?: number;
  bloqueado?: boolean;
};
