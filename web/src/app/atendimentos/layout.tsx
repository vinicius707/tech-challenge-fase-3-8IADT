import { AppHeader } from "@/features/layout/AppHeader";

export default function AtendimentosLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <AppHeader />
      {children}
    </>
  );
}
