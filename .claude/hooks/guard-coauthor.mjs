#!/usr/bin/env node
// HTECH-SDD · PreToolUse(Bash) — impede trailers de co-autoria de IA nos commits.
//
// Regra global da casa (todos os projetos): commits sob a conta GitHub local, SEM
// `Co-Authored-By`, SEM emoji robo, SEM "Generated with...". Este hook bloqueia o
// `git commit` antes de gravar o trailer.
//
// Falha ABERTA (exit 0 em erro do hook). Bloqueio = exit 2 + motivo no stderr.

import { readFileSync } from "node:fs";

const allow = () => process.exit(0);
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
if (!/\bgit\s+commit\b/.test(cmd)) allow(); // so nos interessa o commit

const FORBIDDEN = [
  /co-?authored-by\s*:/i,
  /assisted-by\s*:/i,
  /generated with\b/i,
  /\bClaude\s+(Code|Opus|Sonnet|Haiku)\b/i,
  /🤖/u,
];

if (FORBIDDEN.some((re) => re.test(cmd))) {
  block(
    "⛔ HTECH-SDD: trailer de co-autoria de IA detectado no commit. Regra da casa: " +
      "commit sob a conta GitHub local, sem `Co-Authored-By`, sem `🤖`, sem `Generated with`. " +
      "Reescreva a mensagem so com o porque da mudanca. " +
      "(regra local — veja PLAYBOOK_DEV.md)",
  );
}

allow();
