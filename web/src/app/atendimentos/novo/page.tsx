import type { Metadata } from "next";
import dynamic from "next/dynamic";

export const metadata: Metadata = {
  title: "Novo atendimento",
  description:
    "Conversa com o assistente clínico (streaming SSE) e gravação de auditoria após conclusão.",
  robots: { index: false, follow: false },
};

const AssistantExperience = dynamic(
  () =>
    import("@/features/assistant/AssistantExperience").then((m) => ({
      default: m.AssistantExperience,
    })),
  {
    loading: () => (
      <div className="appShell">
        <p className="muted">A carregar assistente…</p>
      </div>
    ),
    ssr: true,
  },
);

export default function NovoAtendimentoPage() {
  return <AssistantExperience persist embedded />;
}
