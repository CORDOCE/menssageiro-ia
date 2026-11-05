import { redirect } from "next/navigation";

// A tela inicial agora é "Hoje" (spec 0006). Mantém /painel funcionando para bookmarks antigos.
export default function PainelPage() {
  redirect("/hoje");
}
