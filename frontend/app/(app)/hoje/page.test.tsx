import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import * as api from "@/lib/api";
import HojePage from "./page";

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, listarAgendamentos: vi.fn(), listarContatos: vi.fn() };
});

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), usePathname: () => "/hoje" }));

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe("HojePage — entrada da tela Nova mensagem (T9)", () => {
  it("exibe o CTA 'Nova mensagem' apontando para /nova-mensagem", () => {
    vi.mocked(api.listarAgendamentos).mockResolvedValue([]);
    vi.mocked(api.listarContatos).mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 });
    render(<HojePage />);
    expect(screen.getByRole("button", { name: /nova mensagem/i })).toHaveAttribute("href", "/nova-mensagem");
  });
});
