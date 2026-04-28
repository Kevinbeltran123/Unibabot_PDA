import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryProvider } from "@/components/query-provider";
import { AuthProvider } from "@/hooks/use-auth";
import { Toaster } from "@/components/ui/toaster";
import { ConfirmProvider } from "@/components/ui/confirm-dialog";

/*
 * Una sola familia tipográfica para todo el producto: Inter.
 * La jerarquía se construye con peso (400/500/600/700), tamaño y color,
 * no con familias distintas. El "font-mono" de Tailwind cae en Inter
 * con `tabular-nums`, que da numerales alineados sin necesidad de
 * cambiar de familia.
 */
const sans = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "UnibaBot PDA",
  description: "Verificador automático de Planes de Desarrollo Académico.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${sans.variable} font-sans bg-background text-foreground min-h-screen`}
      >
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
          <QueryProvider>
            <AuthProvider>
              <ConfirmProvider>
                {children}
                <Toaster />
              </ConfirmProvider>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
