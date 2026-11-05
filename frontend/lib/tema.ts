// Tema do app (DESIGN §10 / ADR 0010): claro, escuro ou seguir o sistema.
// "sistema" = sem atributo data-theme (cai no @media prefers-color-scheme).
// A aplicação antes da 1ª pintura é feita por um script inline no layout (evita flash).

export type Tema = "claro" | "escuro" | "sistema";

export const CHAVE_TEMA = "mensageiro_tema";

export function lerTema(): Tema {
  if (typeof window === "undefined") {
    return "sistema";
  }
  const v = window.localStorage.getItem(CHAVE_TEMA);
  return v === "claro" || v === "escuro" ? v : "sistema";
}

export function aplicarTema(tema: Tema): void {
  if (typeof document === "undefined") {
    return;
  }
  const raiz = document.documentElement;
  if (tema === "sistema") {
    raiz.removeAttribute("data-theme");
  } else {
    raiz.setAttribute("data-theme", tema === "escuro" ? "dark" : "light");
  }
}

export function salvarTema(tema: Tema): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CHAVE_TEMA, tema);
  }
  aplicarTema(tema);
}

// Script injetado no <head>/início do <body> para aplicar o tema antes da 1ª pintura.
export const SCRIPT_TEMA =
  "(function(){try{var t=localStorage.getItem('" +
  CHAVE_TEMA +
  "');if(t==='escuro'){document.documentElement.setAttribute('data-theme','dark');}" +
  "else if(t==='claro'){document.documentElement.setAttribute('data-theme','light');}}catch(e){}})();";
