"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { login } from "@/lib/api";
import { lerEmail, lerSenha, limparSenha, salvarEmail, salvarSenha, salvarToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [totp, setTotp] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [lembrarSenha, setLembrarSenha] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  // Pré-preenche a partir do navegador (só no cliente, após montar — evita hydration mismatch).
  useEffect(() => {
    const emailSalvo = lerEmail();
    if (emailSalvo) {
      setEmail(emailSalvo);
    }
    const senhaSalva = lerSenha();
    if (senhaSalva) {
      setSenha(senhaSalva);
      setLembrarSenha(true);
    }
  }, []);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const r = await login(email, senha, totp);
      salvarToken(r.token);
      salvarEmail(email);
      if (lembrarSenha) {
        salvarSenha(senha);
      } else {
        limparSenha();
      }
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
          <span className="rotulo-linha">
            Senha
            <button
              type="button"
              className="link"
              onClick={() => setMostrarSenha((v) => !v)}
              aria-pressed={mostrarSenha}
            >
              {mostrarSenha ? "Ocultar" : "Mostrar"}
            </button>
          </span>
          <input
            type={mostrarSenha ? "text" : "password"}
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
        <label className="checkbox">
          <input
            type="checkbox"
            checked={lembrarSenha}
            onChange={(e) => setLembrarSenha(e.target.checked)}
          />
          <span>
            Lembrar senha neste navegador
            <small className="aviso">
              Fica salva em texto neste dispositivo. Em computador compartilhado, não marque.
            </small>
          </span>
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
