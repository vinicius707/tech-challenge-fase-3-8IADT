import type { AtendimentoFiltro, AtendimentoListItem } from "@/types/atendimento";

/** Nível agregado para cor na UI (urgência + bloqueio + redação sensível). */
export type GravidadeNivel = "critico" | "alto" | "moderado" | "rotina";

export function gravidadeFromItem(
  row: Pick<AtendimentoListItem, "urgencia" | "bloqueado" | "sensitiveRedacted">,
): GravidadeNivel {
  if (row.bloqueado) return "critico";
  const u = (row.urgencia || "nenhuma").toLowerCase();
  if (u === "emergencia") return "critico";
  if (u === "alta") return "alto";
  if (row.sensitiveRedacted) return "alto";
  if (u === "moderada") return "moderado";
  return "rotina";
}

export function gravidadeTitulo(nivel: GravidadeNivel): string {
  switch (nivel) {
    case "critico":
      return "Crítico — emergência ou bloqueado";
    case "alto":
      return "Alto — urgência elevada ou conteúdo sensível redigido";
    case "moderado":
      return "Moderado";
    default:
      return "Rotina";
  }
}

export function urgenciaLegivel(urgencia: string): string {
  const u = urgencia.toLowerCase();
  const map: Record<string, string> = {
    nenhuma: "Nenhuma",
    moderada: "Moderada",
    alta: "Alta",
    emergencia: "Emergência",
  };
  return map[u] ?? urgencia;
}

/** Classe CSS base `gravRow gravRow--{nivel}` */
export function gravidadeRowClass(nivel: GravidadeNivel): string {
  return `gravRow gravRow--${nivel}`;
}

/** Classe para pastilha de categoria: `gravPill gravPill--{nivel}` */
export function gravidadePillClass(nivel: GravidadeNivel): string {
  return `gravPill gravPill--${nivel}`;
}

/** Classe para pastilha de urgência: `gravUrg gravUrg--{nivel}` */
export function gravidadeUrgenciaClass(nivel: GravidadeNivel): string {
  return `gravUrg gravUrg--${nivel}`;
}

/** Acento visual dos botões de filtro (tipo de listagem, não urgência). */
export function filtroChipTone(id: AtendimentoFiltro): string {
  return `filtroChip filtroChip--${id}`;
}
