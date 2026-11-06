import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type Agendamento, type Contato } from "@/lib/api";
import * as api from "@/lib/api";
import AgendaPage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    listarAgendamentos: vi.fn(),
    listarContatos: vi.fn(),
    cancelarAgendamento: vi.fn(),
    reenviarAgendamento: vi.fn(),
    cancelarSerie: vi.fn(),
  };
});

// Router estável (como o useRouter real do Next): um objeto só, senão o useEffect de carga entraria
// em loop (carregar depende de router → recriaria a cada render).
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace, push: vi.fn(), back: vi.fn() } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function ag(p: Partial<Agendamento> = {}): Agendamento {
  return {
    id: "a1",
    contato_id: "c1",
    grupo: null,
    modelo_id: "m1",
    variaveis: [],
    executar_em: "2026-12-01T12:00:00.000Z",
    status: "aprovado",
    origem: "operador",
    recorrencia: null,
    agendamento_pai_id: null,
    reagendamentos: 0,
    motivo_ultima_transicao: null,
    criado_em: "2026-11-06T00:00:00.000Z",
    ...p,
  };
}

function contato(p: Partial<Contato> = {}): Contato {
  return {
    id: "c1",
    nome: "Maria",
    telefone_e164: "+5531999990000",
    grupo: null,
    tags: [],
    consentimento: true,
    consentimento_data: null,
    consentimento_origem: null,
    descadastrado_em: null,
    ultima_mensagem_recebida_em: null,
    observacoes: null,
    criado_em: null,
    atualizado_em: null,
    ...p,
  };
}

function mockar(ags: Agendamento[], contatos: Contato[] = [contato()]) {
  vi.mocked(api.listarAgendamentos).mockResolvedValue(ags);
  vi.mocked(api.listarContatos).mockResolvedValue({ items: contatos, total: contatos.length, limit: 200, offset: 0 });
}

beforeEach(() => {
  vi.spyOn(Date, "now").mockReturnValue(new Date("2026-11-06T15:00:00Z").getTime());
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.spyOn(window, "alert").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("AgendaPage — lista (AC-1, AC-7)", () => {
  it("lista agendamentos com destino, selo, data/hora e recorrência; ordem do backend", async () => {
    mockar([
      ag({ id: "a1", contato_id: "c1", status: "aprovado", recorrencia: "FREQ=DAILY" }),
      ag({ id: "a2", contato_id: null, grupo: "clientes", status: "enviado", recorrencia: null }),
    ]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    expect(screen.getByText("Grupo: clientes")).toBeInTheDocument();
    // selo específico (os mesmos textos existem como <option> do filtro de status)
    expect(screen.getByText("Agendada", { selector: "span.selo" })).toBeInTheDocument();
    expect(screen.getByText("Enviada", { selector: "span.selo" })).toBeInTheDocument();
    // recorrência: indicador acessível só no item recorrente
    expect(screen.getByLabelText("Recorrente")).toBeInTheDocument();
    // chamou o backend com limit 200 e sem status (Todos)
    expect(api.listarAgendamentos).toHaveBeenCalledWith({ status: undefined, limit: 200 });
  });

  it("mostra estado vazio com link para Nova mensagem quando não há itens (AC-7)", async () => {
    mockar([]);
    render(<AgendaPage />);
    const vazio = (await screen.findByText(/nenhum agendamento/i)).closest(".estado-vazio") as HTMLElement;
    expect(within(vazio).getByRole("button", { name: /nova mensagem/i })).toHaveAttribute("href", "/nova-mensagem");
  });
});

describe("AgendaPage — filtros (AC-2)", () => {
  it("refaz a busca com ?status ao trocar o filtro de status", async () => {
    mockar([ag()]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Status"), "cancelado");
    await waitFor(() =>
      expect(api.listarAgendamentos).toHaveBeenLastCalledWith({ status: "cancelado", limit: 200 }),
    );
  });

  it("filtra por período no cliente (passados oculta futuros)", async () => {
    mockar([
      ag({ id: "fut", contato_id: "c1", executar_em: "2026-12-01T12:00:00.000Z" }),
      ag({ id: "pas", contato_id: null, grupo: "antigos", executar_em: "2020-01-01T12:00:00.000Z" }),
    ]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Período"), "passados");
    expect(screen.queryByText("Maria")).not.toBeInTheDocument();
    expect(screen.getByText("Grupo: antigos")).toBeInTheDocument();
  });
});

describe("AgendaPage — ações (AC-3, AC-4, AC-5)", () => {
  it("cancela um agendamento não-terminal e recarrega (AC-3)", async () => {
    mockar([ag({ status: "aprovado" })]);
    vi.mocked(api.cancelarAgendamento).mockResolvedValue(ag({ status: "cancelado" }));
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^cancelar$/i }));
    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => expect(api.cancelarAgendamento).toHaveBeenCalledWith("a1"));
    expect(api.listarAgendamentos).toHaveBeenCalledTimes(2); // recarregou
  });

  it("não oferece Cancelar para agendamento terminal (AC-3)", async () => {
    mockar([ag({ status: "enviado" })]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    expect(screen.queryByRole("button", { name: /^cancelar$/i })).not.toBeInTheDocument();
  });

  it("Reenviar só aparece em aguardando_decisao e chama o backend (AC-4)", async () => {
    mockar([ag({ status: "aguardando_decisao" })]);
    vi.mocked(api.reenviarAgendamento).mockResolvedValue(ag({ status: "aprovado" }));
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /reenviar/i }));
    await waitFor(() => expect(api.reenviarAgendamento).toHaveBeenCalledWith("a1"));
  });

  it("não mostra Reenviar fora de aguardando_decisao", async () => {
    mockar([ag({ status: "aprovado" })]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    expect(screen.queryByRole("button", { name: /reenviar/i })).not.toBeInTheDocument();
  });

  it("Cancelar série aparece em recorrente, chama o backend e informa a contagem (AC-5)", async () => {
    mockar([ag({ recorrencia: "FREQ=WEEKLY" })]);
    vi.mocked(api.cancelarSerie).mockResolvedValue({ cancelados: 4 });
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /cancelar série/i }));
    await waitFor(() => expect(api.cancelarSerie).toHaveBeenCalledWith("a1"));
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining("4"));
  });

  it("não mostra Cancelar série em agendamento avulso", async () => {
    mockar([ag({ recorrencia: null, agendamento_pai_id: null })]);
    render(<AgendaPage />);
    await screen.findByText("Maria");
    expect(screen.queryByRole("button", { name: /cancelar série/i })).not.toBeInTheDocument();
  });
});

describe("AgendaPage — erros (AC-6)", () => {
  it("mostra alerta legível e recarrega quando a ação volta 409", async () => {
    mockar([ag({ status: "aprovado" })]);
    vi.mocked(api.cancelarAgendamento).mockRejectedValue(new ApiError(409, "Agendamento em estado terminal"));
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^cancelar$/i }));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith("Agendamento em estado terminal"));
    expect(api.listarAgendamentos).toHaveBeenCalledTimes(2);
    expect(replace).not.toHaveBeenCalled();
  });

  it("redireciona ao login quando a ação volta 401", async () => {
    mockar([ag({ status: "aprovado" })]);
    vi.mocked(api.cancelarAgendamento).mockRejectedValue(new ApiError(401, "não autenticado"));
    render(<AgendaPage />);
    await screen.findByText("Maria");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^cancelar$/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
