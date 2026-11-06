import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type Modelo } from "@/lib/api";
import * as api from "@/lib/api";
import ModelosPage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, listarModelos: vi.fn(), sincronizarModelos: vi.fn() };
});

// Router estável (ver Agenda): senão o useEffect de carga entraria em loop.
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace, push: vi.fn(), back: vi.fn() } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

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

beforeEach(() => {
  vi.spyOn(window, "alert").mockImplementation(() => undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("ModelosPage — lista (AC-1, AC-5)", () => {
  it("lista modelos com nome, selo, categoria/idioma, prévia do corpo e variáveis", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([
      modelo({ nome: "aviso", status: "aprovado", corpo: "Oi {{1}}", variaveis: ["1"], categoria: "UTILITY", idioma: "pt_BR" }),
    ]);
    render(<ModelosPage />);
    expect(await screen.findByText("aviso")).toBeInTheDocument();
    expect(screen.getByText("Aprovado", { selector: "span.selo" })).toBeInTheDocument();
    expect(screen.getByText(/UTILITY · pt_BR/)).toBeInTheDocument();
    expect(screen.getByText("Oi {{1}}")).toBeInTheDocument();
    expect(screen.getByText(/Variáveis: \{\{1\}\}/)).toBeInTheDocument();
    expect(api.listarModelos).toHaveBeenCalledWith({ status: undefined });
  });

  it("modelo sem variáveis mostra 'Sem variáveis' (borda)", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([modelo({ variaveis: [], corpo: "Texto fixo" })]);
    render(<ModelosPage />);
    await screen.findByText("boas_vindas");
    expect(screen.getByText("Sem variáveis")).toBeInTheDocument();
  });

  it("estado vazio orienta a sincronizar (AC-5)", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([]);
    render(<ModelosPage />);
    expect(await screen.findByText(/nenhum modelo/i)).toBeInTheDocument();
  });
});

describe("ModelosPage — filtro (AC-2)", () => {
  it("recarrega com ?status ao trocar o filtro", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([modelo()]);
    render(<ModelosPage />);
    await screen.findByText("boas_vindas");
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Status"), "pendente");
    await waitFor(() => expect(api.listarModelos).toHaveBeenLastCalledWith({ status: "pendente" }));
  });
});

describe("ModelosPage — sincronizar (AC-3, AC-4)", () => {
  it("sincroniza, mostra o resultado e recarrega (AC-3)", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([modelo()]);
    vi.mocked(api.sincronizarModelos).mockResolvedValue({ total: 5, criados: 2, atualizados: 3 });
    render(<ModelosPage />);
    await screen.findByText("boas_vindas");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /sincronizar com a meta/i }));
    await waitFor(() => expect(api.sincronizarModelos).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("status")).toHaveTextContent("5 total, 2 criado(s), 3 atualizado(s)");
    expect(api.listarModelos).toHaveBeenCalledTimes(2); // recarregou
  });

  it("mostra erro legível quando a sincronização falha (ex.: sem credenciais Meta) (AC-4)", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([modelo()]);
    vi.mocked(api.sincronizarModelos).mockRejectedValue(new ApiError(500, "credenciais da Meta ausentes"));
    render(<ModelosPage />);
    await screen.findByText("boas_vindas");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /sincronizar com a meta/i }));
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith("credenciais da Meta ausentes"));
    expect(replace).not.toHaveBeenCalled();
  });

  it("redireciona ao login quando a sincronização volta 401 (AC-4)", async () => {
    vi.mocked(api.listarModelos).mockResolvedValue([modelo()]);
    vi.mocked(api.sincronizarModelos).mockRejectedValue(new ApiError(401, "não autenticado"));
    render(<ModelosPage />);
    await screen.findByText("boas_vindas");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /sincronizar com a meta/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
