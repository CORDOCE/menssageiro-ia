import type { ReactNode } from "react";

// Estado vazio padrão (DESIGN §5): mensagem + ação opcional. Sem spinner.
export function EstadoVazio({ mensagem, acao }: { mensagem: string; acao?: ReactNode }) {
  return (
    <div className="estado-vazio">
      <p>{mensagem}</p>
      {acao}
    </div>
  );
}
