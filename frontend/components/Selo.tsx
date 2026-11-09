// Selo de status: sempre cor + texto (DESIGN §2/§8). O "tom" mapeia para os tokens de selo.
type Tom = "agendada" | "entregue" | "aguardando" | "erro" | "neutro";

export function Selo({ tom, children }: { tom: Tom; children: React.ReactNode }) {
  return <span className={`selo selo-${tom}`}>{children}</span>;
}

// Mapeia o status de um agendamento para selo (DESIGN §5 glossário).
export function seloAgendamento(status: string): { tom: Tom; texto: string } {
  switch (status) {
    case "aprovado":
      return { tom: "agendada", texto: "Agendada" };
    case "enviando":
    case "enviado":
      return { tom: "agendada", texto: "Enviada" };
    case "entregue":
      return { tom: "entregue", texto: "Entregue" };
    case "lido":
      return { tom: "entregue", texto: "Lida" };
    case "aguardando_decisao":
      return { tom: "aguardando", texto: "Aguardando" };
    case "falhou":
      return { tom: "erro", texto: "Não enviada" };
    case "cancelado":
      return { tom: "neutro", texto: "Cancelada" };
    default:
      return { tom: "neutro", texto: status };
  }
}

// Mapeia o status de um envio para selo (spec 0014). Status internos vêm do webhook (§webhook_meta).
export function seloEnvio(status: string): { tom: Tom; texto: string } {
  switch (status) {
    case "criado":
      return { tom: "neutro", texto: "Criado" };
    case "enviando":
      return { tom: "agendada", texto: "Enviando" };
    case "enviado":
      return { tom: "agendada", texto: "Enviado" };
    case "entregue":
      return { tom: "entregue", texto: "Entregue" };
    case "lido":
      return { tom: "entregue", texto: "Lido" };
    case "falhou":
      return { tom: "erro", texto: "Falhou" };
    default:
      return { tom: "neutro", texto: status };
  }
}

// Mapeia o status de um modelo (template) para selo (spec 0013). Status vêm da Meta (§5.3).
export function seloModelo(status: string): { tom: Tom; texto: string } {
  switch (status) {
    case "aprovado":
      return { tom: "entregue", texto: "Aprovado" };
    case "pendente":
      return { tom: "aguardando", texto: "Pendente" };
    case "rejeitado":
      return { tom: "erro", texto: "Rejeitado" };
    case "pausado":
      return { tom: "neutro", texto: "Pausado" };
    case "rascunho":
      return { tom: "neutro", texto: "Rascunho" };
    default:
      return { tom: "neutro", texto: status };
  }
}
