/**
 * Frase de supressão do card Atual vs Alvo — lado TS do par. Lê a MESMA
 * fixture que `tests/test_e5n_narrativas_coerentes.py`: o narrador do E5N e o
 * card imprimem a mesma frase para o mesmo `motivo_supressao`.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  lerCausasDaSupressao,
  motivoDaSupressao,
  ressalvaDoTotal,
  rodapeDaSupressao,
} from "@/components/report/cards/alocacaoSupressao";

interface CasoDeFrase {
  readonly motivo: string;
  readonly frase: string;
}

const RODAPE: readonly CasoDeFrase[] = JSON.parse(
  readFileSync(
    path.resolve(
      __dirname,
      "../../../../tests/fixtures/narrativas/alocacao_supressao_frases.json",
    ),
    "utf8",
  ),
).rodape;

const rodape = (motivo: string): string =>
  rodapeDaSupressao(lerCausasDaSupressao(motivo));

describe("alocacaoSupressao — frase por motivo", () => {
  it("a fixture cobre os quatro slugs do produtor, um desconhecido e causas compostas", () => {
    const slugs = new Set(
      RODAPE.flatMap((c) =>
        c.motivo.split(";").map((p) => p.split(":")[0].trim()),
      ),
    );
    for (const slug of [
      "cobertura_incompleta",
      "nao_classificado",
      "balde_negativo",
      "valor_nao_apurado",
    ]) {
      expect(slugs.has(slug), slug).toBe(true);
    }
    expect(RODAPE.some((c) => c.motivo.includes(";"))).toBe(true);
  });

  it.each(RODAPE)("$motivo", ({ motivo, frase }) => {
    expect(rodape(motivo)).toBe(frase);
  });

  it.each(RODAPE)("cabe no rodapé do card (≤200): $motivo", ({ motivo }) => {
    expect(rodape(motivo).length).toBeLessThanOrEqual(200);
  });

  it("motivo sem causa legível ainda declara a supressão", () => {
    expect(rodape(" ; ")).toBe(
      "Não indicamos a classe do próximo aporte: parte do patrimônio está sem valor confiável.",
    );
  });
});

describe("motivoDaSupressao", () => {
  it("null e vazio contam como indicação emitida", () => {
    expect(motivoDaSupressao({ motivo_supressao: null })).toBeNull();
    expect(motivoDaSupressao({ motivo_supressao: "  " })).toBeNull();
    expect(motivoDaSupressao({})).toBeNull();
  });
});

describe("ressalvaDoTotal — só a cobertura tira valor do KPI", () => {
  it.each([
    [
      "cobertura_incompleta: conjuge",
      "Este total não inclui os investimentos do cônjuge.",
    ],
    [
      "cobertura_incompleta: titular, conjuge; nao_classificado: 4.0% da carteira",
      "Este total não inclui os investimentos do titular e do cônjuge.",
    ],
    ["nao_classificado: 5.1% da carteira", null],
    ["balde_negativo: veiculos", null],
    ["valor_nao_apurado: 2 item(ns)", null],
  ])("%s", (motivo, esperado) => {
    expect(ressalvaDoTotal(lerCausasDaSupressao(motivo))).toBe(esperado);
  });
});
