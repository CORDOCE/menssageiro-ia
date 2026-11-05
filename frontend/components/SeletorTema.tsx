"use client";

import { useEffect, useState } from "react";

import { lerTema, salvarTema, type Tema } from "@/lib/tema";

import { IconeLua, IconeSistema, IconeSol } from "./icones";

// Seletor de tema: Claro / Escuro / Seguir o sistema (DESIGN §10).
export function SeletorTema() {
  const [tema, setTema] = useState<Tema>("sistema");

  useEffect(() => {
    setTema(lerTema());
  }, []);

  function escolher(t: Tema) {
    setTema(t);
    salvarTema(t);
  }

  return (
    <div className="selecao-tema" role="group" aria-label="Tema">
      <button
        type="button"
        className={tema === "claro" ? "ativo" : ""}
        aria-pressed={tema === "claro"}
        onClick={() => escolher("claro")}
        title="Claro"
      >
        <IconeSol />
      </button>
      <button
        type="button"
        className={tema === "escuro" ? "ativo" : ""}
        aria-pressed={tema === "escuro"}
        onClick={() => escolher("escuro")}
        title="Escuro"
      >
        <IconeLua />
      </button>
      <button
        type="button"
        className={tema === "sistema" ? "ativo" : ""}
        aria-pressed={tema === "sistema"}
        onClick={() => escolher("sistema")}
        title="Seguir o sistema"
      >
        <IconeSistema />
      </button>
    </div>
  );
}
