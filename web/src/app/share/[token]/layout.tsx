import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Reporte compartido - UnibaBot PDA",
  description: "Vista publica read-only del reporte de cumplimiento.",
  robots: { index: false, follow: false, googleBot: { index: false, follow: false } },
};

export default function SharedLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
