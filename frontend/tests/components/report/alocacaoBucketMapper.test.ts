import { describe, expect, it } from "vitest";
import {
  aggregateAlocacao,
  type AlocacaoAlvoV1,
  type ClasseAtivoRow,
} from "@/components/report/utils/alocacaoBucketMapper";

const ALVO_60_30_5_5: AlocacaoAlvoV1 = {
  renda_fixa_pct: 60,
  acoes_pct: 30,
  imoveis_reits_pct: 5,
  liquidez_usd_pct: 5,
};

function rows(...entries: Array<[string, number]>): ClasseAtivoRow[] {
  return entries.map(([categoria, valor]) => ({ categoria, valor, pct: 0 }));
}

describe("aggregateAlocacao", () => {
  it("retorna total=0 e buckets vazios para entrada vazia", () => {
    const out = aggregateAlocacao([], ALVO_60_30_5_5, 0);
    expect(out.total).toBe(0);
    expect(out.total_investivel).toBe(0);
    expect(out.buckets).toHaveLength(4);
    expect(out.badge.severity).toBe("rebalancear");
  });

  it("sem alvo definido marca badge sem_alvo e desvio null", () => {
    const out = aggregateAlocacao(rows(["Renda Fixa", 100_000]), undefined, 100_000);
    expect(out.hasAlvo).toBe(false);
    expect(out.badge.severity).toBe("sem_alvo");
    expect(out.buckets.every((b) => b.desvio_pp === null)).toBe(true);
    expect(out.nextAporteBucket).toBeNull();
  });

  it("agrega Previdência em renda_fixa e Fundos em acoes", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 60_000],
        ["Previdência", 40_000],
        ["Ações BR", 50_000],
        ["Fundos", 50_000],
      ),
      undefined,
      200_000,
    );
    const rf = out.buckets.find((b) => b.id === "renda_fixa");
    const ac = out.buckets.find((b) => b.id === "acoes");
    expect(rf?.valor).toBe(100_000);
    expect(ac?.valor).toBe(100_000);
    expect(rf?.subItems).toEqual(expect.arrayContaining(["Renda Fixa", "Previdência"]));
    expect(ac?.subItems).toEqual(expect.arrayContaining(["Ações BR", "Fundos"]));
  });

  it("exclui Caixa do denominador do desvio (reserva ≠ investimento)", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 60_000],
        ["Ações BR", 30_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
        ["Caixa", 50_000],
      ),
      ALVO_60_30_5_5,
      150_000,
    );
    expect(out.total).toBe(150_000);
    expect(out.total_investivel).toBe(100_000);
    expect(out.reserva_caixa_valor).toBe(50_000);
    const rf = out.buckets.find((b) => b.id === "renda_fixa");
    expect(rf?.atual_pct).toBeCloseTo(60, 1);
    expect(rf?.desvio_pp).toBeCloseTo(0, 1);
    expect(rf?.severity).toBe("alinhado");
    const caixa = out.buckets.find((b) => b.id === "caixa");
    expect(caixa).toBeDefined();
    expect(caixa?.alvo_pct).toBeNull();
  });

  it("classifica Cripto e Outros como 'fora do alvo' (alvo=0)", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 60_000],
        ["Ações BR", 30_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
        ["Cripto", 6_000],
        ["Outros", 4_000],
      ),
      ALVO_60_30_5_5,
      110_000,
    );
    const fora = out.buckets.find((b) => b.id === "fora_alvo");
    expect(fora).toBeDefined();
    expect(fora?.valor).toBe(10_000);
    expect(fora?.alvo_pct).toBe(0);
    expect(fora?.desvio_pp).toBeGreaterThan(0);
    expect(fora?.subItems).toEqual(expect.arrayContaining(["Cripto", "Outros"]));
  });

  it("carteira alinhada (≤2pp todas) marca badge alinhado e maior desvio", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 61_000],
        ["Ações BR", 29_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
      ),
      ALVO_60_30_5_5,
      100_000,
    );
    expect(out.badge.severity).toBe("alinhado");
    expect(out.max_abs_desvio_pp).toBeLessThan(2);
  });

  it("carteira desalinhada (>5pp) marca badge rebalancear e cita classe sub-alocada", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 50_000],
        ["Ações BR", 40_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
      ),
      ALVO_60_30_5_5,
      100_000,
    );
    expect(out.badge.severity).toBe("rebalancear");
    expect(out.nextAporteBucket).toBe("renda_fixa");
    const rf = out.buckets.find((b) => b.id === "renda_fixa");
    expect(rf?.desvio_pp).toBeLessThan(0);
    expect(Math.abs(rf?.desvio_pp ?? 0)).toBeGreaterThan(5);
  });

  it("ordena linhas por |desvio| decrescente", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 50_000],
        ["Ações BR", 40_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
      ),
      ALVO_60_30_5_5,
      100_000,
    );
    const alvoIds = out.buckets
      .filter((b) => b.id !== "caixa" && b.id !== "fora_alvo")
      .map((b) => b.id);
    expect(alvoIds[0]).toBe("renda_fixa");
    expect(alvoIds[1]).toBe("acoes");
  });

  it("Caixa e fora_alvo aparecem por último na ordem visual", () => {
    const out = aggregateAlocacao(
      rows(
        ["Renda Fixa", 50_000],
        ["Ações BR", 30_000],
        ["FIIs", 5_000],
        ["Internacional", 5_000],
        ["Cripto", 5_000],
        ["Caixa", 5_000],
      ),
      ALVO_60_30_5_5,
      100_000,
    );
    expect(out.buckets[out.buckets.length - 1].id).toBe("caixa");
  });
});
