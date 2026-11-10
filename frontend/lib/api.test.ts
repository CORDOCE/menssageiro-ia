import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  type AgendamentoCriar,
  type Configuracao,
  type Modelo,
  atualizarConfiguracao,
  cancelarAgendamento,
  cancelarSerie,
  criarAgendamento,
  listarModelos,
  obterConfiguracao,
  reenviarAgendamento,
  sincronizarModelos,
} from "./api";

function resposta(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("listarModelos", () => {
  it("chama GET /api/modelos?status=aprovado com credenciais e devolve a lista (AC-1)", async () => {
    const modelos: Modelo[] = [
      {
        id: "m1",
        nome: "boas_vindas",
        idioma: "pt_BR",
        categoria: "UTILITY",
        status: "aprovado",
        corpo: "Olá {{1}}",
        cabecalho_tipo: null,
        variaveis: ["1"],
      },
    ];
    const fetchMock = vi.fn().mockResolvedValue(resposta(modelos));
    vi.stubGlobal("fetch", fetchMock);

    const r = await listarModelos({ status: "aprovado" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/modelos?status=aprovado",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(r).toEqual(modelos);
  });
});

describe("criarAgendamento", () => {
  it("faz POST /api/agendamentos com o payload sem `origem` e devolve o criado (AC-4)", async () => {
    const dados: AgendamentoCriar = {
      contato_id: "c1",
      modelo_id: "m1",
      variaveis: ["João"],
      executar_em: "2026-12-01T12:00:00-03:00",
    };
    const fetchMock = vi.fn().mockResolvedValue(resposta({ id: "a1", ...dados }, 201));
    vi.stubGlobal("fetch", fetchMock);

    const r = await criarAgendamento(dados);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/agendamentos");
    expect(init.method).toBe("POST");
    const corpo = JSON.parse(init.body as string);
    expect(corpo).toEqual(dados);
    expect(corpo).not.toHaveProperty("origem");
    expect(r).toMatchObject({ id: "a1" });
  });

  it("lança ApiError com o status HTTP quando o backend responde erro (AC-6)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ detail: "dados inválidos" }, 422));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      criarAgendamento({ contato_id: "c1", modelo_id: "m1", variaveis: [], executar_em: "x" }),
    ).rejects.toMatchObject({ status: 422, message: "dados inválidos" });

    const erro = await criarAgendamento({
      contato_id: "c1",
      modelo_id: "m1",
      variaveis: [],
      executar_em: "x",
    }).catch((e) => e);
    expect(erro).toBeInstanceOf(ApiError);
  });
});

describe("ações de agendamento (Agenda, spec 0012)", () => {
  it("cancelarAgendamento faz POST /agendamentos/{id}/cancelar (AC-3)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ id: "a1", status: "cancelado" }));
    vi.stubGlobal("fetch", fetchMock);
    const r = await cancelarAgendamento("a 1");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/agendamentos/a%201/cancelar");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(r).toMatchObject({ status: "cancelado" });
  });

  it("reenviarAgendamento faz POST /agendamentos/{id}/reenviar (AC-4)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ id: "a1", status: "aprovado" }));
    vi.stubGlobal("fetch", fetchMock);
    const r = await reenviarAgendamento("a1");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/agendamentos/a1/reenviar");
    expect(init.method).toBe("POST");
    expect(r).toMatchObject({ status: "aprovado" });
  });

  it("cancelarSerie faz POST /agendamentos/{id}/cancelar-serie e devolve {cancelados} (AC-5)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ cancelados: 3 }));
    vi.stubGlobal("fetch", fetchMock);
    const r = await cancelarSerie("a1");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/agendamentos/a1/cancelar-serie");
    expect(init.method).toBe("POST");
    expect(r).toEqual({ cancelados: 3 });
  });
});

describe("configuração (spec 0018)", () => {
  const cfg: Configuracao = {
    janela_envio: { dias: [0, 1, 2, 3, 4, 5], inicio: "08:00", fim: "20:00" },
    limite_diario: 200,
    limite_por_contato_dia: null,
    limite_por_agendamento_dia: null,
    envios_pausados: false,
    atualizado_em: "2026-11-10T12:00:00Z",
  };

  it("obterConfiguracao faz GET /api/configuracoes com credenciais (AC-10)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta(cfg));
    vi.stubGlobal("fetch", fetchMock);
    const r = await obterConfiguracao();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/configuracoes",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(r).toEqual(cfg);
  });

  it("atualizarConfiguracao faz PATCH /api/configuracoes com o patch no corpo (AC-10)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ ...cfg, envios_pausados: true }));
    vi.stubGlobal("fetch", fetchMock);
    const r = await atualizarConfiguracao({ envios_pausados: true });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/configuracoes");
    expect(init.method).toBe("PATCH");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({ envios_pausados: true });
    expect(r).toMatchObject({ envios_pausados: true });
  });

  it("atualizarConfiguracao propaga ApiError com status (AC-10)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ detail: "limite inválido" }, 422));
    vi.stubGlobal("fetch", fetchMock);
    const erro = await atualizarConfiguracao({ limite_diario: 0 }).catch((e) => e);
    expect(erro).toBeInstanceOf(ApiError);
    expect(erro).toMatchObject({ status: 422, message: "limite inválido" });
  });
});

describe("sincronizarModelos (Modelos, spec 0013)", () => {
  it("faz POST /modelos/sincronizar e devolve {total,criados,atualizados} (AC-3)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(resposta({ total: 5, criados: 5, atualizados: 0 }));
    vi.stubGlobal("fetch", fetchMock);
    const r = await sincronizarModelos();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/modelos/sincronizar");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(r).toEqual({ total: 5, criados: 5, atualizados: 0 });
  });
});
