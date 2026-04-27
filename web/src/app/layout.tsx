import type { Metadata } from "next";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Assistente — Saúde da mulher (demo)",
    template: "%s | Assistente clínico (demo)",
  },
  description:
    "Interface de apoio à decisão clínica conectada à orquestração LangChain/LangGraph (BFF Next.js).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>
        <a href="#conteudo-principal" className="skipLink">
          Saltar para o conteúdo principal
        </a>
        <main id="conteudo-principal" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  );
}
