"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { logout, me, type Usuario } from "@/lib/api";
import { lerToken, limparToken } from "@/lib/auth";

// Shell protegido: exige token válido; valida em /auth/me e redireciona ao login se inválido.
export default function PainelPage() {
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
      <main className="centro">
        <p className="texto-2">Carregando…</p>
      </main>
    );
  }

  return (
    <div className="shell">
      <header className="topo">
        <strong>Mensageiro</strong>
        <div>
          <span className="texto-2">{usuario.email}</span>
          <button className="secundario" onClick={sair} type="button">
            Sair
          </button>
        </div>
      </header>
      <main className="conteudo">
        <h1>Olá, {usuario.nome}</h1>
        <p className="texto-2">
          Painel protegido. As telas (Hoje, Agenda, Contatos…) chegam nas próximas fases.
        </p>
      </main>
    </div>
  );
}
