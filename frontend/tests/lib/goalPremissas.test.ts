import { describe, expect, it } from "vitest";

import {
  buildAportePremissasRows,
  buildDolarPremissasRows,
  buildIFPremissasRows,
  formatGoalVigenciaDate,
  type PremissaRow,
} from "@/lib/goalPremissas";
import { PERCENTUAL_COM_PONTO } from "../shared/percentualPtBr";

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

describe("percentual das premissas usa vírgula (COPY_GUIDELINES §4.6)", () => {
  const valor = (rows: PremissaRow[], label: string) =>
    rows.find((r) => r.label === label)?.value;

  // Os inputs do wizard andam de 0,5 em 0,5: o número cru interpolado saía
  // "4.5% a.a." sem `toFixed` nenhum.
  it("meta IF: TRS, retorno real e taxa conservadora", () => {
    const rows = buildIFPremissasRows(
      {
        renda_passiva_mensal_brl: 10000,
        trs_pct: 4.5,
        retorno_real_anual_pct: 5.5,
        horizonte_anos: 10,
        taxa_retirada_conservadora_pct: 3.5,
      },
      null
    );
    expect(valor(rows, "TRS (taxa de retirada segura)")).toBe("4,5% a.a.");
    expect(valor(rows, "Retorno real esperado")).toBe("5,5% a.a. (acima da inflação)");
    expect(valor(rows, "Taxa conservadora (Trinity)")).toBe("3,5% a.a.");
    expect(rows.map((r) => r.value).join(" ")).not.toMatch(PERCENTUAL_COM_PONTO);
  });

  it("meta IF: valor inteiro leva a casa do formatPercent, como no IFHeroCard", () => {
    const rows = buildIFPremissasRows(
      {
        renda_passiva_mensal_brl: 10000,
        trs_pct: 5,
        retorno_real_anual_pct: 6,
        horizonte_anos: 10,
      },
      null
    );
    expect(valor(rows, "TRS (taxa de retirada segura)")).toBe("5,0% a.a.");
    expect(valor(rows, "Taxa conservadora (Trinity)")).toBe("4,0% a.a.");
  });

  // O produtor quantiza em 2 casas (`compute_aporte_derived`): x,x5 é empate,
  // e o Intl arredonda o decimal exibido (12,35 → 12,4) onde `toFixed`
  // arredondava o binário (12,349… → 12.3).
  it("meta de aporte: distribuição percentual, com empate x,x5", () => {
    const rows = buildAportePremissasRows(
      { meta_aporte_mensal_brl: 2000, dia_aporte: 5 },
      { aporte_anual_brl: 24000, distribuicao_pct: { RF: 87.65, RV: 12.35 } }
    );
    const distribuicao = valor(rows, "Distribuição");
    expect(distribuicao).toBe("RF: 87,7% · RV: 12,4%");
    expect(distribuicao).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

describe("horizonte da dolarização usa vírgula (COPY_GUIDELINES §4.1)", () => {
  const horizonte = (meses: number) =>
    buildDolarPremissasRows(
      { meta_usd: 50000, aporte_mensal_brl: 4000 },
      { horizonte_estimado_meses: meses }
    ).find((r) => r.label === "Horizonte estimado")?.value;

  // O produtor arredonda os meses a 1 casa (`compute_dolar_derived`): eles
  // chegam fracionários e saíam crus, "71.2 meses".
  it("meses fracionários e anos com uma casa", () => {
    expect(horizonte(71.2)).toBe("71,2 meses (~5,9 anos)");
  });

  it("meses inteiros seguem sem casa; os anos mantêm a sua", () => {
    expect(horizonte(96)).toBe("96 meses (~8,0 anos)");
  });

  // 1,8 / 12 = 0,15 é empate no decimal exibido: o Intl arredonda para cima
  // (§4.5), onde `toFixed` arredondava o binário (0,1499…) e dava "0.1".
  it("empate dos anos arredonda o decimal exibido", () => {
    expect(horizonte(1.8)).toBe("1,8 meses (~0,2 anos)");
  });

  it("agrupa milhar", () => {
    expect(horizonte(1234.5)).toBe("1.234,5 meses (~102,9 anos)");
  });
});
