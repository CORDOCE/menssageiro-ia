import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  type AgendamentoCriar,
  type Modelo,
  cancelarAgendamento,
  cancelarSerie,
  criarAgendamento,
  listarModelos,
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
