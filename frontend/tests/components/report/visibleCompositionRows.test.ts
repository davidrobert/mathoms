/**
 * A40.l71 (RV6-23) — predicado único da composição patrimonial.
 *
 * Um caso por estado (não um teste com N asserts: o primeiro a falhar
 * esconderia os outros), mais as duas provas por mutação da lane — a do balde
 * negativo, que é o desacordo medido no r6, e a do rename de categoria, que é
 * o modo de falha silencioso do filtro da ADR-215 P5.
 */
import { describe, expect, it } from "vitest";

import {
  CATEGORIA_RESIDENCIA_LABEL,
  donutSlices,
  visibleCompositionRows,
} from "@/components/report/utils/visibleCompositionRows";
import type { PatrimonioData } from "@/types/report-analysis";

function patrimonio(
  composicao: { categoria: string; valor: number; pct: number }[],
): PatrimonioData {
  return { composicao } as PatrimonioData;
}

const NEGATIVO = { categoria: "Imóveis de Renda", valor: -200_000, pct: 0 };
const POSITIVO = { categoria: "Veículos", valor: 50_000, pct: 100 };
const ZERO = { categoria: "Investimentos Cônjuge", valor: 0, pct: 0 };

describe("visibleCompositionRows — um estado por caso", () => {
  it("valor positivo é `apurado` e vira fatia do donut", () => {
    const rows = visibleCompositionRows(patrimonio([POSITIVO]));

    expect(rows.map((r) => r.state)).toEqual(["apurado"]);
    expect(donutSlices(rows)).toEqual([{ label: "Veículos", value: 50_000 }]);
  });

  it("valor negativo é `negativo`: fica na tabela e sai do donut", () => {
    const rows = visibleCompositionRows(patrimonio([NEGATIVO]));

    expect(rows.map((r) => r.state)).toEqual(["negativo"]);
    expect(rows[0].valor).toBe(-200_000);
    expect(donutSlices(rows)).toEqual([]);
  });

  it("zero sem cobertura é `nao_apurado` — nunca `zero_apurado`", () => {
    const rows = visibleCompositionRows(patrimonio([ZERO]));

    expect(rows.map((r) => r.state)).toEqual(["nao_apurado"]);
    expect(donutSlices(rows)).toEqual([]);
  });

  it("zero COM cobertura é `zero_apurado` — o caminho de saída da ressalva", () => {
    const rows = visibleCompositionRows(
      patrimonio([ZERO]),
      new Set([ZERO.categoria]),
    );

    expect(rows.map((r) => r.state)).toEqual(["zero_apurado"]);
  });

  it("residência zerada não vira linha (ADR-215 P5)", () => {
    const rows = visibleCompositionRows(
      patrimonio([{ categoria: CATEGORIA_RESIDENCIA_LABEL, valor: 0, pct: 0 }]),
    );

    expect(rows).toEqual([]);
  });
});

describe("visibleCompositionRows — provas por mutação", () => {
  // O desacordo do r6: sobre o MESMO payload o donut sumia com o balde e a
  // tabela o imprimia. Agora as duas projeções saem da mesma classificação, e
  // a assimetria é a declarada (área negativa não é representável no donut).
  it("balde negativo: donut e tabela deixam de discordar por acidente", () => {
    const rows = visibleCompositionRows(patrimonio([NEGATIVO, POSITIVO]));

    expect(rows).toHaveLength(2);
    expect(rows.find((r) => r.categoria === NEGATIVO.categoria)?.state).toBe(
      "negativo",
    );
    expect(donutSlices(rows).map((s) => s.label)).toEqual(["Veículos"]);
  });

  // Mutação re-especificada vs. a lane: o payload NÃO carrega o `template_key`
  // da ADR-145 (só o rótulo — `patrimonio_calculator.py:455`), então renomear a
  // categoria no fixture continua desligando o filtro, aqui e em produção. O
  // que a lane queria — rename não desliga em silêncio — é entregue pelo gate
  // `dev/check_composicao_predicate.py`, que quebra no commit do produtor.
  // Este teste PINA a dependência: se alguém a mudar, é decisão, não deriva.
  it("rename da residência desliga o filtro — por isso o gate de paridade existe", () => {
    const renomeada = visibleCompositionRows(
      patrimonio([{ categoria: "Residencia", valor: 0, pct: 0 }]),
    );

    expect(renomeada).toHaveLength(1);
    expect(renomeada[0].state).toBe("nao_apurado");
  });
});

describe("visibleCompositionRows — fallbacks de leitura", () => {
  it("cai em tabela_categorias quando composicao falta", () => {
    const data = { tabela_categorias: [POSITIVO] } as PatrimonioData;

    expect(visibleCompositionRows(data).map((r) => r.categoria)).toEqual([
      "Veículos",
    ]);
  });

  it("payload ausente devolve lista vazia, não estoura", () => {
    expect(visibleCompositionRows(undefined)).toEqual([]);
  });
});
