import { memo } from "react";
import type { ChatMessage } from "@/types/assistant";

type Props = Pick<ChatMessage, "role" | "content" | "urgencia">;

export const AssistantMessageBubble = memo(function AssistantMessageBubble({
  role,
  content,
  urgencia,
}: Props) {
  return (
    <div className={`bubble ${role === "user" ? "user" : "assistant"}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{role === "user" ? "Você" : "Assistente"}</strong>
        {urgencia && urgencia !== "nenhuma" ? (
          <span className="pillUrgent">Urgência: {urgencia}</span>
        ) : null}
      </div>
      <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>
    </div>
  );
});
