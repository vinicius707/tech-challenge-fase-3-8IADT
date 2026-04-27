import dynamic from "next/dynamic";

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
