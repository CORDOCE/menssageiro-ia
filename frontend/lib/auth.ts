// Armazenamento do token de sessão no cliente (localStorage).
// Simples e suficiente para a Fase 1; endurecimentos (cookie HttpOnly) ficam para depois.

const CHAVE = "mensageiro_token";

export function salvarToken(token: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CHAVE, token);
  }
}

export function lerToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(CHAVE);
}

export function limparToken(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(CHAVE);
  }
}
