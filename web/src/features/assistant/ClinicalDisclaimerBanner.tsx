/** Aviso legal estático (sem props) — evita recriar o mesmo JSX no render do assistente. */
export function ClinicalDisclaimerBanner() {
  return (
    <div className="callout callout--warn" role="note">
      <strong>Aviso clínico e legal (FE-UI-02):</strong> ferramenta de{" "}
      <strong>apoio à decisão</strong>. Não prescreve, não diagnostica de forma definitiva e não
      substitui avaliação presencial. Em risco ou violência: acione protocolo institucional e
      profissionais habilitados.
    </div>
  );
}
