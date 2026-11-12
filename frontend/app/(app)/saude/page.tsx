"use client";

import { useRouter } from "next/navigation";
import { type CSSProperties, useCallback, useEffect, useState } from "react";

import { ListaEsqueleto } from "@/components/Esqueleto";
import { FUSO_SAO_PAULO } from "@/lib/datas";
import { ApiError, type SaudeDeep, obterSaude } from "@/lib/api";

// Tela "Saúde do sistema" (spec 0021 / BRIEFING §12): retrato operacional read-only. Token e
// qualidade do número da Meta ficam fora até a Fase 0. 401 → login (sessão expirada).

const FMT = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO_SAO_PAULO,
  dateStyle: "short",
  timeStyle: "short",
});

const WORKER_TXT: Record<string, string> = {
  vivo: "Vivo",
  parado: "Parado",
  desconhecido: "Desconhecido",
};

const CARTAO: CSSProperties = { marginBottom: 0 };
const TITULO: CSSProperties = { fontSize: "0.9rem", margin: "0 0 0.4rem" };

export default function SaudePage() {
  const router = useRouter();
  const [saude, setSaude] = useState<SaudeDeep | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setSaude(null);
    setErro(null);
    obterSaude()
      .then(setSaude)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [router]);

  useEffect(carregar, [carregar]);

  const okRuim = (bom: boolean) => (bom ? "texto-2" : "erro");

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Saúde do sistema</h1>
          <p className="pagina-sub" style={{ margin: 0 }}>
            Visão operacional (atualiza ao abrir)
          </p>
        </div>
        <button type="button" className="fantasma" onClick={carregar}>
          Atualizar
        </button>
      </div>

      {erro ? <p className="erro">{erro}</p> : null}
      {saude === null && !erro ? <ListaEsqueleto linhas={4} /> : null}

      {saude ? (
        <div
          style={{
            display: "grid",
            gap: "0.75rem",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          }}
        >
          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Banco</h2>
            <p className={okRuim(saude.banco.status === "ok")} style={{ margin: 0 }}>
              {saude.banco.status === "ok" ? "Conectado" : "Erro"}
            </p>
          </div>

          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Worker</h2>
            <p className={okRuim(saude.worker.status === "vivo")} style={{ margin: 0 }}>
              {WORKER_TXT[saude.worker.status] ?? saude.worker.status}
            </p>
            <p className="texto-2" style={{ fontSize: "0.8rem", margin: "0.3rem 0 0" }}>
              {saude.worker.ultimo_ciclo_em
                ? `Último ciclo: ${FMT.format(new Date(saude.worker.ultimo_ciclo_em))}`
                : "Nunca executou"}
            </p>
          </div>

          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Envios hoje</h2>
            {Object.keys(saude.envios_hoje).length === 0 ? (
              <p className="texto-2" style={{ margin: 0 }}>
                Nenhum envio hoje
              </p>
            ) : (
              <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem" }}>
                {Object.entries(saude.envios_hoje).map(([s, n]) => (
                  <li key={s}>
                    {s}: <strong>{n}</strong>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Taxa de falha (hoje)</h2>
            <p className={okRuim(saude.taxa_falha_hoje.percentual <= 5)} style={{ margin: 0 }}>
              <strong>{saude.taxa_falha_hoje.percentual}%</strong>
            </p>
            <p className="texto-2" style={{ fontSize: "0.8rem", margin: "0.3rem 0 0" }}>
              {saude.taxa_falha_hoje.falhas} falha(s) em {saude.taxa_falha_hoje.tentativas}{" "}
              tentativa(s)
            </p>
          </div>

          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Fila</h2>
            <p style={{ margin: 0 }}>
              <strong>{saude.fila}</strong> agendamento(s) à espera
            </p>
          </div>

          <div className="painel" style={CARTAO}>
            <h2 style={TITULO}>Gasto do mês (estimado)</h2>
            <p style={{ margin: 0 }}>
              <strong>R$ {saude.gasto_mes_estimado.valor.toFixed(2)}</strong>
            </p>
            <p className="texto-2" style={{ fontSize: "0.8rem", margin: "0.3rem 0 0" }}>
              {saude.gasto_mes_estimado.base}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
