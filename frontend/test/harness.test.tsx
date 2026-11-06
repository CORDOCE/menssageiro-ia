import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

// Teste-fumaça da task 0: valida que o harness (jsdom + plugin React + jest-dom) está de pé.
// Substituído pelos testes reais de AC nas tasks seguintes; mantido como guarda do setup.
describe("harness de teste do frontend", () => {
  it("renderiza um componente e aplica os matchers do jest-dom", () => {
    render(<p>mensageiro</p>);
    expect(screen.getByText("mensageiro")).toBeInTheDocument();
  });
});
