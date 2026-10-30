#!/usr/bin/env node
// HTECH-SDD · PreToolUse(Bash) — impede que SEGREDO entre no historico git.
//
// Por que existe: o erro mais caro do fluxo com IA e um `client_secret`/token/.env vazar num commit
// (ja aconteceu no portfolio). Code review humano nao pega isso de forma confiavel; uma trava
// deterministica pega. Roda ANTES do `git commit`/`git add` e bloqueia (exit 2) se achar segredo.
//
// DUAS verificacoes no `git commit`:
//   1) NOME do arquivo staged: .env real, chave privada, service-account/credentials.* -> bloqueia.
//   2) CONTEUDO staged (`git diff --cached`): tokens de provedor + cabecalho de chave privada -> bloqueia.
// E no `git add <arquivo-sensivel>` explicito: bloqueia cedo, com a mensagem do caminho legitimo.
//
// Filosofia: FALHA ABERTA (qualquer erro do proprio hook -> exit 0; nunca trava por bug do hook).
// Bloqueio real = exit 2 + motivo no stderr (o valor do segredo NUNCA e ecoado).

import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";

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
const isCommit = /\bgit\s+commit\b/.test(cmd);
const isAdd = /\bgit\s+add\b/.test(cmd);
if (!isCommit && !isAdd) allow();

const PB = "(regra local HTECH-SDD — veja playbooks/PLAYBOOK_DEV.md)";

// nomes que (quase) nunca devem ser versionados. .env.example/.sample/.template sao OK.
const SENSITIVE_NAME = [
  /(^|\/)\.env(\.[A-Za-z0-9_]+)?$/, // .env, .env.local, .env.production ...
  /(^|\/)(id_rsa|id_dsa|id_ecdsa|id_ed25519)$/,
  /\.(pem|key|pfx|p12|keystore|jks)$/i,
  /(^|\/)(service-account|serviceaccount|credentials|gcloud-key|gha-creds|secrets?)[^/]*\.json$/i,
  /(^|\/)\.npmrc$/,
  /(^|\/)\.pgpass$/,
];
const SAFE_NAME = /\.env\.(example|sample|template|dist)$/i;
const isSensitiveName = (f) => !SAFE_NAME.test(f) && SENSITIVE_NAME.some((re) => re.test(f));

// padroes de segredo de ALTA confianca (poucos falsos-positivos)
const SECRET_CONTENT = [
  { re: /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/, what: "chave privada" },
  { re: /AKIA[0-9A-Z]{16}/, what: "AWS Access Key ID" },
  { re: /\bASIA[0-9A-Z]{16}/, what: "AWS temp key" },
  { re: /AIza[0-9A-Za-z\-_]{35}/, what: "Google API key" },
  { re: /GOCSPX-[0-9A-Za-z\-_]{20,}/, what: "Google OAuth client secret" },
  { re: /"client_secret"\s*:\s*"[^"]{12,}"/, what: "client_secret (OAuth)" },
  { re: /ghp_[0-9A-Za-z]{36}/, what: "GitHub PAT" },
  { re: /github_pat_[0-9A-Za-z_]{22,}/, what: "GitHub fine-grained PAT" },
  { re: /xox[baprs]-[0-9A-Za-z-]{10,}/, what: "Slack token" },
  { re: /sk_live_[0-9A-Za-z]{20,}/, what: "Stripe live secret" },
  { re: /\bSG\.[0-9A-Za-z\-_]{16,}\.[0-9A-Za-z\-_]{16,}/, what: "SendGrid key" },
  { re: /eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}/, what: "JWT (possivel credencial)" },
];

const sh = (c) => {
  try {
    return execSync(c, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    return "";
  }
};

// --- git add <arquivo-sensivel> explicito: bloqueia cedo ---
if (isAdd) {
  const after = (cmd.split(/\bgit\s+add\b/)[1] || "").split(/[|&;]/)[0];
  const toks = after.trim().split(/\s+/).filter((t) => t && !t.startsWith("-"));
  const bad = toks.find((t) => isSensitiveName(t.replace(/^["']|["']$/g, "")));
  if (bad) {
    block(
      `⛔ HTECH-SDD: \`${bad}\` parece arquivo de segredo e nao deve ser versionado. ` +
        "Adicione ao `.gitignore` e versione um `.env.example` (sem valores). " +
        "Se for MESMO intencional, faca o `git add` voce mesmo num terminal comum. " + PB,
    );
  }
  // `git add .`/`-A`: nao da pra inspecionar aqui — o conteudo cai na rede do commit. Libera.
  allow();
}

// --- git commit: checa nomes E conteudo do que esta staged ---
const names = sh("git diff --cached --name-only").split(/\r?\n/).filter(Boolean);
const sensitive = names.filter(isSensitiveName);
if (sensitive.length) {
  block(
    "⛔ HTECH-SDD: commit bloqueado — arquivo(s) de segredo staged:\n  - " +
      sensitive.join("\n  - ") +
      "\nRemova do stage (`git restore --staged <arquivo>`), coloque no `.gitignore`, " +
      "e versione um `.env.example` sem valores. " + PB,
  );
}

const diff = sh("git diff --cached -U0");
if (diff) {
  const added = diff
    .split(/\r?\n/)
    .filter((l) => l.startsWith("+") && !l.startsWith("+++"))
    .join("\n");
  const hits = SECRET_CONTENT.filter((s) => s.re.test(added)).map((s) => s.what);
  if (hits.length) {
    block(
      "⛔ HTECH-SDD: commit bloqueado — possivel SEGREDO no diff staged: " +
        [...new Set(hits)].join(", ") +
        ".\nTire o valor do codigo (use variavel de ambiente / secret manager), des-stage o arquivo " +
        "e, se ja vazou no historico, ROTACIONE a credencial. (o valor nao foi ecoado de proposito) " +
        PB,
    );
  }
}

allow();
