"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ListaEsqueleto } from "@/components/Esqueleto";
import {
  ApiError,
  type Configuracao,
  type ConfiguracaoPatch,
  atualizarConfiguracao,
  obterConfiguracao,
} from "@/lib/api";
import { type EstadoPush, ativarPush, suportaPush } from "@/lib/push";

// Mensagem por estado da inscrição de push (spec 0023).
const PUSH_MSG: Record<EstadoPush, string> = {
  ok: "Notificações ativadas neste dispositivo.",
  negado: "Permissão negada. Ative as notificações nas configurações do navegador.",
  indisponivel: "Este navegador não suporta push (no iPhone, instale o app na tela inicial).",
  "sem-vapid": "Notificações ainda não configuradas no servidor.",
  erro: "Falha ao ativar. Tente novamente.",
};

// Tela Configurações (spec 0018): edita os controles que o worker lê a cada ciclo (ADR 0008) —
// janela de envio, limites e pausa geral. Salvar envia o formulário inteiro (PATCH); o backend
// valida (422) e audita só o que muda. Pausar é ação sensível → confirmação explícita.

// Cap defensivo espelhando o backend (schemas/configuracao.py: _LIMITE_MAX).
const LIMITE_MAX = 100_000;

// weekday(): 0=segunda … 6=domingo (alinhado ao backend e ao JANELA_PADRAO).
const DIAS = [
  { v: 0, l: "Seg" },
  { v: 1, l: "Ter" },
  { v: 2, l: "Qua" },
  { v: 3, l: "Qui" },
  { v: 4, l: "Sex" },
  { v: 5, l: "Sáb" },
  { v: 6, l: "Dom" },
];

function numOuNull(texto: string): number | null {
  const t = texto.trim();
  return t === "" ? null : Number(t);
}

export default function ConfiguracoesPage() {
  const router = useRouter();
  const [config, setConfig] = useState<Configuracao | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);

  // Campos do formulário (derivados da config ao carregar).
  const [dias, setDias] = useState<number[]>([]);
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [limiteDiario, setLimiteDiario] = useState("");
  const [limiteContato, setLimiteContato] = useState("");
  const [limiteAgendamento, setLimiteAgendamento] = useState("");
  const [pausados, setPausados] = useState(false);

  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  // Notificações push (spec 0023): independente do formulário de envio.
  const [estadoPush, setEstadoPush] = useState<EstadoPush | null>(null);
  const [ativandoPush, setAtivandoPush] = useState(false);

  async function ativarNotificacoes() {
    setAtivandoPush(true);
    try {
      setEstadoPush(await ativarPush());
    } finally {
      setAtivandoPush(false);
    }
  }

  const preencher = useCallback((c: Configuracao) => {
    setConfig(c);
    setDias(c.janela_envio.dias);
    setInicio(c.janela_envio.inicio);
    setFim(c.janela_envio.fim);
    setLimiteDiario(String(c.limite_diario));
    setLimiteContato(c.limite_por_contato_dia === null ? "" : String(c.limite_por_contato_dia));
    setLimiteAgendamento(
      c.limite_por_agendamento_dia === null ? "" : String(c.limite_por_agendamento_dia),
    );
    setPausados(c.envios_pausados);
  }, []);

  const carregar = useCallback(() => {
    setConfig(null);
    setErroCarga(null);
    obterConfiguracao()
      .then(preencher)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErroCarga(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [preencher, router]);

  useEffect(carregar, [carregar]);

  function alternarDia(v: number) {
    setDias((atual) => (atual.includes(v) ? atual.filter((d) => d !== v) : [...atual, v].sort((a, b) => a - b)));
  }

  async function salvar() {
    setErro(null);
    setAviso(null);

    // Validação no cliente para dar erro legível (o helper pedir() não expõe o detail-lista
    // do 422 do Pydantic). O backend continua sendo a fonte da verdade.
    const limiteValido = (n: number | null) =>
      n === null || (Number.isInteger(n) && n >= 1 && n <= LIMITE_MAX);

    if (dias.length === 0) {
      setErro("Selecione ao menos um dia da janela.");
      return;
    }
    if (fim <= inicio) {
      setErro("O fim da janela deve ser maior que o início.");
      return;
    }
    const diario = numOuNull(limiteDiario);
    if (diario === null || !limiteValido(diario)) {
      setErro(`Informe o limite diário (inteiro entre 1 e ${LIMITE_MAX}).`);
      return;
    }
    const porContato = numOuNull(limiteContato);
    const porAgendamento = numOuNull(limiteAgendamento);
    if (!limiteValido(porContato) || !limiteValido(porAgendamento)) {
      setErro(`Limites opcionais: inteiro entre 1 e ${LIMITE_MAX}, ou vazio para sem limite.`);
      return;
    }
    // Confirmação ao ativar a pausa geral (ação sensível): só quando passa de ativo → pausado.
    if (pausados && config && !config.envios_pausados) {
      if (!window.confirm("Pausar TODOS os envios? Nada será disparado até retomar.")) {
        return;
      }
    }

    const patch: ConfiguracaoPatch = {
      janela_envio: { dias, inicio, fim },
      limite_diario: diario,
      limite_por_contato_dia: porContato,
      limite_por_agendamento_dia: porAgendamento,
      envios_pausados: pausados,
    };

    setSalvando(true);
    try {
      const atualizada = await atualizarConfiguracao(patch);
      preencher(atualizada);
      setAviso("Configurações salvas. O worker aplica no próximo ciclo.");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      setErro(e instanceof Error ? e.message : "Falha ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  if (config === null && !erroCarga) {
    return (
      <div>
        <h1 className="pagina-titulo">Configurações</h1>
        <ListaEsqueleto linhas={6} />
      </div>
    );
  }

  return (
    <div>
      <h1 className="pagina-titulo">Configurações</h1>
      <p className="pagina-sub">Controles de envio. Mudanças valem no próximo ciclo do worker.</p>

      {erroCarga ? <p className="erro">{erroCarga}</p> : null}

      {config ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void salvar();
          }}
        >
          <section className="painel" style={{ marginBottom: "0.75rem" }}>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={pausados}
                onChange={(e) => setPausados(e.target.checked)}
                aria-label="Pausar todos os envios"
              />
              Pausar todos os envios
            </label>
          </section>

          <section className="painel" style={{ marginBottom: "0.75rem" }}>
            <h2 className="pagina-sub" style={{ marginTop: 0 }}>Limites</h2>
            <label>
              Limite diário
              <input
                type="number"
                min={1}
                value={limiteDiario}
                onChange={(e) => setLimiteDiario(e.target.value)}
              />
            </label>
            <label>
              Limite por contato (por dia)
              <input
                type="number"
                min={1}
                placeholder="sem limite"
                value={limiteContato}
                onChange={(e) => setLimiteContato(e.target.value)}
              />
            </label>
            <label>
              Limite por disparo (por dia)
              <input
                type="number"
                min={1}
                placeholder="sem limite"
                value={limiteAgendamento}
                onChange={(e) => setLimiteAgendamento(e.target.value)}
              />
            </label>
          </section>

          <section className="painel" style={{ marginBottom: "0.75rem" }}>
            <h2 className="pagina-sub" style={{ marginTop: 0 }}>Janela de envio</h2>
            <div className="dias-semana">
              {DIAS.map((d) => (
                <label key={d.v} className="checkbox">
                  <input
                    type="checkbox"
                    checked={dias.includes(d.v)}
                    onChange={() => alternarDia(d.v)}
                    aria-label={d.l}
                  />
                  {d.l}
                </label>
              ))}
            </div>
            <label>
              Início
              <input type="time" value={inicio} onChange={(e) => setInicio(e.target.value)} />
            </label>
            <label>
              Fim
              <input type="time" value={fim} onChange={(e) => setFim(e.target.value)} />
            </label>
          </section>

          {aviso ? <p role="status" className="aviso">{aviso}</p> : null}
          {erro ? <p role="alert" className="erro">{erro}</p> : null}

          <button type="submit" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </button>
        </form>
      ) : null}

      <section className="painel" style={{ marginTop: "0.75rem" }}>
        <h2 className="pagina-sub" style={{ marginTop: 0 }}>Notificações</h2>
        <p className="texto-2" style={{ fontSize: "0.85rem", marginTop: 0 }}>
          Receba os alertas do sistema (modelo rejeitado, falhas) neste dispositivo, além do e-mail.
        </p>
        <button
          type="button"
          className="secundario"
          disabled={ativandoPush || !suportaPush()}
          onClick={() => void ativarNotificacoes()}
        >
          {ativandoPush ? "Ativando…" : "Ativar notificações"}
        </button>
        {estadoPush ? (
          <p
            role="status"
            className={estadoPush === "ok" ? "aviso" : "erro"}
            style={{ marginBottom: 0 }}
          >
            {PUSH_MSG[estadoPush]}
          </p>
        ) : null}
        {!suportaPush() ? (
          <p className="texto-2" style={{ fontSize: "0.8rem", marginBottom: 0 }}>
            {PUSH_MSG.indisponivel}
          </p>
        ) : null}
      </section>
    </div>
  );
}
