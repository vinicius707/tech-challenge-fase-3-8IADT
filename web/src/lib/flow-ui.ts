import type { ClinicalFlowId } from "@/types/assistant";

/** Tons de chip alinhados aos filtros da auditoria (identidade visual partilhada). */
const FLOW_CHIP_TONE: Record<ClinicalFlowId, "medico" | "emergencia" | "bloqueado" | "fora_escopo"> = {
  triagemGinecologica: "medico",
  violenciaDomestica: "emergencia",
  obstetrico: "bloqueado",
  prevencao: "fora_escopo",
};

/** Chip de fluxo LangGraph (mesmas classes que filtros de listagem). */
export function flowChipClass(flowId: ClinicalFlowId, selected: boolean): string {
  const tone = FLOW_CHIP_TONE[flowId];
  const base = `filtroChip filtroChip--${tone}`;
  return selected ? `${base} filtroChip--active` : base;
}
