import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type Configuracao } from "@/lib/api";
import * as api from "@/lib/api";
import * as pushLib from "@/lib/push";
import ConfiguracoesPage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, obterConfiguracao: vi.fn(), atualizarConfiguracao: vi.fn() };
});

vi.mock("@/lib/push", () => ({ ativarPush: vi.fn(), suportaPush: vi.fn(() => true) }));

// Router estável (ver Agenda): senão o useEffect de carga entraria em loop.
const { replace, router } = vi.hoisted(() => {
  const replace = vi.fn();
  return { replace, router: { replace, push: vi.fn(), back: vi.fn() } };
});
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function cfg(p: Partial<Configuracao> = {}): Configuracao {
  return {
    janela_envio: { dias: [0, 1, 2, 3, 4, 5], inicio: "08:00", fim: "20:00" },
    limite_diario: 200,
    limite_por_contato_dia: null,
    limite_por_agendamento_dia: null,
    envios_pausados: false,
    atualizado_em: "2026-11-10T12:00:00Z",
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

describe("ConfiguracoesPage — carga (AC-10)", () => {
  it("preenche o formulário com os valores atuais", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    render(<ConfiguracoesPage />);

    expect(await screen.findByLabelText("Limite diário")).toHaveValue(200);
    expect(screen.getByLabelText("Pausar todos os envios")).not.toBeChecked();
    expect(screen.getByLabelText("Início")).toHaveValue("08:00");
    expect(screen.getByLabelText("Fim")).toHaveValue("20:00");
    expect(screen.getByLabelText("Seg")).toBeChecked();
    expect(screen.getByLabelText("Dom")).not.toBeChecked();
  });

  it("redireciona ao login em 401 na carga", async () => {
    vi.mocked(api.obterConfiguracao).mockRejectedValue(new ApiError(401, "não autenticado"));
    render(<ConfiguracoesPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});

describe("ConfiguracoesPage — salvar (AC-10)", () => {
  it("envia o PATCH com o limite editado e mostra sucesso", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.mocked(api.atualizarConfiguracao).mockResolvedValue(cfg({ limite_diario: 500 }));
    render(<ConfiguracoesPage />);

    const campo = await screen.findByLabelText("Limite diário");
    await userEvent.clear(campo);
    await userEvent.type(campo, "500");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(api.atualizarConfiguracao).toHaveBeenCalled());
    expect(vi.mocked(api.atualizarConfiguracao).mock.calls[0][0]).toMatchObject({ limite_diario: 500 });
    expect(await screen.findByRole("status")).toHaveTextContent(/salv/i);
  });

  it("limite por contato vazio é enviado como null (sem limite)", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg({ limite_por_contato_dia: 10 }));
    vi.mocked(api.atualizarConfiguracao).mockResolvedValue(cfg());
    render(<ConfiguracoesPage />);

    const campo = await screen.findByLabelText("Limite por contato (por dia)");
    await userEvent.clear(campo);
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(api.atualizarConfiguracao).toHaveBeenCalled());
    expect(vi.mocked(api.atualizarConfiguracao).mock.calls[0][0]).toMatchObject({
      limite_por_contato_dia: null,
    });
  });

  it("pedir confirmação ao ativar a pausa; confirmado, envia envios_pausados=true", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.mocked(api.atualizarConfiguracao).mockResolvedValue(cfg({ envios_pausados: true }));
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<ConfiguracoesPage />);

    await userEvent.click(await screen.findByLabelText("Pausar todos os envios"));
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(confirm).toHaveBeenCalled();
    await waitFor(() => expect(api.atualizarConfiguracao).toHaveBeenCalled());
    expect(vi.mocked(api.atualizarConfiguracao).mock.calls[0][0]).toMatchObject({
      envios_pausados: true,
    });
  });

  it("confirmação cancelada não salva", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<ConfiguracoesPage />);

    await userEvent.click(await screen.findByLabelText("Pausar todos os envios"));
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(api.atualizarConfiguracao).not.toHaveBeenCalled();
  });

  it("valida no cliente (fim ≤ início) com erro legível, sem chamar o backend", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    render(<ConfiguracoesPage />);

    const fim = await screen.findByLabelText("Fim");
    await userEvent.clear(fim);
    await userEvent.type(fim, "07:00"); // 07:00 ≤ início 08:00
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/fim.*maior.*início/i);
    expect(api.atualizarConfiguracao).not.toHaveBeenCalled();
  });

  it("propaga erro do backend ao salvar (ex.: 500) de forma legível", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.mocked(api.atualizarConfiguracao).mockRejectedValue(new ApiError(500, "Erro 500"));
    render(<ConfiguracoesPage />);

    await screen.findByLabelText("Limite diário");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByText("Erro 500")).toBeInTheDocument();
  });
});

describe("ConfiguracoesPage — notificações push (AC-9)", () => {
  it("ativa push e mostra confirmação", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.mocked(pushLib.suportaPush).mockReturnValue(true);
    vi.mocked(pushLib.ativarPush).mockResolvedValue("ok");
    render(<ConfiguracoesPage />);

    const botao = await screen.findByRole("button", { name: "Ativar notificações" });
    await userEvent.click(botao);

    expect(pushLib.ativarPush).toHaveBeenCalled();
    expect(await screen.findByText("Notificações ativadas neste dispositivo.")).toBeInTheDocument();
  });

  it("navegador sem suporte: botão desabilitado + aviso", async () => {
    vi.mocked(api.obterConfiguracao).mockResolvedValue(cfg());
    vi.mocked(pushLib.suportaPush).mockReturnValue(false);
    render(<ConfiguracoesPage />);

    const botao = await screen.findByRole("button", { name: "Ativar notificações" });
    expect(botao).toBeDisabled();
    expect(screen.getByText(/não suporta push/)).toBeInTheDocument();
  });
});
