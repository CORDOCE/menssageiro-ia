import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Ambiente de teste do frontend (spec 0011): jsdom p/ render de componentes React.
// Sem `globals` — cada teste importa `describe/it/expect/vi` de "vitest" (padrão estrito do repo).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: { "@": new URL(".", import.meta.url).pathname },
  },
});
