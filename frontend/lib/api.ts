// Cliente da API (FastAPI) via proxy same-origin do Next (ADR 0012): caminhos sob /api; a sessão
// vai por cookie HttpOnly, não por token em JS. Toda chamada usa credentials:"include".

const BASE = "/api";

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
    credentials: "include",
  });
  if (!r.ok) {
    const corpo: { detail?: string } = await r.json().catch(() => ({}));
    throw new Error(corpo.detail ?? "Falha no login");
  }
  return r.json() as Promise<LoginResposta>;
}

export async function me(): Promise<Usuario> {
  const r = await fetch(`${BASE}/auth/me`, { credentials: "include" });
  if (!r.ok) {
    throw new Error("Não autenticado");
  }
  return r.json() as Promise<Usuario>;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => undefined);
}

// ---- Helper autenticado (sessão via cookie; credentials:"include") -------------------------

// Erro de API que preserva o status HTTP, para o chamador diferenciar 401 (sessão expirada →
// login), 422 (validação) e demais sem reparsear a mensagem. `instanceof Error` segue valendo.
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${caminho}`, {
    ...init,
    credentials: "include",
    headers: { ...(init.headers ?? {}) },
  });
  if (!r.ok) {
    const corpo: { detail?: unknown } = await r.json().catch(() => ({}));
    const detalhe = typeof corpo.detail === "string" ? corpo.detail : `Erro ${r.status}`;
    throw new ApiError(r.status, detalhe);
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

// Payload de criação (spec 0011): contato individual + modelo + variáveis + quando enviar.
// `origem` é omitido de propósito — o backend aplica o default "operador" (schemas/agendamento.py).
// `executar_em`: ISO-8601 com offset (UTC), convertido do horário local America/Sao_Paulo.
export interface AgendamentoCriar {
  contato_id: string;
  modelo_id: string;
  variaveis: string[];
  executar_em: string;
}

export async function criarAgendamento(dados: AgendamentoCriar): Promise<Agendamento> {
  return pedirJson<Agendamento>("/agendamentos", "POST", dados);
}

// Ações de gestão (tela Agenda, spec 0012) — transições de estado no backend (§5.1: a API só
// registra/transiciona; quem envia é o worker). `cancelar`: não-terminal → cancelado.
export async function cancelarAgendamento(id: string): Promise<Agendamento> {
  return pedir<Agendamento>(`/agendamentos/${encodeURIComponent(id)}/cancelar`, { method: "POST" });
}

// `reenviar`: só vale para status `aguardando_decisao` (backend devolve 409 caso contrário).
export async function reenviarAgendamento(id: string): Promise<Agendamento> {
  return pedir<Agendamento>(`/agendamentos/${encodeURIComponent(id)}/reenviar`, { method: "POST" });
}

// `cancelar-serie`: cancela as ocorrências futuras pendentes da série; devolve quantas.
export async function cancelarSerie(id: string): Promise<{ cancelados: number }> {
  return pedir<{ cancelados: number }>(
    `/agendamentos/${encodeURIComponent(id)}/cancelar-serie`,
    { method: "POST" },
  );
}

// ---- Modelos (templates aprovados) ---------------------------------------------------------

export interface Modelo {
  id: string;
  nome: string;
  idioma: string;
  categoria: string;
  status: string;
  corpo: string;
  cabecalho_tipo: string | null;
  variaveis: string[];
}

// Lista modelos; `status: "aprovado"` filtra os que podem iniciar conversa (§5.3). O backend
// já ordena por nome.
export async function listarModelos(params: { status?: string } = {}): Promise<Modelo[]> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  const sufixo = q.toString() ? `?${q.toString()}` : "";
  return pedir<Modelo[]>(`/modelos${sufixo}`);
}

// Sincroniza os modelos com a Meta (lê templates, upsert; §5.3). Exige credenciais Meta no backend
// (staging tem; produção não até a Fase 0 → falha lá). Tela Modelos (spec 0013).
export async function sincronizarModelos(): Promise<{
  total: number;
  criados: number;
  atualizados: number;
}> {
  return pedir("/modelos/sincronizar", { method: "POST" });
}

// ---- Envios (histórico) --------------------------------------------------------------------

export interface Envio {
  id: string;
  contato_id: string;
  contato_nome: string;
  contato_telefone: string;
  modelo_id: string | null;
  modelo_nome: string | null;
  status: string;
  erro_codigo: string | null;
  erro_motivo: string | null;
  criado_em: string;
}

// Histórico de envios (spec 0014). Filtros de status e período (ISO-8601 UTC) + paginação.
// O backend já ordena por `criado_em` desc (mais recentes primeiro).
export async function listarEnvios(params: {
  status?: string;
  desde?: string;
  ate?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<Envio[]> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.desde) q.set("desde", params.desde);
  if (params.ate) q.set("ate", params.ate);
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  const sufixo = q.toString() ? `?${q.toString()}` : "";
  return pedir<Envio[]>(`/envios${sufixo}`);
}

// Reenvio manual (spec 0020): reabre um envio em `aguardando_decisao` para nova tentativa automática.
export async function reenviarEnvio(id: string): Promise<Envio> {
  return pedir<Envio>(`/envios/${encodeURIComponent(id)}/reenviar`, { method: "POST" });
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
  return pedirJson<Contato>(`/contatos/${encodeURIComponent(id)}`, "PATCH", dados);
}

export async function descadastrarContato(id: string): Promise<Contato> {
  return pedir<Contato>(`/contatos/${encodeURIComponent(id)}/descadastrar`, { method: "POST" });
}

export async function registrarConsentimento(
  id: string,
  dados: { origem: string; data: string },
): Promise<Contato> {
  return pedirJson<Contato>(`/contatos/${encodeURIComponent(id)}/consentimento`, "POST", dados);
}

export async function importarContatos(arquivo: File): Promise<RelatorioImportacao> {
  const form = new FormData();
  form.append("arquivo", arquivo);
  return pedir<RelatorioImportacao>("/contatos/importar", { method: "POST", body: form });
}

// ---- Configuração de envio (spec 0018) -----------------------------------------------------

export interface JanelaEnvio {
  dias: number[]; // 0=segunda … 6=domingo
  inicio: string; // "HH:MM"
  fim: string; // "HH:MM"
}

export interface Configuracao {
  janela_envio: JanelaEnvio;
  limite_diario: number;
  limite_por_contato_dia: number | null;
  limite_por_agendamento_dia: number | null;
  envios_pausados: boolean;
  atualizado_em: string;
}

// PATCH parcial: só os campos presentes mudam; `null` nos limites opcionais remove o limite.
export interface ConfiguracaoPatch {
  janela_envio?: JanelaEnvio;
  limite_diario?: number;
  limite_por_contato_dia?: number | null;
  limite_por_agendamento_dia?: number | null;
  envios_pausados?: boolean;
}

export async function obterConfiguracao(): Promise<Configuracao> {
  return pedir<Configuracao>("/configuracoes");
}

export async function atualizarConfiguracao(patch: ConfiguracaoPatch): Promise<Configuracao> {
  return pedirJson<Configuracao>("/configuracoes", "PATCH", patch);
}

// ---- Saúde do sistema (spec 0021 / §12) ----------------------------------------------------

export interface SaudeBanco {
  status: string; // "ok" | "erro"
}
export interface SaudeWorker {
  status: string; // "vivo" | "parado" | "desconhecido"
  ultimo_ciclo_em: string | null;
  segundos_desde: number | null;
}
export interface SaudeTaxaFalha {
  tentativas: number;
  falhas: number;
  percentual: number;
}
export interface SaudeGastoMes {
  valor: number;
  moeda: string;
  estimado: boolean;
  base: string;
}
export interface SaudeDeep {
  banco: SaudeBanco;
  worker: SaudeWorker;
  envios_hoje: Record<string, number>;
  taxa_falha_hoje: SaudeTaxaFalha;
  fila: number;
  gasto_mes_estimado: SaudeGastoMes;
}

// Retrato de saúde operacional (read-only). Token/qualidade do número da Meta ficam fora até a Fase 0.
export async function obterSaude(): Promise<SaudeDeep> {
  return pedir<SaudeDeep>("/admin/health/deep");
}

// ---- Notificações push (spec 0023 / Web Push) ----------------------------------------------

export interface ChavePush {
  chave: string | null; // VAPID public key (null = push não configurado no backend)
}
export interface InscricaoPush {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}

export async function obterChavePush(): Promise<ChavePush> {
  return pedir<ChavePush>("/push/chave-publica");
}

export async function inscreverPush(sub: InscricaoPush): Promise<void> {
  await pedirJson<{ status: string }>("/push/inscrever", "POST", sub);
}
