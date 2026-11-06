import { describe, expect, it } from "vitest";

import { seloModelo } from "./Selo";

describe("seloModelo", () => {
  it("mapeia os status de modelo para tom + texto (AC-1)", () => {
    expect(seloModelo("aprovado")).toEqual({ tom: "entregue", texto: "Aprovado" });
    expect(seloModelo("pendente")).toEqual({ tom: "aguardando", texto: "Pendente" });
    expect(seloModelo("rejeitado")).toEqual({ tom: "erro", texto: "Rejeitado" });
    expect(seloModelo("pausado")).toEqual({ tom: "neutro", texto: "Pausado" });
    expect(seloModelo("rascunho")).toEqual({ tom: "neutro", texto: "Rascunho" });
  });

  it("desconhecido cai em neutro com o próprio status", () => {
    expect(seloModelo("xyz")).toEqual({ tom: "neutro", texto: "xyz" });
  });
});
