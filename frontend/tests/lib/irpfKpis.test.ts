/**
 * Unit tests — ADR-157 · IRPF Full Schema · UI lane.
 *
 * Cobre o narrow guard `isIrpfKpis` (proteção contra shape inválido vindo
 * do snapshot E5) e `parseDecimalString` (conversão Decimal-string → number).
 */
import { describe, expect, it } from "vitest";
import { isIrpfKpis, parseDecimalString, type IrpfKpis } from "@/types/irpf";

const VALID_KPIS: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2022, 2023, 2024],
  renda_anual_familiar_brl: "150000.00",
  renda_liquida_familiar_brl: "120000.00",
  ir_pago_total_brl: "20000.00",
  aliquota_sobre_tributavel_pct: "17.50",
  aliquota_sobre_total_pct: "13.20",
  pgbl_capacidade_dedutivel_brl: "14000.00",
  split_trabalho_brl: "100000.00",
  split_capital_brl: "50000.00",
  evolucao_renda_anos: { "2022": "120000.00", "2023": "135000.00", "2024": "150000.00" },
};

describe("isIrpfKpis", () => {
  it("aceita shape canônico do _e5_kpis_from_analyzer", () => {
    expect(isIrpfKpis(VALID_KPIS)).toBe(true);
  });

  it("rejeita null/undefined/primitivos", () => {
    expect(isIrpfKpis(null)).toBe(false);
    expect(isIrpfKpis(undefined)).toBe(false);
    expect(isIrpfKpis(42)).toBe(false);
    expect(isIrpfKpis("foo")).toBe(false);
    expect(isIrpfKpis([])).toBe(false);
  });

  it("rejeita ano_base não numérico", () => {
    expect(isIrpfKpis({ ...VALID_KPIS, ano_base: "2024" })).toBe(false);
  });

  it("rejeita anos_disponiveis não-array", () => {
    expect(isIrpfKpis({ ...VALID_KPIS, anos_disponiveis: "2024" })).toBe(false);
  });

  it("rejeita anos_disponiveis com elementos não-numéricos", () => {
    expect(isIrpfKpis({ ...VALID_KPIS, anos_disponiveis: [2024, "2025"] })).toBe(false);
  });

  it("rejeita campo Decimal-string com tipo errado", () => {
    expect(isIrpfKpis({ ...VALID_KPIS, ir_pago_total_brl: 20000 })).toBe(false);
  });

  it("rejeita evolucao_renda_anos com valores não-string", () => {
    expect(
      isIrpfKpis({ ...VALID_KPIS, evolucao_renda_anos: { "2024": 150000 } }),
    ).toBe(false);
  });

  it("rejeita objeto faltando campo obrigatório", () => {
    const { aliquota_sobre_total_pct: _drop, ...partial } = VALID_KPIS;
    expect(isIrpfKpis(partial)).toBe(false);
  });
});

describe("parseDecimalString", () => {
  it("converte Decimal-string canônico", () => {
    expect(parseDecimalString("150000.00")).toBe(150000);
    expect(parseDecimalString("17.50")).toBe(17.5);
    expect(parseDecimalString("0")).toBe(0);
  });

  it("retorna null para inputs inválidos", () => {
    expect(parseDecimalString("")).toBeNull();
    expect(parseDecimalString("abc")).toBeNull();
    // @ts-expect-error — testando defesa runtime contra non-string
    expect(parseDecimalString(42)).toBeNull();
    // @ts-expect-error — testando defesa runtime contra null
    expect(parseDecimalString(null)).toBeNull();
  });

  it("aceita valores negativos", () => {
    expect(parseDecimalString("-1234.56")).toBe(-1234.56);
  });
});
