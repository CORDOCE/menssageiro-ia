// Cliente da API do backend (FastAPI). Base em NEXT_PUBLIC_API_URL (definida na Railway).
import { lerToken } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface LoginResposta {
  token: string;
  nome: string;
  email: string;
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  ativo: boolean;
}

export async function login(email: string, senha: string, totp: string): Promise<LoginResposta> {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha, totp }),
  });
  if (!r.ok) {
    const corpo: { detail?: string } = await r.json().catch(() => ({}));
    throw new Error(corpo.detail ?? "Falha no login");
  }
  return r.json() as Promise<LoginResposta>;
}

export async function me(): Promise<Usuario> {
  const r = await fetch(`${BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${lerToken() ?? ""}` },
  });
  if (!r.ok) {
    throw new Error("Não autenticado");
  }
  return r.json() as Promise<Usuario>;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${lerToken() ?? ""}` },
  }).catch(() => undefined);
}

// ---- Helper autenticado --------------------------------------------------------------------

function autorizacao(): Record<string, string> {
  return { Authorization: `Bearer ${lerToken() ?? ""}` };
}

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${caminho}`, {
    ...init,
    headers: { ...autorizacao(), ...(init.headers ?? {}) },
  });
  if (!r.ok) {
    const corpo: { detail?: unknown } = await r.json().catch(() => ({}));
    const detalhe = typeof corpo.detail === "string" ? corpo.detail : `Erro ${r.status}`;
    throw new Error(detalhe);
  }
  return r.json() as Promise<T>;
}

async function pedirJson<T>(caminho: string, metodo: string, corpo: unknown): Promise<T> {
  return pedir<T>(caminho, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
}

// ---- Agendamentos --------------------------------------------------------------------------

export interface Agendamento {
  id: string;
  contato_id: string | null;
  grupo: string | null;
  modelo_id: string;
  variaveis: string[];
  executar_em: string;
  status: string;
  origem: string;
  recorrencia: string | null;
  agendamento_pai_id: string | null;
  reagendamentos: number;
  motivo_ultima_transicao: string | null;
  criado_em: string;
}

export async function listarAgendamentos(params: {
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<Agendamento[]> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  const sufixo = q.toString() ? `?${q.toString()}` : "";
  return pedir<Agendamento[]>(`/agendamentos${sufixo}`);
}

// ---- Contatos ------------------------------------------------------------------------------

export interface Contato {
  id: string;
  nome: string;
  telefone_e164: string;
  grupo: string | null;
  tags: string[];
  consentimento: boolean;
  consentimento_data: string | null;
  consentimento_origem: string | null;
  descadastrado_em: string | null;
  ultima_mensagem_recebida_em: string | null;
  observacoes: string | null;
  criado_em: string | null;
  atualizado_em: string | null;
}

export interface ContatoLista {
  items: Contato[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContatoEntrada {
  nome: string;
  telefone: string;
  grupo?: string | null;
  observacoes?: string | null;
}

export interface ResultadoLinha {
  linha: number;
  status: "criado" | "atualizado" | "ignorado" | "erro";
  telefone: string | null;
  motivo: string | null;
}

export interface RelatorioImportacao {
  total: number;
  criados: number;
  atualizados: number;
  ignorados: number;
  erros: number;
  linhas: ResultadoLinha[];
}

export async function listarContatos(params: {
  status?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ContatoLista> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  const sufixo = q.toString() ? `?${q.toString()}` : "";
  return pedir<ContatoLista>(`/contatos${sufixo}`);
}

export async function criarContato(dados: ContatoEntrada): Promise<Contato> {
  return pedirJson<Contato>("/contatos", "POST", dados);
}

export async function atualizarContato(id: string, dados: Partial<ContatoEntrada>): Promise<Contato> {
  return pedirJson<Contato>(`/contatos/${id}`, "PATCH", dados);
}

export async function descadastrarContato(id: string): Promise<Contato> {
  return pedir<Contato>(`/contatos/${id}/descadastrar`, { method: "POST" });
}

export async function registrarConsentimento(
  id: string,
  dados: { origem: string; data: string },
): Promise<Contato> {
  return pedirJson<Contato>(`/contatos/${id}/consentimento`, "POST", dados);
}

export async function importarContatos(arquivo: File): Promise<RelatorioImportacao> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return pedir<RelatorioImportacao>("/contatos/importar", { method: "POST", body: form });
}
