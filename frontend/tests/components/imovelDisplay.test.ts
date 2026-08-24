import { describe, expect, it } from "vitest";

import { imovelDisplayLabel, valorApurado } from "@/components/report/cards/imovelDisplay";

describe("imovelDisplayLabel", () => {
  // Os valores abaixo são a SAÍDA REAL de `canonicalize()` + `endereco_exibivel()`
  // para descrições cartoriais — não formas escritas à mão (A40.l6 §Ataque A4).
  it("mostra o endereço minimizado que o E5 publicou", () => {
    expect(
      imovelDisplayLabel({ endereco_display: "  exemplo 100  ", classification: "locado" }),
    ).toBe("exemplo 100");
  });

  it("cai para classe quando o E5 suprimiu o endereço (cascata mat:/iptu: ou PII)", () => {
    expect(imovelDisplayLabel({ endereco_display: null, classification: "comercial" })).toBe(
      "Imóvel comercial",
    );
  });

  it("cai para classe em payload antigo, sem o campo", () => {
    expect(
      imovelDisplayLabel({ endereco_display: undefined, classification: "locado" } as never),
    ).toBe("Imóvel locado");
  });
});

describe("valorApurado", () => {
  it("treats null and zero as absent", () => {
    expect(valorApurado(null)).toBeNull();
    expect(valorApurado(0)).toBeNull();
    expect(valorApurado(1500)).toBe(1500);
  });
});
