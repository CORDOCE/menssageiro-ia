"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EstadoVazio } from "@/components/EstadoVazio";
import { ListaEsqueleto } from "@/components/Esqueleto";
import { Selo, seloModelo } from "@/components/Selo";
import { ApiError, type Modelo, listarModelos, sincronizarModelos } from "@/lib/api";

// Tela Modelos (spec 0013): ver os templates e seus status + sincronizar com a Meta (§5.3).
// Só leitura + sincronizar; criar/submeter template fica fora (spec futura).

const STATUS_OPCOES = [
  { valor: "", texto: "Todos os status" },
  { valor: "aprovado", texto: "Aprovado" },
  { valor: "pendente", texto: "Pendente" },
  { valor: "rejeitado", texto: "Rejeitado" },
  { valor: "pausado", texto: "Pausado" },
  { valor: "rascunho", texto: "Rascunho" },
];

export default function ModelosPage() {
  const router = useRouter();
  const [modelos, setModelos] = useState<Modelo[] | null>(null);
  const [status, setStatus] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [avisoSync, setAvisoSync] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setModelos(null);
    setErro(null);
    listarModelos({ status: status || undefined })
      .then(setModelos)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [status, router]);

  useEffect(carregar, [carregar]);

  async function sincronizar() {
    setSincronizando(true);
    setAvisoSync(null);
    try {
      const r = await sincronizarModelos();
      setAvisoSync(`Sincronizado: ${r.total} total, ${r.criados} criado(s), ${r.atualizados} atualizado(s).`);
      carregar();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      window.alert(e instanceof Error ? e.message : "Falha ao sincronizar com a Meta");
    } finally {
      setSincronizando(false);
    }
  }

  return (
    <div>
      <div className="cabecalho-linha">
        <div>
          <h1 className="pagina-titulo">Modelos</h1>
          <p className="pagina-sub" style={{ margin: 0 }}>
            {modelos ? `${modelos.length} modelo(s)` : "Carregando…"}
          </p>
        </div>
        <button type="button" onClick={sincronizar} disabled={sincronizando}>
          {sincronizando ? "Sincronizando…" : "Sincronizar com a Meta"}
        </button>
      </div>

      <div className="barra-acoes" style={{ marginBottom: "1rem" }}>
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
      </div>

      {avisoSync ? <p role="status" className="aviso">{avisoSync}</p> : null}
      {erro ? <p className="erro">{erro}</p> : null}
      {modelos === null && !erro ? <ListaEsqueleto linhas={5} /> : null}

      {modelos !== null && modelos.length === 0 ? (
        <EstadoVazio mensagem="Nenhum modelo. Sincronize com a Meta para trazer os templates aprovados." />
      ) : null}

      {(modelos ?? []).map((m) => (
        <div className="painel" key={m.id} style={{ marginBottom: "0.75rem" }}>
          <div className="cabecalho-linha" style={{ marginBottom: "0.4rem" }}>
            <strong>{m.nome}</strong>
            <Selo tom={seloModelo(m.status).tom}>{seloModelo(m.status).texto}</Selo>
          </div>
          <div className="texto-2" style={{ fontSize: "0.8rem", marginBottom: "0.4rem" }}>
            {m.categoria} · {m.idioma}
            {m.cabecalho_tipo ? ` · cabeçalho: ${m.cabecalho_tipo}` : ""}
          </div>
          {/* Corpo como texto puro (§6): React escapa — sem HTML/markdown interpretado. */}
          <p className="texto-2" style={{ whiteSpace: "pre-wrap", margin: "0 0 0.4rem" }}>
            {m.corpo}
          </p>
          <div className="texto-3" style={{ fontSize: "0.78rem" }}>
            {m.variaveis.length > 0 ? `Variáveis: ${m.variaveis.map((v) => `{{${v}}}`).join(", ")}` : "Sem variáveis"}
          </div>
        </div>
      ))}
    </div>
  );
}
