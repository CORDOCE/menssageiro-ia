import type { ReactNode } from "react";

import { GuardaAuth } from "@/components/GuardaAuth";

// Grupo de rotas autenticadas: guarda de auth + shell de navegação.
export default function AppLayout({ children }: { children: ReactNode }) {
  return <GuardaAuth>{children}</GuardaAuth>;
}
