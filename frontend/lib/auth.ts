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

// --- Lembrar credenciais (conveniência do login) ---------------------------------------------
// E-mail: não é sensível, memorizado sempre. Senha: SÓ se o usuário marcar — fica em TEXTO no
// localStorage deste navegador (risco de XSS/acesso local). O gerenciador de senhas do navegador
// é a alternativa segura.

const CHAVE_EMAIL = "mensageiro_email";
const CHAVE_SENHA = "mensageiro_senha";

export function salvarEmail(email: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CHAVE_EMAIL, email);
  }
}

export function lerEmail(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(CHAVE_EMAIL) ?? "";
}

export function salvarSenha(senha: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CHAVE_SENHA, senha);
  }
}

export function lerSenha(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(CHAVE_SENHA) ?? "";
}

export function limparSenha(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(CHAVE_SENHA);
  }
}
