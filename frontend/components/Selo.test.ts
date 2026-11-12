import { describe, expect, it } from "vitest";

import { seloAgendamento, seloEnvio, seloModelo } from "./Selo";

describe("seloEnvio", () => {
  it("mapeia os status de reenvio (spec 0020)", () => {
    expect(seloEnvio("aguardando_retry")).toEqual({ tom: "aguardando", texto: "Reenviando" });
    expect(seloEnvio("aguardando_decisao")).toEqual({ tom: "erro", texto: "Precisa decisão" });
    expect(seloEnvio("falhou")).toEqual({ tom: "erro", texto: "Falhou" });
  });
});

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

describe("seloAgendamento", () => {
  it("mapeia 'parcial' (teto por-agendamento, spec 0016)", () => {
    expect(seloAgendamento("parcial")).toEqual({ tom: "aguardando", texto: "Parcial" });
  });

  it("distingue enviado, não enviada e cancelada", () => {
    expect(seloAgendamento("enviado")).toEqual({ tom: "agendada", texto: "Enviada" });
    expect(seloAgendamento("falhou")).toEqual({ tom: "erro", texto: "Não enviada" });
    expect(seloAgendamento("cancelado")).toEqual({ tom: "neutro", texto: "Cancelada" });
  });
});
