import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { RegistrarSW } from "@/components/RegistrarSW";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mensageiro",
  description: "Assistente de mensagens no WhatsApp",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#2b59c3",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        {children}
        <RegistrarSW />
      </body>
    </html>
  );
}
