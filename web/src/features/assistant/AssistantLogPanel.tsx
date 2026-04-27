import { memo } from "react";

type Props = {
  requestId: string | null;
  logs: string[];
};

export const AssistantLogPanel = memo(function AssistantLogPanel({ requestId, logs }: Props) {
  return (
    <>
      <h3 className="sectionLabel sectionLabel--block">Trilha / logs (FE-INT-04)</h3>
      <p className="muted">
        <strong>x-request-id:</strong> {requestId ?? "—"}
      </p>
      <div style={{ maxHeight: 220, overflow: "auto" }}>
        {logs.length === 0 ? (
          <p className="muted">Sem eventos.</p>
        ) : (
          logs.map((l) => (
            <div key={l} className="logLine">
              {l}
            </div>
          ))
        )}
      </div>
    </>
  );
});
