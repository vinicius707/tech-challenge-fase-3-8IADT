/**
 * Tipos compartilhados UI ↔ BFF ↔ orquestração Python.
 * Alinhado a RF-SEC-04 e docs/api.md
 */

export type ClinicalFlowId =
  | "triagemGinecologica"
  | "violenciaDomestica"
  | "obstetrico"
  | "prevencao";

export type UrgenciaLevel = "nenhuma" | "moderada" | "alta" | "emergencia";

export interface ExplainBlock {
  fonte?: string;
  /** 0–1 normalizado no BFF quando possível */
  confianca?: number;
  lacunas?: string[];
  raciocinioClinico?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  explain?: ExplainBlock;
  urgencia?: UrgenciaLevel;
}

export interface PatientContextPayload {
  resumo?: string;
  preventivos?: Record<string, unknown>;
  obstetrica?: Record<string, unknown>;
  cicloMenstrual?: Record<string, unknown>;
  historicoReprodutivo?: Record<string, unknown>;
}

export interface ChatStreamRequest {
  flowId: ClinicalFlowId;
  threadId?: string;
  messages: Array<Pick<ChatMessage, "role" | "content">>;
  patientContext?: PatientContextPayload;
}

export type SseEventName =
  | "meta"
  | "token"
  | "explain"
  | "log"
  | "trace"
  | "done"
  | "error";

export interface SseMetaPayload {
  requestId: string;
  flowId: ClinicalFlowId;
  modelVersion?: string;
  urgencia?: UrgenciaLevel;
}

export interface SseTokenPayload {
  delta: string;
}

export interface SseLogPayload {
  level: "info" | "warn" | "error";
  message: string;
  ts: string;
}

export interface SseErrorPayload {
  code: string;
  message: string;
}

export interface TraceNode {
  name: string;
  status?: "ok" | "skipped" | "blocked" | "error";
  summary?: string;
  safetyFlags?: string[];
}

export interface TraceSummary {
  flowId: ClinicalFlowId;
  nodes: TraceNode[];
  finalRisk?: UrgenciaLevel | null;
}
