"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, ReactNode, SVGProps } from "react";

import type { Usuario } from "@/lib/api";

import { IconeAgenda, IconeContatos, IconeHoje } from "./icones";
import { SeletorTema } from "./SeletorTema";

type Item = { href: string; rotulo: string; icone: ComponentType<SVGProps<SVGSVGElement>> };

const ITENS: Item[] = [
  { href: "/hoje", rotulo: "Hoje", icone: IconeHoje },
  { href: "/agenda", rotulo: "Agenda", icone: IconeAgenda },
  { href: "/contatos", rotulo: "Contatos", icone: IconeContatos },
];

// Itens do DESIGN §4 ainda não implementados — visíveis, desabilitados.
const EM_BREVE = ["Conversas", "Sugestões", "Modelos", "Histórico", "Configurações"];

// Shell de navegação (DESIGN §4): menu lateral ≥1024px, barra inferior <640px.
export function AppShell({
  usuario,
  onSair,
  children,
}: {
  usuario: Usuario;
  onSair: () => void;
  children: ReactNode;
}) {
  const path = usePathname();
  const ativo = (href: string) => path === href || path.startsWith(`${href}/`);

  return (
    <div className="app">
      <aside className="lateral">
        <div className="marca">Mensageiro</div>
        {ITENS.map((it) => {
          const Icone = it.icone;
          return (
            <Link key={it.href} href={it.href} className={ativo(it.href) ? "ativo" : ""}>
              <Icone />
              {it.rotulo}
            </Link>
          );
        })}
        {EM_BREVE.map((r) => (
          <span key={r} className="item desabilitado" title="Em breve">
            {r}
          </span>
        ))}
        <div className="rodape">
          <SeletorTema />
          <span className="texto-2" style={{ fontSize: "0.8rem", wordBreak: "break-all" }}>
            {usuario.email}
          </span>
          <button type="button" className="secundario" onClick={onSair}>
            Sair
          </button>
        </div>
      </aside>

      <div>
        <header className="app-topo">
          <span className="marca">Mensageiro</span>
          <div className="acoes">
            <SeletorTema />
            <button type="button" className="fantasma" onClick={onSair}>
              Sair
            </button>
          </div>
        </header>

        <main className="app-main">{children}</main>

        <nav className="barra-inferior" aria-label="Navegação">
          {ITENS.map((it) => {
            const Icone = it.icone;
            return (
              <Link key={it.href} href={it.href} className={ativo(it.href) ? "ativo" : ""}>
                <Icone width={22} height={22} />
                {it.rotulo}
              </Link>
            );
          })}
          <span className="desabilitado" title="Em breve">
            Mais
          </span>
        </nav>
      </div>
    </div>
  );
}
