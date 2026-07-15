/**
 * Tests — onda R2 (PD-01) — PerfilFamiliaCard lê o contrato left/right do narrador
 * (não o context/conclusion morto) e parseia os <p> sem dangerouslySetInnerHTML.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PerfilFamiliaCard } from "@/components/report/cards/PerfilFamiliaCard";

const LEFT = "<p>Titular, 40 anos, é engenheiro.</p>\n<p>Cônjuge, CLT.</p>";
const RIGHT = "<p>Meta de IF de R$ 5M.</p>";

describe("PerfilFamiliaCard", () => {
  it("renderiza os parágrafos de left/right (contrato do narrador)", () => {
    render(<PerfilFamiliaCard narrativas={{ perfil_familia: { left: LEFT, right: RIGHT } }} />);
    expect(screen.getByText("A Família")).toBeInTheDocument();
    expect(screen.getByText("Titular, 40 anos, é engenheiro.")).toBeInTheDocument();
    expect(screen.getByText("Cônjuge, CLT.")).toBeInTheDocument();
    expect(screen.getByText("Meta de IF de R$ 5M.")).toBeInTheDocument();
  });

  it("não emite tags <p> literais (parse, não dangerouslySetInnerHTML)", () => {
    const { container } = render(
      <PerfilFamiliaCard narrativas={{ perfil_familia: { left: LEFT, right: RIGHT } }} />,
    );
    expect(container.textContent).not.toContain("<p>");
  });

  it("renderiza null quando não há narrativa de perfil", () => {
    const { container } = render(<PerfilFamiliaCard narrativas={{}} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza null com o contrato antigo context/conclusion (não casa mais)", () => {
    const { container } = render(
      <PerfilFamiliaCard narrativas={{ perfil_familia: { context: "x", conclusion: "y" } }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
