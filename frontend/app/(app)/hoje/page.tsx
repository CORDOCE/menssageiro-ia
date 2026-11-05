"use client";

import { useEffect, useState } from "react";

import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaEsqueleto } from "@/components/Esqueleto";
import { IconeRecorrencia } from "@/components/icones";
import { Selo, seloAgendamento } from "@/components/Selo";
import { type Agendamento, listarAgendamentos, listarContatos } from "@/lib/api";

const TZ = "America/Sao_Paulo";
const LIMITE_LISTA = 8;

const fmtDiaMes = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, day: "2-digit", month: "2-digit" });
const fmtDiaMesAno = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TZ,
  day: "2-digit",
  month: "2-digit",
  year: "2-digit",
});
const fmtHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TZ,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const fmtAno = new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, year: "numeric" });
const fmtExtenso = new Intl.DateTimeFormat("pt-BR", {
  timeZone: TZ,
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});

function dataHora(iso: string): { dia: string; hora: string } {
  const d = new Date(iso);
  const mesmoAno = fmtAno.format(d) === fmtAno.format(new Date());
  return { dia: (mesmoAno ? fmtDiaMes : fmtDiaMesAno).format(d), hora: fmtHora.format(d) };
}

export default function HojePage() {
  const [itens, setItens] = useState<Agendamento[] | null>(null);
  const [nomes, setNomes] = useState<Map<string, string>>(new Map());
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const agora = Date.now();
    Promise.all([listarAgendamentos({ status: "aprovado", limit: 200 }), listarContatos({ limit: 200 })])
      .then(([ags, contatos]) => {
        setNomes(new Map(contatos.items.map((c) => [c.id, c.nome])));
        const futuros = ags
          .filter((a) => new Date(a.executar_em).getTime() > agora)
          .sort((a, b) => a.executar_em.localeCompare(b.executar_em));
        setItens(futuros);
      })
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Falha ao carregar"));
  }, []);

  const programadas = itens?.length ?? 0;
  const hojeExtenso = fmtExtenso.format(new Date());

  function destino(a: Agendamento): string {
    if (a.grupo) return `Grupo: ${a.grupo}`;
    return (a.contato_id && nomes.get(a.contato_id)) || "Contato";
  }

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Hoje</h1>
          <p className="pagina-sub" style={{ textTransform: "capitalize", margin: 0 }}>
            {hojeExtenso}
          </p>
        </div>
        <Selo tom="entregue">Sistema ok</Selo>
      </div>

      <div className="grade-indicadores">
        <div className="painel indicador">
          <div className="rotulo">Programadas</div>
          <div className="valor tabular">{itens === null ? "—" : programadas}</div>
        </div>
        <div className="painel indicador">
          <div className="rotulo">Entregues no mês</div>
          <div className="valor texto-3">—</div>
        </div>
        <div className="painel indicador">
          <div className="rotulo">Não enviadas</div>
          <div className="valor texto-3">—</div>
        </div>
        <div className="painel indicador">
          <div className="rotulo">Gasto no mês</div>
          <div className="valor texto-3">—</div>
        </div>
      </div>

      <div className="painel">
        <h2 className="pagina-titulo" style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
          Envios programados
        </h2>

        {erro ? <p className="erro">{erro}</p> : null}

        {itens === null && !erro ? <ListaEsqueleto linhas={5} /> : null}

        {itens !== null && itens.length === 0 ? (
          <EstadoVazio mensagem="Nenhum envio programado. Programe sua próxima mensagem." />
        ) : null}

        {itens !== null && itens.length > 0
          ? itens.slice(0, LIMITE_LISTA).map((a) => {
              const { dia, hora } = dataHora(a.executar_em);
              const s = seloAgendamento(a.status);
              return (
                <div className="linha-item" key={a.id}>
                  <div className="data-hora tabular">
                    <div className="dia">{dia}</div>
                    <div className="hora">{hora}</div>
                  </div>
                  <div className="item-corpo">
                    <div className="nome">
                      {a.recorrencia ? <IconeRecorrencia aria-label="Recorrente" /> : null}
                      {destino(a)}
                    </div>
                    <div className="meta">{a.recorrencia ? "Recorrente" : "Avulso"}</div>
                  </div>
                  <Selo tom={s.tom}>{s.texto}</Selo>
                </div>
              );
            })
          : null}

        {itens !== null && itens.length > LIMITE_LISTA ? (
          <div className="rodape-lista">Ver todos na agenda ({itens.length})</div>
        ) : null}
      </div>
    </div>
  );
}
