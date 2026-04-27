import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assistente — Saúde da mulher (demo)",
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
      <body>{children}</body>
    </html>
  );
}
