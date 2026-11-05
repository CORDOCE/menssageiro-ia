"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Raiz: encaminha para Hoje; a GuardaAuth (via cookie) redireciona ao /login se não autenticado.
// O token é cookie HttpOnly (ADR 0012) — não dá para checar sessão em JS aqui.
export default function Home(): null {
  const router = useRouter();
  useEffect(() => {
    router.replace("/hoje");
  }, [router]);
  return null;
}
