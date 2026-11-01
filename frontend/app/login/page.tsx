"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { login } from "@/lib/api";
import { salvarToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [totp, setTotp] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const r = await login(email, senha, totp);
      salvarToken(r.token);
      router.replace("/painel");
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="centro">
      <form className="cartao" onSubmit={enviar}>
        <h1>Mensageiro</h1>
        <p className="sub">Entre com e-mail, senha e o código do autenticador.</p>
        <label>
          E-mail
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label>
          Código 2FA
          <input
            inputMode="numeric"
            value={totp}
            onChange={(e) => setTotp(e.target.value)}
            required
            autoComplete="one-time-code"
            placeholder="000000"
          />
        </label>
        {erro ? (
          <p role="alert" className="erro">
            {erro}
          </p>
        ) : null}
        <button type="submit" disabled={carregando}>
          {carregando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
