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

// Tela Configurações (spec 0018): edita os controles que o worker lê a cada ciclo (ADR 0008) —
// janela de envio, limites e pausa geral. Salvar envia o formulário inteiro (PATCH); o backend
// valida (422) e audita só o que muda. Pausar é ação sensível → confirmação explícita.

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

    // Validação leve no cliente; o backend é a fonte da verdade (422).
    if (dias.length === 0) {
      setErro("Selecione ao menos um dia da janela.");
      return;
    }
    if (limiteDiario.trim() === "") {
      setErro("Informe o limite diário.");
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
      limite_diario: Number(limiteDiario),
      limite_por_contato_dia: numOuNull(limiteContato),
      limite_por_agendamento_dia: numOuNull(limiteAgendamento),
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
    </div>
  );
}
