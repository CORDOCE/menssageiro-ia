import { describe, expect, it } from "vitest";

import { saoPauloParaIso } from "./datas";

describe("saoPauloParaIso", () => {
  it("converte horário de parede de São Paulo (sem horário de verão) para UTC (AC-4)", () => {
    // Dez/2026: Brasil sem horário de verão desde 2019 → UTC-3. 12:00 SP = 15:00 UTC.
    expect(saoPauloParaIso("2026-12-01T12:00")).toBe("2026-12-01T15:00:00.000Z");
  });

  it("aplica o offset de horário de verão vigente na data (borda DST)", () => {
    // Fev/2018: SP em horário de verão → UTC-2. 12:00 SP = 14:00 UTC.
    expect(saoPauloParaIso("2018-02-15T12:00")).toBe("2018-02-15T14:00:00.000Z");
    // Jul/2018: horário padrão → UTC-3. 12:00 SP = 15:00 UTC.
    expect(saoPauloParaIso("2018-07-15T12:00")).toBe("2018-07-15T15:00:00.000Z");
  });

  it("aceita segundos opcionais no horário de parede", () => {
    expect(saoPauloParaIso("2026-12-01T12:00:30")).toBe("2026-12-01T15:00:30.000Z");
  });

  it("lança erro para string vazia ou mal formada", () => {
    expect(() => saoPauloParaIso("")).toThrow();
    expect(() => saoPauloParaIso("01/12/2026 12:00")).toThrow();
  });
});
