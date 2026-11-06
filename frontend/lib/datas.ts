// Conversão de horário para a tela Nova mensagem (spec 0011, AC-4). O operador informa um horário
// de parede no fuso America/Sao_Paulo (input datetime-local); o backend espera um instante em
// ISO-8601 UTC. A conversão usa a base IANA via Intl — independe do fuso do navegador/runner e
// respeita o offset vigente na data (ex.: horário de verão histórico).

export const FUSO_SAO_PAULO = "America/Sao_Paulo";

const PADRAO_LOCAL = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/;

// Offset do fuso em relação ao UTC, em milissegundos (tempo no fuso − UTC), para o instante dado.
function offsetFusoMs(fuso: string, instante: Date): number {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: fuso,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(instante);
  const m: Record<string, number> = {};
  for (const p of partes) if (p.type !== "literal") m[p.type] = Number(p.value);
  const comoUtc = Date.UTC(m.year, m.month - 1, m.day, m.hour, m.minute, m.second);
  return comoUtc - instante.getTime();
}

/**
 * Converte um horário de parede de São Paulo ("YYYY-MM-DDTHH:mm" com segundos opcionais) para
 * ISO-8601 em UTC (sufixo Z). Lança Error se a string for inválida.
 */
export function saoPauloParaIso(local: string): string {
  const m = PADRAO_LOCAL.exec(local);
  if (!m) throw new Error("Horário inválido");
  const [, y, mo, d, h, mi, s] = m;
  const comp = [Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), s ? Number(s) : 0] as const;
  // 1ª aproximação: trata o horário de parede como se fosse UTC e corrige pelo offset do fuso.
  const palpite = Date.UTC(...comp);
  const off1 = offsetFusoMs(FUSO_SAO_PAULO, new Date(palpite));
  let utc = palpite - off1;
  // Refino: perto de transições de offset, o offset no instante corrigido pode diferir.
  const off2 = offsetFusoMs(FUSO_SAO_PAULO, new Date(utc));
  if (off2 !== off1) utc = palpite - off2;
  return new Date(utc).toISOString();
}
