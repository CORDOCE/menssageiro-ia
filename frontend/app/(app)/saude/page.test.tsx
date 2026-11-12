import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { ApiError, type SaudeDeep } from "@/lib/api";
import * as api from "@/lib/api";
import SaudePage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, obterSaude: vi.fn() };
});

// Router estável (ver Histórico/Agenda): senão o useEffect de carga entraria em loop.
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace, push: vi.fn(), back: vi.fn() } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function saude(p: Partial<SaudeDeep> = {}): SaudeDeep {
  return {
    banco: { status: "ok" },
    worker: { status: "vivo", ultimo_ciclo_em: "2026-11-12T12:00:00Z", segundos_desde: 30 },
    envios_hoje: { entregue: 2, falhou: 1 },
    taxa_falha_hoje: { tentativas: 3, falhas: 1, percentual: 33.3 },
    fila: 4,
    gasto_mes_estimado: {
      valor: 1.05,
      moeda: "BRL",
      estimado: true,
      base: "30 envio(s) com sucesso × R$ 0.035 (tarifa UTILITY, §4.4)",
    },
    ...p,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("SaudePage (AC-10)", () => {
  it("mostra os cartões das 6 seções com os dados", async () => {
    vi.mocked(api.obterSaude).mockResolvedValue(saude());
    render(<SaudePage />);
    expect(await screen.findByText("Conectado")).toBeInTheDocument(); // banco
    expect(screen.getByText("Vivo")).toBeInTheDocument(); // worker
    expect(screen.getByText(/entregue:/)).toBeInTheDocument(); // envios hoje
    expect(screen.getByText("33.3%")).toBeInTheDocument(); // taxa
    expect(screen.getByText(/agendamento\(s\) à espera/)).toBeInTheDocument(); // fila
    expect(screen.getByText("R$ 1.05")).toBeInTheDocument(); // gasto estimado
    expect(screen.getByText(/tarifa UTILITY/)).toBeInTheDocument(); // base do cálculo
  });

  it("worker parado aparece com classe de erro", async () => {
    vi.mocked(api.obterSaude).mockResolvedValue(
      saude({ worker: { status: "parado", ultimo_ciclo_em: null, segundos_desde: null } }),
    );
    render(<SaudePage />);
    const parado = await screen.findByText("Parado");
    expect(parado).toHaveClass("erro");
    expect(screen.getByText("Nunca executou")).toBeInTheDocument();
  });

  it("erro de carga mostra mensagem legível", async () => {
    vi.mocked(api.obterSaude).mockRejectedValue(new ApiError(500, "Erro 500"));
    render(<SaudePage />);
    expect(await screen.findByText("Erro 500")).toBeInTheDocument();
  });

  it("401 redireciona para login", async () => {
    vi.mocked(api.obterSaude).mockRejectedValue(new ApiError(401, "nao autenticado"));
    render(<SaudePage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
