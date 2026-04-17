import { describe, expect, it } from "vitest";

import {
  buildIFPremissasRows,
  formatGoalVigenciaDate,
} from "@/lib/goalPremissas";

describe("formatGoalVigenciaDate", () => {
  it("formata YYYY-MM-DD para dd/mm/aaaa", () => {
    expect(formatGoalVigenciaDate("2026-04-17")).toBe("17/04/2026");
  });
});

describe("buildIFPremissasRows", () => {
  it("inclui taxa conservadora default e derivados quando fornecidos", () => {
    const rows = buildIFPremissasRows(
      {
        renda_passiva_mensal_brl: 10000,
        trs_pct: 5,
        retorno_real_anual_pct: 6,
        horizonte_anos: 10,
        taxa_retirada_conservadora_pct: 4,
      },
      {
        if_meta_brl: 2_400_000,
        aporte_necessario_mensal_brl: 5000,
        if_meta_conservadora_brl: 3_000_000,
      }
    );
    expect(rows.some((r) => r.label.includes("TRS"))).toBe(true);
    expect(rows.some((r) => r.value.includes("10 anos"))).toBe(true);
    expect(rows.some((r) => r.label.includes("Patrimônio-alvo (operacional)"))).toBe(
      true
    );
  });
});
