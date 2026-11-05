import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import { RegistrarSW } from "@/components/RegistrarSW";
import { SCRIPT_TEMA } from "@/lib/tema";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--fonte", display: "swap" });

export const metadata: Metadata = {
  title: "Mensageiro",
  description: "Assistente de mensagens no WhatsApp",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#2b59c3" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1115" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body>
        {/* Aplica o tema salvo antes da 1ª pintura (sem flash) — ADR 0010. */}
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
        {children}
        <RegistrarSW />
      </body>
    </html>
  );
}
