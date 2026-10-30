#!/usr/bin/env node
// HTECH-SDD · SessionStart — injeta o contexto base do projeto no inicio de TODA sessao.
//
// Por que existe: garante que voce (ou qualquer pessoa do time, ou outra sessao de IA)
// ao reabrir o projeto JA comeca com o estado + as diretrizes carregados, sem ler nada manual.
//
// Agnostico ao formato do repo: acha o STATE em varios lugares, le o indice de memoria
// se o repo usa esse padrao (fluxo-service/HTECH-EVOLVE usam ./memory/MEMORY.md), mostra a
// branch atual e AVISA se voce esta na main. stdout vira contexto. Sempre exit 0.

import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";

const first = (paths) => paths.find((p) => existsSync(p));

try {
  let out = "# Contexto base — H.Tech SDD (carregado no SessionStart)\n";

  // 1) branch atual + aviso de main
  let branch = "";
  try {
    branch = execSync("git rev-parse --abbrev-ref HEAD", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    /* repo sem git ou git ausente */
  }
  if (branch) {
    out += `\nBranch atual: **${branch}**`;
    if (branch === "main" || branch === "master") {
      out +=
        `  ⚠️ Voce esta na **${branch}** (producao). Trabalhe na \`dev\` e abra PR — ` +
        "push direto na main esta bloqueado por hook.";
    }
    out += "\n";
  }

  // 2) STATE.md — memoria de trabalho (volatil): retome o trabalho exatamente daqui
  const state = first(["STATE.md", "docs/STATE.md", ".claude/STATE.md", "PROGRESS.md", "docs/PROGRESS.md"]);
  if (state) {
    out += `\n===== ${state} (memoria de trabalho — retome daqui) =====\n`;
    out += readFileSync(state, "utf8").trim() + "\n";
  }

  // 3) indice de memoria do repo, se existir (padrao fluxo/HTECH-EVOLVE)
  const mem = first(["memory/MEMORY.md", "docs/MEMORY.md"]);
  if (mem) {
    out += `\n===== ${mem} (indice de memoria — puxe itens sob demanda) =====\n`;
    out += readFileSync(mem, "utf8").trim() + "\n";
  }

  // 4) dica da spec ativa
  if (existsSync("specs")) {
    out += `\n> Spec ativa: veja "Em andamento" no STATE e leia \`specs/NNNN-*/spec.md\` sob demanda.\n`;
  }

  // 5) lembrete curto das diretrizes (detalhe completo no CLAUDE.md)
  out +=
    "\n> Diretrizes H.Tech SDD: a **spec e a fonte da verdade** · trabalhe na **dev** e abra PR · " +
    "**zero co-autoria de IA** nos commits · rode **/validar** antes do PR · atualize o **STATE.md** ao pausar. " +
    "Detalhe no CLAUDE.md.\n";

  // so escreve se achou algo util alem do lembrete (evita ruido em repo cru)
  if (branch || state || mem) process.stdout.write(out);
} catch {
  /* fail-graceful: nunca derruba a sessao por causa do hook */
}
process.exit(0);
