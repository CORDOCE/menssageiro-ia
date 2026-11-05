// Esqueletos de carregamento (DESIGN §5: sem spinner de tela cheia).
export function Esqueleto({ altura = 16, largura = "100%" }: { altura?: number; largura?: string | number }) {
  return <div className="esqueleto" style={{ height: altura, width: largura }} aria-hidden />;
}

export function ListaEsqueleto({ linhas = 5 }: { linhas?: number }) {
  return (
    <div aria-busy="true" aria-label="Carregando" style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
      {Array.from({ length: linhas }).map((_, i) => (
        <Esqueleto key={i} altura={44} />
      ))}
    </div>
  );
}
