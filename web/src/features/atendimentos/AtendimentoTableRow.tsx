import { memo } from "react";
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
  return (
    <tr className={selected ? "rowSelected" : undefined}>
      <td>
        <button type="button" className="linkButton" onClick={() => onSelect(row.id)}>
          {dateLabel}
        </button>
      </td>
      <td style={{ maxWidth: 420 }}>{row.perguntaText}</td>
      <td>
        <span className="pill">
          {row.categoria}{" "}
          {row.categoriaConfidence != null
            ? `${Math.round(row.categoriaConfidence * 100)}%`
            : ""}
        </span>
      </td>
      <td>{row.segurancaStatus === "ok" ? "✓ OK" : row.segurancaStatus}</td>
      <td>{row.fontesCount}</td>
      <td>{(row.duracaoMs / 1000).toFixed(1)}s</td>
    </tr>
  );
});
