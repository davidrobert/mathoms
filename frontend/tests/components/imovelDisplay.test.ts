import { describe, expect, it } from "vitest";

import { imovelDisplayLabel, valorApurado } from "@/components/report/cards/imovelDisplay";

describe("imovelDisplayLabel", () => {
  it("prefers endereco_canonical", () => {
    expect(
      imovelDisplayLabel({ endereco_canonical: "  Rua Exemplo, 100  ", classification: "locado" }),
    ).toBe("Rua Exemplo, 100");
  });

  it("falls back to classification", () => {
    expect(imovelDisplayLabel({ endereco_canonical: null, classification: "comercial" })).toBe(
      "Imóvel comercial",
    );
  });
});

describe("valorApurado", () => {
  it("treats null and zero as absent", () => {
    expect(valorApurado(null)).toBeNull();
    expect(valorApurado(0)).toBeNull();
    expect(valorApurado(1500)).toBe(1500);
  });
});
