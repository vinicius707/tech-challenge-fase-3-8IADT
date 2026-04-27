import { memo } from "react";
import {
  gravidadeFromItem,
  gravidadePillClass,
  gravidadeRowClass,
  gravidadeTitulo,
  gravidadeUrgenciaClass,
  urgenciaLegivel,
} from "@/lib/atendimento-gravidade";
import type { AtendimentoListItem } from "@/types/atendimento";

type Props = {
  row: AtendimentoListItem;
  selected: boolean;
  dateLabel: string;
  onSelect: (id: string) => void;
};

export const AtendimentoTableRow = memo(function AtendimentoTableRow({
  row,
  selected,
  dateLabel,
  onSelect,
}: Props) {
  const nivel = gravidadeFromItem(row);
  const trClass = [gravidadeRowClass(nivel), selected ? "rowSelected" : ""].filter(Boolean).join(" ");

  return (
    <tr className={trClass}>
      <td>
        <button type="button" className="linkButton" onClick={() => onSelect(row.id)}>
          {dateLabel}
        </button>
      </td>
      <td style={{ maxWidth: 420 }}>{row.perguntaText}</td>
      <td>
        <span className={gravidadePillClass(nivel)} title={gravidadeTitulo(nivel)}>
          {row.categoria}
          {row.categoriaConfidence != null
            ? ` · ${Math.round(row.categoriaConfidence * 100)}%`
            : ""}
        </span>
      </td>
      <td>
        <div className="gravSegCell">
          <span className={gravidadeUrgenciaClass(nivel)} title={gravidadeTitulo(nivel)}>
            {urgenciaLegivel(row.urgencia)}
          </span>
          <span className="gravSegStatus">
            {row.segurancaStatus === "ok" ? "Segurança: OK" : `Seg.: ${row.segurancaStatus}`}
          </span>
        </div>
      </td>
      <td>{row.fontesCount}</td>
      <td>{(row.duracaoMs / 1000).toFixed(1)}s</td>
    </tr>
  );
});
