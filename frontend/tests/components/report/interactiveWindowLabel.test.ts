import { describe, expect, it } from "vitest";

import { formatInteractiveWindowBasis } from "@/components/report/utils/interactiveWindowLabel";
import {
  describeJanelaEscopo,
  parseJanelaRotulo,
} from "@/components/report/utils/janelaLabel";

describe("formatInteractiveWindowBasis", () => {
  it("imprime contagem real e limites sem prometer contiguidade", () => {
    expect(
      formatInteractiveWindowBasis({
        janela_meses: 3,
        mes_inicio: "2025-08",
        mes_fim: "2025-12",
      }),
    ).toBe("3 meses documentados · ago/25 — dez/25");
  });

  it("não repete o mesmo mês e concorda no singular", () => {
    expect(
      formatInteractiveWindowBasis({
        janela_meses: 1,
        mes_inicio: "2026-01",
        mes_fim: "2026-01",
      }),
    ).toBe("1 mês documentado · jan/26");
  });

  it("não inventa limites ausentes", () => {
    expect(
      formatInteractiveWindowBasis({
        janela_meses: 0,
        mes_inicio: null,
        mes_fim: null,
      }),
    ).toBe("0 meses documentados");
  });
});

describe("vocabulário das janelas interativas", () => {
  it.each(["3m", "6m", "12m", "ytd"] as const)(
    "aceita %s sem confundir tipo conceitual com contagem",
    (tipo) => {
      const parsed = parseJanelaRotulo(tipo, 2);
      expect(parsed?.tipo).toBe(tipo);
      expect(parsed?.meses).toBe(2);
      expect(parsed && describeJanelaEscopo(parsed)).toBe(
        "os últimos 2 meses documentados",
      );
    },
  );
});
