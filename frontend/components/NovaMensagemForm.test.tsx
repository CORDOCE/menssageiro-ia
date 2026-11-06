import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type Contato, type Modelo } from "@/lib/api";
import * as api from "@/lib/api";
import { NovaMensagemForm } from "./NovaMensagemForm";

// Mantém ApiError real (instanceof no componente) e mocka só as funções de rede.
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    listarModelos: vi.fn(),
    listarContatos: vi.fn(),
    criarAgendamento: vi.fn(),
  };
});

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn() }),
}));

function modelo(p: Partial<Modelo> = {}): Modelo {
  return {
    id: "m1",
    nome: "boas_vindas",
    idioma: "pt_BR",
    categoria: "UTILITY",
    status: "aprovado",
    corpo: "Olá {{1}}",
    cabecalho_tipo: null,
    variaveis: ["1"],
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
    consentimento_data: "2026-01-01",
    consentimento_origem: "formulário",
    descadastrado_em: null,
    ultima_mensagem_recebida_em: null,
    observacoes: null,
    criado_em: null,
    atualizado_em: null,
    ...p,
  };
}

function mockarCarga(modelos: Modelo[], contatos: Contato[]) {
  vi.mocked(api.listarModelos).mockResolvedValue(modelos);
  vi.mocked(api.listarContatos).mockResolvedValue({
    items: contatos,
    total: contatos.length,
    limit: 200,
    offset: 0,
  });
}

beforeEach(() => {
  // "agora" fixo = 2026-11-06T15:00Z (12:00 em São Paulo), p/ futuro/passado determinístico.
  vi.spyOn(Date, "now").mockReturnValue(new Date("2026-11-06T15:00:00Z").getTime());
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("NovaMensagemForm — carregamento", () => {
  it("pede modelos só aprovados ao backend (AC-1)", async () => {
    mockarCarga([modelo()], [contato()]);
    render(<NovaMensagemForm />);
    await screen.findByLabelText("Modelo");
    expect(api.listarModelos).toHaveBeenCalledWith({ status: "aprovado" });
  });

  it("lista no seletor de modelo os aprovados devolvidos pelo backend (AC-1)", async () => {
    mockarCarga([modelo({ id: "a", nome: "aviso" }), modelo({ id: "b", nome: "boleto" })], [contato()]);
    render(<NovaMensagemForm />);
    const sel = (await screen.findByLabelText("Modelo")) as HTMLSelectElement;
    const nomes = within(sel).getAllByRole("option").map((o) => o.textContent);
    expect(nomes).toEqual(["Selecione um modelo…", "aviso", "boleto"]);
  });

  it("oferece só contatos elegíveis: consentimento e não descadastrado (AC-3)", async () => {
    mockarCarga(
      [modelo()],
      [
        contato({ id: "ok", nome: "Com consentimento", consentimento: true }),
        contato({ id: "sem", nome: "Sem consentimento", consentimento: false }),
        contato({ id: "desc", nome: "Descadastrado", consentimento: true, descadastrado_em: "2026-02-01" }),
      ],
    );
    render(<NovaMensagemForm />);
    const sel = (await screen.findByLabelText("Contato")) as HTMLSelectElement;
    const nomes = within(sel).getAllByRole("option").map((o) => o.textContent);
    expect(nomes.some((n) => n?.includes("Com consentimento"))).toBe(true);
    expect(nomes.some((n) => n?.includes("Sem consentimento"))).toBe(false);
    expect(nomes.some((n) => n?.includes("Descadastrado"))).toBe(false);
  });
});

describe("NovaMensagemForm — variáveis (AC-2)", () => {
  it("renderiza exatamente os campos das variáveis do modelo e a prévia do corpo", async () => {
    mockarCarga([modelo({ variaveis: ["1", "2"], corpo: "Oi {{1}}, saldo {{2}}" })], [contato()]);
    render(<NovaMensagemForm />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText("Modelo"), "m1");
    expect(screen.getByLabelText("{{1}}")).toBeInTheDocument();
    expect(screen.getByLabelText("{{2}}")).toBeInTheDocument();
    expect(screen.getByText("Oi {{1}}, saldo {{2}}")).toBeInTheDocument();
  });

  it("não renderiza campo de variável quando o modelo não tem variáveis", async () => {
    mockarCarga([modelo({ variaveis: [], corpo: "Mensagem fixa" })], [contato()]);
    render(<NovaMensagemForm />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText("Modelo"), "m1");
    expect(screen.queryByLabelText("{{1}}")).not.toBeInTheDocument();
  });

  it("recria os campos ao trocar de modelo, sem manter valores órfãos", async () => {
    mockarCarga(
      [modelo({ id: "a", nome: "a", variaveis: ["1"] }), modelo({ id: "b", nome: "b", variaveis: ["2"] })],
      [contato()],
    );
    render(<NovaMensagemForm />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText("Modelo"), "a");
    await user.type(screen.getByLabelText("{{1}}"), "valor");
    await user.selectOptions(screen.getByLabelText("Modelo"), "b");
    expect(screen.queryByLabelText("{{1}}")).not.toBeInTheDocument();
    expect((screen.getByLabelText("{{2}}") as HTMLInputElement).value).toBe("");
  });
});

describe("NovaMensagemForm — habilitação do botão (AC-5, matriz)", () => {
  async function preencherTudo() {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    render(<NovaMensagemForm />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText("Modelo"), "m1");
    await user.selectOptions(screen.getByLabelText("Contato"), "c1");
    await user.type(screen.getByLabelText("{{1}}"), "Maria");
    return user;
  }
  const botao = () => screen.getByRole("button", { name: /agendar envio/i });

  it("desabilita sem modelo", async () => {
    mockarCarga([modelo()], [contato()]);
    render(<NovaMensagemForm />);
    await screen.findByLabelText("Modelo");
    expect(botao()).toBeDisabled();
  });

  it("desabilita com variável só de espaços", async () => {
    const user = await preencherTudo();
    await user.clear(screen.getByLabelText("{{1}}"));
    await user.type(screen.getByLabelText("{{1}}"), "   ");
    await user.type(screen.getByLabelText(/quando enviar/i), "2026-12-01T12:00");
    expect(botao()).toBeDisabled();
  });

  it("desabilita com data no passado", async () => {
    const user = await preencherTudo();
    await user.type(screen.getByLabelText(/quando enviar/i), "2020-01-01T10:00");
    expect(botao()).toBeDisabled();
  });

  it("habilita com modelo, contato, variável e data futura", async () => {
    const user = await preencherTudo();
    await user.type(screen.getByLabelText(/quando enviar/i), "2026-12-01T12:00");
    expect(botao()).toBeEnabled();
  });
});

describe("NovaMensagemForm — submissão (AC-4, AC-6, AC-7)", () => {
  async function preencherValido(user = userEvent.setup()) {
    await user.selectOptions(await screen.findByLabelText("Modelo"), "m1");
    await user.selectOptions(screen.getByLabelText("Contato"), "c1");
    await user.type(screen.getByLabelText("{{1}}"), "  Maria  ");
    await user.type(screen.getByLabelText(/quando enviar/i), "2026-12-01T12:00");
    return user;
  }

  it("envia o payload correto (sem origem, variáveis trimadas, executar_em em UTC) e confirma (AC-4, AC-7)", async () => {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    vi.mocked(api.criarAgendamento).mockResolvedValue({ id: "a1" } as never);
    render(<NovaMensagemForm />);
    const user = await preencherValido();
    await user.click(screen.getByRole("button", { name: /agendar envio/i }));

    await waitFor(() => expect(api.criarAgendamento).toHaveBeenCalledTimes(1));
    expect(api.criarAgendamento).toHaveBeenCalledWith({
      contato_id: "c1",
      modelo_id: "m1",
      variaveis: ["Maria"],
      executar_em: "2026-12-01T15:00:00.000Z",
    });
    // Confirmação + caminhos "criar outra" / "voltar" (AC-7).
    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /criar outra/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ir para hoje/i })).toHaveAttribute("href", "/hoje");
  });

  it("não chama o backend quando o formulário está incompleto (AC-5)", async () => {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    render(<NovaMensagemForm />);
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByLabelText("Modelo"), "m1");
    // sem contato, sem variável, sem data
    await user.click(screen.getByRole("button", { name: /agendar envio/i }));
    expect(api.criarAgendamento).not.toHaveBeenCalled();
  });

  it("mostra erro legível e preserva o preenchimento quando o backend falha (AC-6)", async () => {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    vi.mocked(api.criarAgendamento).mockRejectedValue(new ApiError(409, "limite diário atingido"));
    render(<NovaMensagemForm />);
    const user = await preencherValido();
    await user.click(screen.getByRole("button", { name: /agendar envio/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("limite diário atingido");
    // Preenchimento mantido: ainda há o campo de variável com o valor digitado.
    expect((screen.getByLabelText("{{1}}") as HTMLInputElement).value).toBe("  Maria  ");
    expect(replace).not.toHaveBeenCalled();
  });

  it("redireciona ao login quando o backend responde 401 (AC-6)", async () => {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    vi.mocked(api.criarAgendamento).mockRejectedValue(new ApiError(401, "não autenticado"));
    render(<NovaMensagemForm />);
    const user = await preencherValido();
    await user.click(screen.getByRole("button", { name: /agendar envio/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("'criar outra' limpa o formulário (AC-7)", async () => {
    mockarCarga([modelo({ variaveis: ["1"] })], [contato()]);
    vi.mocked(api.criarAgendamento).mockResolvedValue({ id: "a1" } as never);
    render(<NovaMensagemForm />);
    const user = await preencherValido();
    await user.click(screen.getByRole("button", { name: /agendar envio/i }));
    await user.click(await screen.findByRole("button", { name: /criar outra/i }));
    // Volta ao formulário com o seletor de modelo vazio.
    expect((await screen.findByLabelText("Modelo")) as HTMLSelectElement).toHaveValue("");
  });
});

describe("NovaMensagemForm — estados vazios (bordas)", () => {
  it("sem modelos aprovados mostra orientação e não mostra seletor de modelo", async () => {
    mockarCarga([], [contato()]);
    render(<NovaMensagemForm />);
    expect(await screen.findByText(/nenhum modelo aprovado/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Modelo")).not.toBeInTheDocument();
  });

  it("sem contatos elegíveis mostra orientação com link para Contatos", async () => {
    mockarCarga([modelo()], [contato({ consentimento: false })]);
    render(<NovaMensagemForm />);
    expect(await screen.findByText(/nenhum contato com consentimento/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ir para contatos/i })).toHaveAttribute("href", "/contatos");
  });
});
