"use client";

import { type FormEvent, useEffect, useState } from "react";

import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaEsqueleto } from "@/components/Esqueleto";
import { Selo } from "@/components/Selo";
import {
  type Contato,
  type ContatoEntrada,
  atualizarContato,
  criarContato,
  descadastrarContato,
  importarContatos,
  listarContatos,
  registrarConsentimento,
  type RelatorioImportacao,
} from "@/lib/api";

function SeloConsentimento({ c }: { c: Contato }) {
  if (c.descadastrado_em) return <Selo tom="neutro">Descadastrado</Selo>;
  return c.consentimento ? (
    <Selo tom="entregue">Com consentimento</Selo>
  ) : (
    <Selo tom="aguardando">Sem consentimento</Selo>
  );
}

export default function ContatosPage() {
  const [contatos, setContatos] = useState<Contato[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState<Contato | "novo" | null>(null);
  const [consentindo, setConsentindo] = useState<Contato | null>(null);
  const [importando, setImportando] = useState(false);

  function recarregar() {
    setContatos(null);
    listarContatos({ limit: 200 })
      .then((r) => setContatos(r.items))
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Falha ao carregar"));
  }

  useEffect(recarregar, []);

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Contatos</h1>
          <p className="pagina-sub" style={{ margin: 0 }}>
            {contatos ? `${contatos.length} na lista` : "Carregando…"}
          </p>
        </div>
        <div className="barra-acoes">
          <button type="button" className="secundario" onClick={() => setImportando(true)}>
            Importar
          </button>
          <button type="button" onClick={() => setEditando("novo")}>
            Novo contato
          </button>
        </div>
      </div>

      {erro ? <p className="erro">{erro}</p> : null}
      {contatos === null && !erro ? <ListaEsqueleto linhas={6} /> : null}
      {contatos !== null && contatos.length === 0 ? (
        <EstadoVazio mensagem="Nenhum contato ainda. Crie ou importe sua base." />
      ) : null}

      {contatos !== null && contatos.length > 0 ? (
        <>
          {/* Desktop: tabela */}
          <div className="painel so-desktop" style={{ padding: 0 }}>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Telefone</th>
                  <th>Grupo</th>
                  <th>Situação</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {contatos.map((c) => (
                  <tr key={c.id}>
                    <td>{c.nome}</td>
                    <td className="tabular">{c.telefone_e164}</td>
                    <td className="texto-2">{c.grupo ?? "—"}</td>
                    <td>
                      <SeloConsentimento c={c} />
                    </td>
                    <td>
                      <AcoesContato
                        c={c}
                        onEditar={() => setEditando(c)}
                        onConsentir={() => setConsentindo(c)}
                        onRecarregar={recarregar}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Celular: cartões */}
          <div className="lista-cartoes so-mobile">
            {contatos.map((c) => (
              <div className="contato-cartao" key={c.id}>
                <strong>{c.nome}</strong>
                <span className="texto-2 tabular">{c.telefone_e164}</span>
                <div className="selos">
                  <SeloConsentimento c={c} />
                  {c.grupo ? <Selo tom="agendada">{c.grupo}</Selo> : null}
                </div>
                <AcoesContato
                  c={c}
                  onEditar={() => setEditando(c)}
                  onConsentir={() => setConsentindo(c)}
                  onRecarregar={recarregar}
                />
              </div>
            ))}
          </div>
        </>
      ) : null}

      {editando ? (
        <DialogoContato
          contato={editando === "novo" ? null : editando}
          onFechar={() => setEditando(null)}
          onSalvo={() => {
            setEditando(null);
            recarregar();
          }}
        />
      ) : null}

      {consentindo ? (
        <DialogoConsentimento
          contato={consentindo}
          onFechar={() => setConsentindo(null)}
          onSalvo={() => {
            setConsentindo(null);
            recarregar();
          }}
        />
      ) : null}

      {importando ? (
        <DialogoImportar
          onFechar={() => setImportando(false)}
          onImportado={() => recarregar()}
        />
      ) : null}
    </div>
  );
}

function AcoesContato({
  c,
  onEditar,
  onConsentir,
  onRecarregar,
}: {
  c: Contato;
  onEditar: () => void;
  onConsentir: () => void;
  onRecarregar: () => void;
}) {
  const [ocupado, setOcupado] = useState(false);

  async function descadastrar() {
    if (!window.confirm(`Descadastrar ${c.nome}? Ele não receberá mais mensagens.`)) return;
    setOcupado(true);
    try {
      await descadastrarContato(c.id);
      onRecarregar();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Falha");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="barra-acoes">
      <button type="button" className="fantasma" onClick={onEditar} disabled={ocupado}>
        Editar
      </button>
      {!c.consentimento && !c.descadastrado_em ? (
        <button type="button" className="fantasma" onClick={onConsentir} disabled={ocupado}>
          Consentimento
        </button>
      ) : null}
      {!c.descadastrado_em ? (
        <button type="button" className="fantasma" onClick={descadastrar} disabled={ocupado}>
          Descadastrar
        </button>
      ) : null}
    </div>
  );
}

function DialogoContato({
  contato,
  onFechar,
  onSalvo,
}: {
  contato: Contato | null;
  onFechar: () => void;
  onSalvo: () => void;
}) {
  const [nome, setNome] = useState(contato?.nome ?? "");
  const [telefone, setTelefone] = useState(contato?.telefone_e164 ?? "");
  const [grupo, setGrupo] = useState(contato?.grupo ?? "");
  const [observacoes, setObservacoes] = useState(contato?.observacoes ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    const dados: ContatoEntrada = {
      nome,
      telefone,
      grupo: grupo || null,
      observacoes: observacoes || null,
    };
    try {
      if (contato) {
        await atualizarContato(contato.id, dados);
      } else {
        await criarContato(dados);
      }
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Overlay onFechar={onFechar}>
      <form className="dialogo" onSubmit={enviar}>
        <h2>{contato ? "Editar contato" : "Novo contato"}</h2>
        <label>
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required />
        </label>
        <label>
          Telefone
          <input
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder="+55 31 99999-9999"
            required
          />
        </label>
        <label>
          Grupo (opcional)
          <input value={grupo} onChange={(e) => setGrupo(e.target.value)} />
        </label>
        <label>
          Observações (opcional)
          <textarea value={observacoes} onChange={(e) => setObservacoes(e.target.value)} rows={2} />
        </label>
        {erro ? (
          <p role="alert" className="erro">
            {erro}
          </p>
        ) : null}
        <div className="dialogo-acoes">
          <button type="button" className="secundario" onClick={onFechar} disabled={salvando}>
            Cancelar
          </button>
          <button type="submit" disabled={salvando}>
            {salvando ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </form>
    </Overlay>
  );
}

function DialogoConsentimento({
  contato,
  onFechar,
  onSalvo,
}: {
  contato: Contato;
  onFechar: () => void;
  onSalvo: () => void;
}) {
  const [origem, setOrigem] = useState("");
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await registrarConsentimento(contato.id, { origem, data });
      onSalvo();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao registrar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Overlay onFechar={onFechar}>
      <form className="dialogo" onSubmit={enviar}>
        <h2>Registrar consentimento</h2>
        <p className="texto-2" style={{ margin: 0, fontSize: "0.85rem" }}>
          {contato.nome} — informe de onde veio o opt-in e a data.
        </p>
        <label>
          Origem
          <input
            value={origem}
            onChange={(e) => setOrigem(e.target.value)}
            placeholder="Ex.: formulário do site"
            required
          />
        </label>
        <label>
          Data
          <input type="date" value={data} onChange={(e) => setData(e.target.value)} required />
        </label>
        {erro ? (
          <p role="alert" className="erro">
            {erro}
          </p>
        ) : null}
        <div className="dialogo-acoes">
          <button type="button" className="secundario" onClick={onFechar} disabled={salvando}>
            Cancelar
          </button>
          <button type="submit" disabled={salvando}>
            {salvando ? "Salvando…" : "Registrar"}
          </button>
        </div>
      </form>
    </Overlay>
  );
}

function DialogoImportar({
  onFechar,
  onImportado,
}: {
  onFechar: () => void;
  onImportado: () => void;
}) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [relatorio, setRelatorio] = useState<RelatorioImportacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!arquivo) return;
    setErro(null);
    setEnviando(true);
    try {
      const r = await importarContatos(arquivo);
      setRelatorio(r);
      onImportado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha ao importar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Overlay onFechar={onFechar}>
      <form className="dialogo" onSubmit={enviar}>
        <h2>Importar contatos</h2>
        <p className="texto-2" style={{ margin: 0, fontSize: "0.85rem" }}>
          Envie um CSV ou XLSX. A importação não concede consentimento automático.
        </p>
        <input
          type="file"
          accept=".csv,.xlsx"
          onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
        />
        {erro ? (
          <p role="alert" className="erro">
            {erro}
          </p>
        ) : null}
        {relatorio ? (
          <div className="painel" style={{ fontSize: "0.9rem" }}>
            <strong>Resultado</strong>
            <div className="texto-2">
              Total {relatorio.total} · Criados {relatorio.criados} · Atualizados{" "}
              {relatorio.atualizados} · Ignorados {relatorio.ignorados} · Erros {relatorio.erros}
            </div>
          </div>
        ) : null}
        <div className="dialogo-acoes">
          <button type="button" className="secundario" onClick={onFechar} disabled={enviando}>
            {relatorio ? "Fechar" : "Cancelar"}
          </button>
          {!relatorio ? (
            <button type="submit" disabled={enviando || !arquivo}>
              {enviando ? "Importando…" : "Importar"}
            </button>
          ) : null}
        </div>
      </form>
    </Overlay>
  );
}

function Overlay({ children, onFechar }: { children: React.ReactNode; onFechar: () => void }) {
  return (
    <div
      className="overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onFechar();
      }}
    >
      {children}
    </div>
  );
}
