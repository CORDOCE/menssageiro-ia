import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  type AgendamentoCriar,
  type Modelo,
  criarAgendamento,
  listarModelos,
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
