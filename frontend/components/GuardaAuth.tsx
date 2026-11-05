"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { logout, me, type Usuario } from "@/lib/api";

import { AppShell } from "./AppShell";
import { ListaEsqueleto } from "./Esqueleto";

// Guarda de autenticação (DESIGN/§ auth): valida a sessão pelo cookie via GET /api/auth/me
// (ADR 0012). 401 → /login. Envolve as telas no shell.
export function GuardaAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    me()
      .then(setUsuario)
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  async function sair() {
    await logout();
    router.replace("/login");
  }

  if (!usuario) {
    return (
      <main className="app-main">
        <ListaEsqueleto linhas={4} />
      </main>
    );
  }

  return (
    <AppShell usuario={usuario} onSair={sair}>
      {children}
    </AppShell>
  );
}
