"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaEsqueleto } from "@/components/Esqueleto";
import { Selo, seloEnvio } from "@/components/Selo";
import { FUSO_SAO_PAULO, saoPauloParaIso } from "@/lib/datas";
import { ApiError, type Envio, listarEnvios, reenviarEnvio } from "@/lib/api";

// Tela Histórico (spec 0014): lista os envios realizados para auditoria. Só leitura; filtros de
// status e período; mais recentes primeiro (o backend ordena por criado_em desc).

const STATUS_OPCOES = [
  { valor: "", texto: "Todos os status" },
  { valor: "criado", texto: "Criado" },
  { valor: "enviando", texto: "Enviando" },
  { valor: "enviado", texto: "Enviado" },
  { valor: "entregue", texto: "Entregue" },
  { valor: "lido", texto: "Lido" },
  { valor: "aguardando_retry", texto: "Reenviando" },
  { valor: "aguardando_decisao", texto: "Precisa decisão" },
  { valor: "falhou", texto: "Falhou" },
];

const FMT = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO_SAO_PAULO,
  dateStyle: "short",
  timeStyle: "short",
});

export default function HistoricoPage() {
  const router = useRouter();
  const [envios, setEnvios] = useState<Envio[] | null>(null);
  const [status, setStatus] = useState("");
  const [desde, setDesde] = useState("");
  const [ate, setAte] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [reenviando, setReenviando] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setEnvios(null);
    setErro(null);
    let params: { status?: string; desde?: string; ate?: string };
    try {
      params = {
        status: status || undefined,
        desde: desde ? saoPauloParaIso(`${desde}T00:00`) : undefined,
        ate: ate ? saoPauloParaIso(`${ate}T23:59:59`) : undefined,
      };
    } catch {
      setErro("Período inválido");
      return;
    }
    listarEnvios(params)
      .then(setEnvios)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [status, desde, ate, router]);

  const reenviar = useCallback(
    (id: string) => {
      setReenviando(id);
      setErro(null);
      reenviarEnvio(id)
        .then(() => carregar())
        .catch((e: unknown) => {
          if (e instanceof ApiError && e.status === 401) {
            router.replace("/login");
            return;
          }
          setErro(e instanceof Error ? e.message : "Falha ao reenviar");
        })
        .finally(() => setReenviando(null));
    },
    [carregar, router],
  );

  useEffect(carregar, [carregar]);

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Histórico</h1>
          <p className="pagina-sub" style={{ margin: 0 }}>
            {envios ? `${envios.length} envio(s)` : "Carregando…"}
          </p>
        </div>
      </div>

      <div className="barra-acoes" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
        <label style={{ fontSize: "0.8rem" }}>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPCOES.map((o) => (
              <option key={o.valor} value={o.valor}>
                {o.texto}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: "0.8rem" }}>
          De
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label style={{ fontSize: "0.8rem" }}>
          Até
          <input type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
        </label>
      </div>

      {erro ? <p className="erro">{erro}</p> : null}
      {envios === null && !erro ? <ListaEsqueleto linhas={5} /> : null}

      {envios !== null && envios.length === 0 ? (
        <EstadoVazio mensagem="Nenhum envio no período. Ajuste os filtros ou aguarde novos disparos." />
      ) : null}

      {(envios ?? []).map((e) => (
        <div className="painel" key={e.id} style={{ marginBottom: "0.75rem" }}>
          <div className="cabecalho-linha" style={{ marginBottom: "0.4rem" }}>
            <strong>{e.contato_nome}</strong>
            <Selo tom={seloEnvio(e.status).tom}>{seloEnvio(e.status).texto}</Selo>
          </div>
          <div className="texto-2" style={{ fontSize: "0.8rem", marginBottom: "0.4rem" }}>
            {e.contato_telefone}
            {e.modelo_nome ? ` · ${e.modelo_nome}` : " · (sem modelo)"}
            {` · ${FMT.format(new Date(e.criado_em))}`}
          </div>
          {(e.status === "falhou" || e.status === "aguardando_decisao") && (e.erro_motivo || e.erro_codigo) ? (
            <p className="erro" style={{ margin: 0, fontSize: "0.8rem" }}>
              Falha{e.erro_codigo ? ` (${e.erro_codigo})` : ""}: {e.erro_motivo ?? "sem detalhe"}
            </p>
          ) : null}
          {e.status === "aguardando_decisao" ? (
            <button
              type="button"
              className="fantasma"
              style={{ marginTop: "0.5rem" }}
              disabled={reenviando === e.id}
              onClick={() => reenviar(e.id)}
            >
              {reenviando === e.id ? "Reenviando…" : "Reenviar"}
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}
