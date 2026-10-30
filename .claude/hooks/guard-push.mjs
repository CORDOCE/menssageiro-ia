#!/usr/bin/env node
// HTECH-SDD · PreToolUse(Bash) — bloqueia operacoes git perigosas antes de rodarem.
//
// DOIS MODOS (lidos de .claude/htech-sdd.json -> { "guardPush": "block" | "warn" }):
//   - "block"  (PR-first): BLOQUEIA push direto na main/master. Pra repos que trabalham em dev e
//              mergeiam via PR.
//   - "warn"   (deploy-por-push / trunk): NAO bloqueia push na main (push e o deploy sancionado —
//              ex.: Railway). So AVISA. Default quando nao ha config (nunca quebra um deploy).
// Em QUALQUER modo: SEMPRE bloqueia force-push em branch compartilhada e remocao destrutiva ampla.
//
// Filosofia: FALHA ABERTA (erro do hook -> exit 0). Bloqueio real = exit 2 + motivo no stderr.

import { readFileSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";

const allow = () => process.exit(0);
const warn = (msg) => {
  process.stderr.write(msg + "\n");
  process.exit(0); // avisa, mas deixa passar
};
const block = (msg) => {
  process.stderr.write(msg + "\n");
  process.exit(2);
};

let payload = {};
try {
  payload = JSON.parse(readFileSync(0, "utf8") || "{}");
} catch {
  allow();
}

const cmd = String((payload.tool_input && payload.tool_input.command) || "");
if (!cmd.trim()) allow();

// modo (default warn = nunca quebra deploy; o bootstrap grava "block" nos repos PR-first)
let mode = "warn";
try {
  if (existsSync(".claude/htech-sdd.json")) {
    mode = JSON.parse(readFileSync(".claude/htech-sdd.json", "utf8")).guardPush || "warn";
  }
} catch {
  /* sem config -> warn */
}

const PB = "(regra local HTECH-SDD — veja 00 - WORKFLOW IA/playbooks/PLAYBOOK_DEV.md)";
const isPush = /\bgit\s+push\b/.test(cmd);

// 1) force-push: SEMPRE bloqueia (em qualquer modo) — apaga trabalho de outro
if (isPush && /(--force(?!-with-lease)\b|\s-f\b)/.test(cmd)) {
  block(
    "⛔ HTECH-SDD: force-push bloqueado. Reescrever historico em branch compartilhada apaga " +
      "trabalho dos outros. Use `--force-with-lease` numa branch sua, se for mesmo necessario. " + PB,
  );
}

if (isPush) {
  const after = (cmd.split(/\bgit\s+push\b/)[1] || "").split(/[|&;]/)[0];
  const positionals = after.trim().split(/\s+/).filter((t) => t && !t.startsWith("-"));
  const hasExplicitTarget = positionals.length > 0;
  const targetsMain =
    positionals.some((t) => /^(HEAD:)?(main|master)$/.test(t)) || /:(main|master)\b/.test(after);

  let onMain = false;
  if (!hasExplicitTarget) {
    try {
      const b = execSync("git rev-parse --abbrev-ref HEAD", {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
      onMain = b === "main" || b === "master";
    } catch {
      /* sem git */
    }
  }

  if (targetsMain || onMain) {
    if (mode === "block") {
      block(
        "⛔ HTECH-SDD: push direto na main/master bloqueado (modo PR-first). Trabalhe na `dev` e " +
          "abra PR. Se este repo usa push-na-main como DEPLOY, troque .claude/htech-sdd.json para " +
          '{"guardPush":"warn"}. ' + PB,
      );
    }
    warn(
      "⚠️  HTECH-SDD: voce esta publicando na main/master. Neste repo isso e o deploy sancionado " +
        "(modo warn). Confirme que e proposital — e prefira PR quando possivel. " + PB,
    );
  }
}

// destrutivos amplos: SEMPRE bloqueia
const padded = " " + cmd.replace(/\s+/g, " ") + " ";
const DESTRUCTIVE = [
  /\brm\s+-[rf]{1,2}\s+(\/|~|\*|\.\s|\.\/|[A-Za-z]:[\\/])/,
  /\bgit\s+clean\s+-[a-z]*f[a-z]*d/,
];
if (DESTRUCTIVE.some((re) => re.test(padded))) {
  block(
    "⛔ HTECH-SDD: comando de remocao/limpeza destrutiva bloqueado. Confirme o alvo exato e rode " +
      "manualmente num terminal comum se for mesmo a intencao. " + PB,
  );
}

allow();
