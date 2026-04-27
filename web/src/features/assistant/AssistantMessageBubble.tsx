import { memo } from "react";
import {
  gravidadeFromUrgencia,
  gravidadeTitulo,
  gravidadeUrgenciaClass,
  urgenciaLegivel,
} from "@/lib/atendimento-gravidade";
import type { ChatMessage } from "@/types/assistant";

type Props = Pick<ChatMessage, "role" | "content" | "urgencia">;

export const AssistantMessageBubble = memo(function AssistantMessageBubble({
  role,
  content,
  urgencia,
}: Props) {
  const nivel = gravidadeFromUrgencia(urgencia);
  const showUrg = urgencia && urgencia !== "nenhuma";

  return (
    <div className={`bubble ${role === "user" ? "user" : "assistant"}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{role === "user" ? "Você" : "Assistente"}</strong>
        {showUrg ? (
          <span className={gravidadeUrgenciaClass(nivel)} title={gravidadeTitulo(nivel)}>
            {urgenciaLegivel(urgencia)}
          </span>
        ) : null}
      </div>
      <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>
    </div>
  );
});
