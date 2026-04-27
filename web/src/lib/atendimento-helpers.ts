import type { ClinicalFlowId, ExplainBlock } from "@/types/assistant";

export function isViolenceFlow(flowId: ClinicalFlowId): boolean {
  return flowId === "violenciaDomestica";
}

export function redactResposta(flowId: ClinicalFlowId, texto: string): string {
  if (!isViolenceFlow(flowId)) return texto;
  return "[REDACTED] Conteúdo sensível não armazenado em claro (fluxo violência doméstica).";
}

export function deriveCategoria(
  flowId: ClinicalFlowId,
  urgencia: string | undefined,
  explain: ExplainBlock | null,
): { categoria: string; confidence: number } {
  if (flowId === "violenciaDomestica") {
    return { categoria: "Sensível — violência", confidence: explain?.confianca ?? 0.45 };
  }
  if (urgencia === "emergencia" || urgencia === "alta") {
    return { categoria: "Emergência", confidence: 0.9 };
  }
  if (flowId === "prevencao") {
    return { categoria: "Prevenção / rastreamento", confidence: explain?.confianca ?? 0.65 };
  }
  if (flowId === "obstetrico") {
    return { categoria: "Obstétrico", confidence: explain?.confianca ?? 0.65 };
  }
  return { categoria: "Saúde da mulher / GO", confidence: explain?.confianca ?? 0.6 };
}

export function fontesCountFromExplain(explain: ExplainBlock | null): number {
  if (!explain?.fonte) return 0;
  const pmids = explain.fonte.match(/\d{5,8}/g);
  if (pmids?.length) return pmids.length;
  return 1;
}
