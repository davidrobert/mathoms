/**
 * Unit tests — ADR-195 · A12 · PGBL threshold AUVP modula variante.
 *
 * Cobre o helper puro `evaluatePgblAuvpFit`. Thresholds X=20%, Y=12%
 * fixados em ADR-195 §3 D2 (decisão G0 financial-planner).
 *
 * Cenários: auvp_aderente · neutro · abaixo · indeterminado
 *           (por estado != capacidade_disponivel, por alíquota inválida,
 *           por alíquota negativa).
 */
import { describe, expect, it } from "vitest";

import {
  AUVP_ABAIXO_THRESHOLD_PCT,
  AUVP_ADERENTE_THRESHOLD_PCT,
  evaluatePgblAuvpFit,
} from "@/lib/irpf/pgbl-auvp-fit";
import type { IrpfKpis, PgblStatus } from "@/types/irpf";

const KPIS_BASE: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2022, 2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "30000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "11600.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: {
    "2022": "150000.00",
    "2023": "165000.00",
    "2024": "180000.00",
  },
};

function withAliquota(
  aliquotaPct: string,
  status: PgblStatus = "capacidade_disponivel",
): IrpfKpis {
  return {
    ...KPIS_BASE,
    pgbl_status: status,
    aliquota_sobre_tributavel_pct: aliquotaPct,
  };
}

describe("evaluatePgblAuvpFit · ADR-195 §3 D1-D2", () => {
  it("thresholds canônicos = X 20% / Y 12% (consistência com ADR-195 §3 D2)", () => {
    expect(AUVP_ADERENTE_THRESHOLD_PCT).toBe(20);
    expect(AUVP_ABAIXO_THRESHOLD_PCT).toBe(12);
  });

  it("auvp_aderente quando alíquota >= 20% (faixa marginal alta 22,5/27,5%)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("22.50"));
    expect(result.tier).toBe("auvp_aderente");
    expect(result.aliquota).toBe(22.5);
    expect(result.reason).toMatch(/>=.*20/);
  });

  it("auvp_aderente no limite inferior exato (20,00%)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("20.00"));
    expect(result.tier).toBe("auvp_aderente");
    expect(result.aliquota).toBe(20);
  });

  it("neutro quando 12% <= alíquota < 20% (faixa intermediária)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("16.50"));
    expect(result.tier).toBe("neutro");
    expect(result.aliquota).toBe(16.5);
    expect(result.reason).toMatch(/12.*<=.*16\.5.*<.*20/);
  });

  it("neutro no limite inferior exato (12,00%)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("12.00"));
    expect(result.tier).toBe("neutro");
    expect(result.aliquota).toBe(12);
  });

  it("neutro no limite superior estrito (19,99%)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("19.99"));
    expect(result.tier).toBe("neutro");
    expect(result.aliquota).toBe(19.99);
  });

  it("abaixo quando alíquota < 12% (faixa marginal baixa 7,5% ou abaixo)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("7.50"));
    expect(result.tier).toBe("abaixo");
    expect(result.aliquota).toBe(7.5);
    expect(result.reason).toMatch(/<.*12/);
  });

  it("abaixo no limite superior estrito (11,99%)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("11.99"));
    expect(result.tier).toBe("abaixo");
  });

  it("abaixo quando alíquota = 0% (renda toda no isento)", () => {
    const result = evaluatePgblAuvpFit(withAliquota("0.00"));
    expect(result.tier).toBe("abaixo");
    expect(result.aliquota).toBe(0);
  });

  describe("tier `indeterminado` (fallback silencioso §3 D5)", () => {
    it("retorna indeterminado quando pgbl_status = modelo_simplificado", () => {
      const result = evaluatePgblAuvpFit(
        withAliquota("22.50", "modelo_simplificado"),
      );
      expect(result.tier).toBe("indeterminado");
      expect(result.aliquota).toBeNull();
      expect(result.reason).toMatch(/diferente de capacidade_disponivel/);
    });

    it("retorna indeterminado quando pgbl_status = no_teto", () => {
      const result = evaluatePgblAuvpFit(withAliquota("22.50", "no_teto"));
      expect(result.tier).toBe("indeterminado");
    });

    it("retorna indeterminado quando pgbl_status = sem_renda_tributavel", () => {
      const result = evaluatePgblAuvpFit(
        withAliquota("22.50", "sem_renda_tributavel"),
      );
      expect(result.tier).toBe("indeterminado");
    });

    it("retorna indeterminado quando alíquota string vazia", () => {
      const result = evaluatePgblAuvpFit(withAliquota(""));
      expect(result.tier).toBe("indeterminado");
      expect(result.aliquota).toBeNull();
      expect(result.reason).toMatch(/ausente ou inválida/);
    });

    it("retorna indeterminado quando alíquota não-numérica", () => {
      const result = evaluatePgblAuvpFit(withAliquota("abc"));
      expect(result.tier).toBe("indeterminado");
    });

    it("retorna indeterminado quando alíquota negativa (defesa)", () => {
      const result = evaluatePgblAuvpFit(withAliquota("-5.00"));
      expect(result.tier).toBe("indeterminado");
    });
  });

  it("não muta o input kpis", () => {
    const kpis = withAliquota("22.50");
    const snapshot = JSON.stringify(kpis);
    evaluatePgblAuvpFit(kpis);
    expect(JSON.stringify(kpis)).toBe(snapshot);
  });
});
