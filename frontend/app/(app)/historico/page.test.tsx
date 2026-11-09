import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type Envio } from "@/lib/api";
import * as api from "@/lib/api";
import HistoricoPage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, listarEnvios: vi.fn() };
});

// Router estável (ver Agenda/Modelos): senão o useEffect de carga entraria em loop.
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace, push: vi.fn(), back: vi.fn() } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function envio(p: Partial<Envio> = {}): Envio {
  return {
    id: "e1",
    contato_id: "c1",
    contato_nome: "Alice",
    contato_telefone: "+5531999990001",
    modelo_id: "m1",
    modelo_nome: "boas_vindas",
    status: "entregue",
    erro_codigo: null,
    erro_motivo: null,
    criado_em: "2026-01-01T15:00:00Z",
    ...p,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("HistoricoPage — lista (AC-8)", () => {
  it("lista envios com contato, telefone, modelo e selo de status", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([envio({ status: "entregue" })]);
    render(<HistoricoPage />);
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Entregue", { selector: "span.selo" })).toBeInTheDocument();
    expect(screen.getByText(/\+5531999990001/)).toBeInTheDocument();
    expect(screen.getByText(/boas_vindas/)).toBeInTheDocument();
    expect(api.listarEnvios).toHaveBeenCalledWith({ status: undefined, desde: undefined, ate: undefined });
  });

  it("envio avulso (sem modelo) mostra '(sem modelo)' (borda)", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([envio({ modelo_id: null, modelo_nome: null })]);
    render(<HistoricoPage />);
    await screen.findByText("Alice");
    expect(screen.getByText(/\(sem modelo\)/)).toBeInTheDocument();
  });

  it("estado vazio orienta a ajustar filtros", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([]);
    render(<HistoricoPage />);
    expect(await screen.findByText(/nenhum envio/i)).toBeInTheDocument();
  });
});

describe("HistoricoPage — erro só quando falhou (AC-8/AC-6)", () => {
  it("mostra motivo e código quando status=falhou", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([
      envio({ status: "falhou", erro_codigo: "131026", erro_motivo: "indisponível" }),
    ]);
    render(<HistoricoPage />);
    await screen.findByText("Alice");
    expect(screen.getByText(/Falha \(131026\): indisponível/)).toBeInTheDocument();
  });

  it("não mostra bloco de erro quando o envio não falhou", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([envio({ status: "entregue" })]);
    render(<HistoricoPage />);
    await screen.findByText("Alice");
    expect(screen.queryByText(/^Falha/)).not.toBeInTheDocument();
  });
});

describe("HistoricoPage — filtro e auth (AC-8)", () => {
  it("recarrega com ?status ao trocar o filtro", async () => {
    vi.mocked(api.listarEnvios).mockResolvedValue([envio()]);
    render(<HistoricoPage />);
    await screen.findByText("Alice");
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Status"), "falhou");
    await waitFor(() =>
      expect(api.listarEnvios).toHaveBeenLastCalledWith({ status: "falhou", desde: undefined, ate: undefined }),
    );
  });

  it("redireciona ao login quando a carga volta 401", async () => {
    vi.mocked(api.listarEnvios).mockRejectedValue(new ApiError(401, "não autenticado"));
    render(<HistoricoPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
