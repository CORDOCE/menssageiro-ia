// Cliente da API do backend (FastAPI). Base em NEXT_PUBLIC_API_URL (definida na Railway).
import { lerToken } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface LoginResposta {
  token: string;
  nome: string;
  email: string;
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  ativo: boolean;
}

export async function login(email: string, senha: string, totp: string): Promise<LoginResposta> {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha, totp }),
  });
  if (!r.ok) {
    const corpo: { detail?: string } = await r.json().catch(() => ({}));
    throw new Error(corpo.detail ?? "Falha no login");
  }
  return r.json() as Promise<LoginResposta>;
}

export async function me(): Promise<Usuario> {
  const r = await fetch(`${BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${lerToken() ?? ""}` },
  });
  if (!r.ok) {
    throw new Error("Não autenticado");
  }
  return r.json() as Promise<Usuario>;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${lerToken() ?? ""}` },
  }).catch(() => undefined);
}
