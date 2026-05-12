/**
 * Unit tests — ADR-196 · A12 · Reconciliação PGBL S7×IRPF.
 *
 * Cobre o helper `getPgblCardStrategy` + primitivas `derivePrimaryYear`
 * e `matchIrpfToPeriod`. Matriz da §D1 da ADR-196.
 */
import { describe, expect, it } from "vitest";

import {
  derivePrimaryYear,
  getPgblCardStrategy,
  isInformativeMode,
  matchIrpfToPeriod,
  type PgblCardMode,
} from "@/lib/irpf/pgbl-card-strategy";
import type { IrpfKpis, PgblStatus } from "@/types/irpf";

const KPIS_BASE: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "5400.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2023": "160000.00", "2024": "180000.00" },
};

function withStatus(status: PgblStatus, overrides: Partial<IrpfKpis> = {}): IrpfKpis {
  return { ...KPIS_BASE, pgbl_status: status, ...overrides };
}

describe("derivePrimaryYear", () => {
  it("extrai ano do último label YYYY-MM", () => {
    expect(derivePrimaryYear(["2024-01", "2024-06", "2024-12"])).toBe(2024);
  });

  it("retorna null para labels vazios", () => {
    expect(derivePrimaryYear([])).toBeNull();
    expect(derivePrimaryYear(undefined)).toBeNull();
  });

  it("retorna null para label malformado", () => {
    expect(derivePrimaryYear(["abc"])).toBeNull();
    expect(derivePrimaryYear([""])).toBeNull();
  });

  it("aceita labels com prefixo de ano válido", () => {
    expect(derivePrimaryYear(["2025-03"])).toBe(2025);
  });
});

describe("matchIrpfToPeriod", () => {
  it("authoritative quando ano-base = primaryYear", () => {
    const m = matchIrpfToPeriod([2023, 2024], 2024);
    expect(m).toEqual({ anoBase: 2024, defasadoAnos: 0, authoritative: true });
  });

  it("authoritative quando ano-base = primaryYear - 1 (gap 1)", () => {
    const m = matchIrpfToPeriod([2023, 2024], 2025);
    expect(m).toEqual({ anoBase: 2024, defasadoAnos: 1, authoritative: true });
  });

  it("defasado quando gap >= 2", () => {
    const m = matchIrpfToPeriod([2022], 2025);
    expect(m).toEqual({ anoBase: 2022, defasadoAnos: 3, authoritative: false });
  });

  it("authoritative escolhe maior ano elegível (ignora N+1 futuro)", () => {
    const m = matchIrpfToPeriod([2023, 2024, 2027], 2024);
    expect(m.anoBase).toBe(2024);
  });

  it("anoBase null quando todos os anos > primaryYear + 1", () => {
    const m = matchIrpfToPeriod([2027, 2028], 2024);
    expect(m).toEqual({ anoBase: null, defasadoAnos: null, authoritative: false });
  });

  it("anoBase null para anos_disponiveis vazio", () => {
    const m = matchIrpfToPeriod([], 2024);
    expect(m.anoBase).toBeNull();
  });
});

describe("getPgblCardStrategy", () => {
  it("default quando irpfKpis null", () => {
    const s = getPgblCardStrategy(null, 2024);
    expect(s.mode).toBe("default");
    expect(s.anoBase).toBeNull();
  });

  it("default quando primaryYear null", () => {
    const s = getPgblCardStrategy(KPIS_BASE, null);
    expect(s.mode).toBe("default");
  });

  it("informative-capacidade quando authoritative + capacidade_disponivel", () => {
    const s = getPgblCardStrategy(withStatus("capacidade_disponivel"), 2024);
    expect(s.mode).toBe("informative-capacidade");
    expect(s.anoBase).toBe(2024);
    expect(s.defasadoAnos).toBe(0);
  });

  it("informative-simplificado quando authoritative + modelo_simplificado", () => {
    const s = getPgblCardStrategy(withStatus("modelo_simplificado"), 2024);
    expect(s.mode).toBe("informative-simplificado");
  });

  it("informative-no-teto quando authoritative + no_teto", () => {
    const s = getPgblCardStrategy(withStatus("no_teto"), 2024);
    expect(s.mode).toBe("informative-no-teto");
  });

  it("informative-sem-renda quando authoritative + sem_renda_tributavel", () => {
    const s = getPgblCardStrategy(withStatus("sem_renda_tributavel"), 2024);
    expect(s.mode).toBe("informative-sem-renda");
  });

  it("authoritative com gap 1 (IRPF 2024 + análise 2025)", () => {
    const s = getPgblCardStrategy(withStatus("capacidade_disponivel"), 2025);
    expect(s.mode).toBe("informative-capacidade");
    expect(s.defasadoAnos).toBe(1);
  });

  it("default-defasado quando gap >= 2", () => {
    const s = getPgblCardStrategy(
      withStatus("capacidade_disponivel", { ano_base: 2022, anos_disponiveis: [2022] }),
      2024,
    );
    expect(s.mode).toBe("default-defasado");
    expect(s.anoBase).toBe(2022);
    expect(s.defasadoAnos).toBe(2);
  });

  it("default quando todos os anos > primaryYear + 1 (workspace pré-IRPF)", () => {
    const s = getPgblCardStrategy(
      withStatus("capacidade_disponivel", { ano_base: 2027, anos_disponiveis: [2027] }),
      2024,
    );
    expect(s.mode).toBe("default");
  });

  it("default quando matcher escolhe ano diferente do payload.ano_base (raro)", () => {
    // Backend escolheu 2024, mas matcher elegeria 2023 dado primaryYear=2022.
    // Defensivo: devolve default para evitar mostrar pgbl_status referente a 2024
    // num modo informativo que se diz sobre 2023.
    const kpis = withStatus("capacidade_disponivel", {
      ano_base: 2024,
      anos_disponiveis: [2023, 2024],
    });
    const s = getPgblCardStrategy(kpis, 2022);
    expect(s.mode).toBe("default");
  });
});

describe("isInformativeMode", () => {
  it("true para modos informative-*", () => {
    const informativos: PgblCardMode[] = [
      "informative-capacidade",
      "informative-simplificado",
      "informative-no-teto",
      "informative-sem-renda",
    ];
    informativos.forEach((m) => expect(isInformativeMode(m)).toBe(true));
  });

  it("false para default e default-defasado", () => {
    expect(isInformativeMode("default")).toBe(false);
    expect(isInformativeMode("default-defasado")).toBe(false);
  });
});
