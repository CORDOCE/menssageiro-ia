"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  type Contato,
  type Modelo,
  criarAgendamento,
  enviarAnexo,
  listarContatos,
  listarModelos,
} from "@/lib/api";
import { saoPauloParaIso } from "@/lib/datas";

import { EstadoVazio } from "./EstadoVazio";
import { ListaEsqueleto } from "./Esqueleto";

// Tela Nova mensagem (spec 0011): escolher modelo aprovado + contato elegível, preencher as
// variáveis do template, definir quando enviar (horário de São Paulo) e gravar via POST
// /agendamentos. Só contato individual, só envio único (ver Fora de escopo da spec).
export function NovaMensagemForm() {
  const router = useRouter();

  const [modelos, setModelos] = useState<Modelo[] | null>(null);
  const [contatos, setContatos] = useState<Contato[] | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);

  const [modeloId, setModeloId] = useState("");
  const [valores, setValores] = useState<Record<string, string>>({});
  const [contatoId, setContatoId] = useState("");
  const [quando, setQuando] = useState("");
  const [anexo, setAnexo] = useState<File | null>(null); // PDF, quando o modelo é DOCUMENT (spec 0024)

  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    Promise.all([listarModelos({ status: "aprovado" }), listarContatos({ status: "ativo", limit: 200 })])
      .then(([ms, cs]) => {
        setModelos(ms);
        // Elegível (spec S4): consentimento registrado e não descadastrado. O backend já exclui
        // descadastrados com status=ativo; o consentimento é filtrado aqui (não há filtro no GET).
        setContatos(cs.items.filter((c) => c.consentimento && !c.descadastrado_em));
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErroCarga(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [router]);

  const modelo = useMemo(
    () => modelos?.find((m) => m.id === modeloId) ?? null,
    [modelos, modeloId],
  );

  // O modelo exige anexo PDF quando tem cabeçalho DOCUMENT (spec 0024).
  const exigeAnexo = modelo?.cabecalho_tipo === "DOCUMENT";

  // Troca de modelo recria os campos de variável: descarta valores do template anterior (sem órfãos).
  function escolherModelo(id: string) {
    setModeloId(id);
    setValores({});
    setAnexo(null);
  }

  const variaveisPreenchidas = modelo
    ? modelo.variaveis.every((n) => (valores[n] ?? "").trim() !== "")
    : false;

  const dataFutura = (() => {
    if (!quando) return false;
    try {
      return new Date(saoPauloParaIso(quando)).getTime() > Date.now();
    } catch {
      return false;
    }
  })();

  const podeEnviar =
    modeloId !== "" &&
    contatoId !== "" &&
    variaveisPreenchidas &&
    dataFutura &&
    (!exigeAnexo || anexo !== null) &&
    !enviando;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!podeEnviar || !modelo) return;
    setErroEnvio(null);
    setEnviando(true);
    try {
      // Modelo com cabeçalho DOCUMENT: sobe o PDF primeiro e vincula pelo id (spec 0024).
      let anexoId: string | undefined;
      if (exigeAnexo && anexo) {
        anexoId = (await enviarAnexo(anexo)).id;
      }
      await criarAgendamento({
        contato_id: contatoId,
        modelo_id: modelo.id,
        variaveis: modelo.variaveis.map((n) => (valores[n] ?? "").trim()),
        executar_em: saoPauloParaIso(quando),
        anexo_id: anexoId,
      });
      setSucesso(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      // Mensagem do backend (detail), sem stack/PII. O preenchimento é mantido (AC-6).
      setErroEnvio(err instanceof Error ? err.message : "Falha ao agendar");
    } finally {
      setEnviando(false);
    }
  }

  function criarOutra() {
    setModeloId("");
    setValores({});
    setContatoId("");
    setQuando("");
    setAnexo(null);
    setErroEnvio(null);
    setSucesso(false);
  }

  if (erroCarga) return <p role="alert" className="erro">{erroCarga}</p>;
  if (modelos === null || contatos === null) return <ListaEsqueleto linhas={5} />;

  if (sucesso) {
    return (
      <div>
        <h1 className="pagina-titulo">Mensagem agendada</h1>
        <p role="status" className="pagina-sub">
          O agendamento foi criado. O envio acontece no horário escolhido.
        </p>
        <div className="barra-acoes">
          <button type="button" onClick={criarOutra}>
            Criar outra
          </button>
          <Link className="secundario" href="/hoje" role="button">
            Ir para Hoje
          </Link>
        </div>
      </div>
    );
  }

  const semModelos = modelos.length === 0;
  const semContatos = contatos.length === 0;

  return (
    <div>
      <h1 className="pagina-titulo">Nova mensagem</h1>
      <p className="pagina-sub">Agende o envio de um modelo aprovado para um contato.</p>

      <form onSubmit={enviar} className="painel" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {semModelos ? (
          <EstadoVazio
            mensagem="Nenhum modelo aprovado disponível. Sincronize e aprove modelos na Meta antes de agendar."
          />
        ) : (
          <label>
            Modelo
            <select value={modeloId} onChange={(e) => escolherModelo(e.target.value)}>
              <option value="">Selecione um modelo…</option>
              {modelos.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nome}
                </option>
              ))}
            </select>
          </label>
        )}

        {modelo ? (
          <div className="previa">
            <span className="aviso">Prévia do texto</span>
            {/* Texto do template renderizado como texto puro (§6): React escapa — sem HTML/markdown. */}
            <p className="texto-2" style={{ whiteSpace: "pre-wrap", margin: "0.3rem 0 0" }}>
              {modelo.corpo}
            </p>
          </div>
        ) : null}

        {modelo && modelo.variaveis.length > 0 ? (
          <fieldset style={{ border: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.7rem" }}>
            <legend className="aviso" style={{ padding: 0 }}>
              Variáveis do template
            </legend>
            {modelo.variaveis.map((n) => (
              <label key={n}>
                {`{{${n}}}`}
                <input
                  value={valores[n] ?? ""}
                  onChange={(e) => setValores((v) => ({ ...v, [n]: e.target.value }))}
                />
              </label>
            ))}
          </fieldset>
        ) : null}

        {exigeAnexo ? (
          <label>
            Boleto (PDF)
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setAnexo(e.target.files?.[0] ?? null)}
            />
            <span className="aviso">Este modelo exige um PDF no cabeçalho.</span>
            {anexo ? (
              <span className="texto-2" style={{ fontSize: "0.8rem" }}>
                {anexo.name}
              </span>
            ) : null}
          </label>
        ) : null}

        {semContatos ? (
          <EstadoVazio
            mensagem="Nenhum contato com consentimento. Registre o consentimento para poder enviar."
            acao={
              <Link className="secundario" href="/contatos" role="button">
                Ir para Contatos
              </Link>
            }
          />
        ) : (
          <label>
            Contato
            <select value={contatoId} onChange={(e) => setContatoId(e.target.value)}>
              <option value="">Selecione um contato…</option>
              {contatos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome} — {c.telefone_e164}
                </option>
              ))}
            </select>
          </label>
        )}

        <label>
          Quando enviar (horário de Brasília)
          <input type="datetime-local" value={quando} onChange={(e) => setQuando(e.target.value)} />
          {quando && !dataFutura ? <span className="aviso erro">A data e hora precisam ser futuras.</span> : null}
        </label>

        {erroEnvio ? (
          <p role="alert" className="erro">
            {erroEnvio}
          </p>
        ) : null}

        <div className="dialogo-acoes">
          <button type="submit" disabled={!podeEnviar}>
            {enviando ? "Agendando…" : "Agendar envio"}
          </button>
        </div>
      </form>
    </div>
  );
}
