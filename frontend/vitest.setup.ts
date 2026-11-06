// Registra os matchers do jest-dom (toBeInTheDocument, toBeDisabled, ...) no `expect` do Vitest
// e aplica a augmentação de tipos correspondente. Carregado via `setupFiles` do vitest.config.ts.
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Sem `globals: true`, o auto-cleanup do Testing Library não é registrado — fazemos aqui, para o
// DOM de um teste não vazar para o próximo.
afterEach(() => {
  cleanup();
});
