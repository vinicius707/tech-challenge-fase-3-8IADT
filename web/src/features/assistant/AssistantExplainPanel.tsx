import { memo } from "react";
import type { ExplainBlock } from "@/types/assistant";

type Props = { explain: ExplainBlock | null };

export const AssistantExplainPanel = memo(function AssistantExplainPanel({ explain }: Props) {
  if (!explain) {
    return <p className="muted">Aguardando resposta…</p>;
  }
  return (
    <div className="bubble assistant">
      <div>
        <strong>Fonte:</strong> {explain.fonte ?? "—"}
      </div>
      <div>
        <strong>Confiança:</strong>{" "}
        {explain.confianca === undefined ? "—" : `${Math.round(explain.confianca * 100)}%`}
      </div>
      {explain.raciocinioClinico ? (
        <div style={{ marginTop: "0.5rem" }}>
          <strong>Raciocínio (alto nível):</strong>{" "}
          <span style={{ whiteSpace: "pre-wrap" }}>{explain.raciocinioClinico}</span>
        </div>
      ) : null}
      <div style={{ marginTop: "0.5rem" }}>
        <strong>Lacunas:</strong>
        <ul>
          {(explain.lacunas ?? []).map((l, i) => (
            <li key={`${i}-${l.slice(0, 40)}`}>{l}</li>
          ))}
        </ul>
      </div>
    </div>
  );
});
