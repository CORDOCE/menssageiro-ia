"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaEsqueleto } from "@/components/Esqueleto";
import { IconeRecorrencia } from "@/components/icones";
import { Selo, seloAgendamento } from "@/components/Selo";
import {
  ApiError,
  type Agendamento,
  cancelarAgendamento,
  cancelarSerie,
  listarAgendamentos,
  listarContatos,
  reenviarAgendamento,
} from "@/lib/api";

// Tela Agenda (spec 0012): gestão dos agendamentos — listar/filtrar e agir (cancelar, reenviar,
// cancelar série). Usa só endpoints existentes; quem envia é o worker (§5.1).

const TZ = "America/Sao_Paulo";
const fmtData = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "2-digit" });
const fmtHora = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });

type Periodo = "todos" | "futuros" | "passados";

const STATUS_OPCOES = [
  { valor: "", texto: "Todos os status" },
  { valor: "aprovado", texto: "Agendada" },
  { valor: "enviado", texto: "Enviada" },
  { valor: "entregue", texto: "Entregue" },
  { valor: "aguardando_decisao", texto: "Aguardando" },
  { valor: "falhou", texto: "Não enviada" },
  { valor: "cancelado", texto: "Cancelada" },
];

const TERMINAIS = new Set(["enviado", "cancelado"]);

export default function AgendaPage() {
  const router = useRouter();
  const [itens, setItens] = useState<Agendamento[] | null>(null);
  const [nomes, setNomes] = useState<Map<string, string>>(new Map());
  const [status, setStatus] = useState("");
  const [periodo, setPeriodo] = useState<Periodo>("todos");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupadoId, setOcupadoId] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setItens(null);
    setErro(null);
    Promise.all([
      listarAgendamentos({ status: status || undefined, limit: 200 }),
      listarContatos({ limit: 200 }),
    ])
      .then(([ags, contatos]) => {
        setNomes(new Map(contatos.items.map((c) => [c.id, c.nome])));
        setItens(ags);
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [status, router]);

  useEffect(carregar, [carregar]);

  function destino(a: Agendamento): string {
    if (a.grupo) return `Grupo: ${a.grupo}`;
    return (a.contato_id && nomes.get(a.contato_id)) || "Contato";
  }

  // Período é filtrado no cliente (o GET não filtra por data).
  const agora = Date.now();
  const visiveis = (itens ?? []).filter((a) => {
    if (periodo === "todos") return true;
    const futuro = new Date(a.executar_em).getTime() > agora;
    return periodo === "futuros" ? futuro : !futuro;
  });

  // Executa uma ação de transição, com guarda de duplo clique, confirmação e tratamento de erro
  // no padrão da tela Contatos (window.alert). 401 → login; demais → mensagem + recarrega a lista.
  async function agir(id: string, acao: () => Promise<unknown>, confirmar: string | null) {
    if (confirmar !== null && !window.confirm(confirmar)) return;
    setOcupadoId(id);
    try {
      await acao();
      carregar();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      window.alert(e instanceof Error ? e.message : "Falha na ação");
      carregar();
    } finally {
      setOcupadoId(null);
    }
  }

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Agenda</h1>
          <p className="pagina-sub" style={{ margin: 0 }}>
            {itens ? `${visiveis.length} agendamento(s)` : "Carregando…"}
          </p>
        </div>
        <Link href="/nova-mensagem" role="button">
          Nova mensagem
        </Link>
      </div>

      <div className="barra-acoes" style={{ marginBottom: "1rem", gap: "0.5rem" }}>
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
          Período
          <select value={periodo} onChange={(e) => setPeriodo(e.target.value as Periodo)}>
            <option value="todos">Todos</option>
            <option value="futuros">Futuros</option>
            <option value="passados">Passados</option>
          </select>
        </label>
      </div>

      {erro ? <p className="erro">{erro}</p> : null}
      {itens === null && !erro ? <ListaEsqueleto linhas={6} /> : null}

      {itens !== null && visiveis.length === 0 ? (
        <EstadoVazio
          mensagem="Nenhum agendamento neste filtro."
          acao={
            <Link className="secundario" href="/nova-mensagem" role="button">
              Nova mensagem
            </Link>
          }
        />
      ) : null}

      {visiveis.map((a) => {
        const s = seloAgendamento(a.status);
        const emSerie = a.recorrencia !== null || a.agendamento_pai_id !== null;
        const ocupado = ocupadoId === a.id;
        return (
          <div className="linha-item" key={a.id}>
            <div className="data-hora tabular">
              <div className="dia">{fmtData.format(new Date(a.executar_em))}</div>
              <div className="hora">{fmtHora.format(new Date(a.executar_em))}</div>
            </div>
            <div className="item-corpo">
              <div className="nome">
                {emSerie ? <IconeRecorrencia aria-label="Recorrente" /> : null}
                {destino(a)}
              </div>
              <div className="meta">{emSerie ? "Recorrente" : "Avulso"}</div>
            </div>
            <Selo tom={s.tom}>{s.texto}</Selo>
            <div className="barra-acoes">
              {!TERMINAIS.has(a.status) ? (
                <button
                  type="button"
                  className="fantasma"
                  disabled={ocupado}
                  onClick={() =>
                    agir(a.id, () => cancelarAgendamento(a.id), `Cancelar o envio para ${destino(a)}?`)
                  }
                >
                  Cancelar
                </button>
              ) : null}
              {a.status === "aguardando_decisao" ? (
                <button
                  type="button"
                  className="fantasma"
                  disabled={ocupado}
                  onClick={() => agir(a.id, () => reenviarAgendamento(a.id), null)}
                >
                  Reenviar
                </button>
              ) : null}
              {emSerie ? (
                <button
                  type="button"
                  className="fantasma"
                  disabled={ocupado}
                  onClick={() =>
                    agir(
                      a.id,
                      async () => {
                        const r = await cancelarSerie(a.id);
                        window.alert(`${r.cancelados} ocorrência(s) futura(s) cancelada(s).`);
                      },
                      "Cancelar todas as ocorrências futuras desta série?",
                    )
                  }
                >
                  Cancelar série
                </button>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
