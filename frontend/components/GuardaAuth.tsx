"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { logout, me, type Usuario } from "@/lib/api";
import { lerToken, limparToken } from "@/lib/auth";

import { AppShell } from "./AppShell";
import { ListaEsqueleto } from "./Esqueleto";

// Guarda de autenticação (DESIGN/§ auth): sem token válido → /login. Envolve as telas no shell.
export function GuardaAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    if (!lerToken()) {
      router.replace("/login");
      return;
    }
    me()
      .then(setUsuario)
      .catch(() => {
        limparToken();
        router.replace("/login");
      });
  }, [router]);

  async function sair() {
    await logout();
    limparToken();
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
