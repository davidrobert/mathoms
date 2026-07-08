/**
 * A32.l6 PR2 — taxonomia de natureza + teste de contradição.
 *
 * Critérios da lane: cada um dos 6 codes E3 tem natureza atribuída; nenhum
 * card nega fato presente nos dados que o próprio card recebe (caso
 * `banco=''` ao lado do nome do banco resolvido pelo PR1).
 */
import { describe, expect, it } from "vitest";

import {
  NATURE_SPEC,
  REVIEW_REASON_NATURE,
  natureForCode,
  natureLabelForCode,
} from "@/lib/review-nature";
import { translateOffendingValue } from "@/lib/review-offending-value";
import { REVIEW_REASON_COPY } from "@/lib/validation-copy.registry";
import { formatCopy } from "@/lib/validation-copy";

/** Context com identidade totalmente resolvida (PR1) — os fatos que o
 * sistema TEM e que a copy não pode negar. */
const RESOLVED_CONTEXT = {
  artifact_key: "f861374a39e9_c6bank_extratoconta_202604",
  document_id: "doc-1",
  doc_bank_code: "c6bank",
  doc_type: "bank_statement",
  doc_e0_type: "extratoconta",
  doc_period: "202604",
  offending_value: "banco=''",
  expected: "campo banco/institution nao-vazio no artefato E2",
};

/** Frases que negam conhecimento de fato presente no DB/context. */
const DENIAL_PATTERNS = [
  // Nega saber a instituição enquanto o card mostra o banco resolvido.
  /n[ãa]o (foi poss[íi]vel|conseguimos|sabemos) (dizer|identificar|saber)[^.]*\b(banco|corretora|institui[çc][ãa]o)/i,
  /sem banco ou corretora/i,
  /documento sem banco/i,
  // Nega saber o período enquanto documents.period está correto no DB.
  /n[ãa]o (foi poss[íi]vel|conseguimos|sabemos) (dizer|identificar|saber)[^.]*\bper[íi]odo\b/i,
];

describe("REVIEW_REASON_NATURE — completude", () => {
  it("cada um dos 6 codes E3 do copy registry tem natureza atribuída", () => {
    const copyCodes = Object.keys(REVIEW_REASON_COPY).sort();
    const natureCodes = Object.keys(REVIEW_REASON_NATURE).sort();
    expect(copyCodes).toHaveLength(6);
    expect(natureCodes).toEqual(copyCodes);
  });

  it("as 3 naturezas têm rótulos distintos (distinção não depende de cor)", () => {
    const labels = Object.values(NATURE_SPEC).map((s) => s.label);
    expect(new Set(labels).size).toBe(3);
  });

  it("codes de atribuição incerta recebem hedge 'provável'", () => {
    expect(natureLabelForCode("extract.missing_required_field")).toMatch(/^Provável/);
    expect(natureLabelForCode("domain.balance_gap")).toMatch(/^Provável/);
    expect(natureLabelForCode("dedup.sentinel_period")).toBe("Falha na nossa leitura");
    expect(natureLabelForCode("domain.temporal_gap")).toBe("Documento faltando");
  });

  it("code desconhecido → sem natureza, sem selo", () => {
    expect(natureForCode("e16.pii.unmasked_cpf")).toBeNull();
    expect(natureLabelForCode("qualquer.coisa")).toBeNull();
  });
});

describe("teste de contradição — copy nunca nega fato que o card recebe", () => {
  for (const [code, copy] of Object.entries(REVIEW_REASON_COPY)) {
    it(`${code}: card com identidade resolvida não nega banco/período`, () => {
      const cardText = [
        copy.title,
        formatCopy(copy.cardSummary, RESOLVED_CONTEXT),
        formatCopy(copy.description, RESOLVED_CONTEXT),
        copy.whyItMatters ?? "",
      ].join(" ");
      for (const pattern of DENIAL_PATTERNS) {
        expect(cardText).not.toMatch(pattern);
      }
    });
  }

  it("quando o defeito provável é nosso, a copy assume em vez de culpar o dado", () => {
    for (const code of [
      "extract.missing_required_field",
      "dedup.sentinel_period",
      "domain.anachronic_transaction",
    ]) {
      const copy = REVIEW_REASON_COPY[code]!;
      expect(`${copy.description}`).toMatch(/noss[ao]/i);
    }
  });
});

describe("translateOffendingValue — valor cru nunca exibido sem tradução", () => {
  it("campo vazio vira frase, não `banco=''`", () => {
    expect(translateOffendingValue("banco=''")).toBe(
      "O campo de instituição veio em branco na nossa leitura.",
    );
  });

  it("datas ISO viram dd/mm/aaaa", () => {
    expect(
      translateOffendingValue("9 dias sem extrato em c6bank/corrente/-/BRL (2026-04-30 → 2026-05-09)"),
    ).toBe("9 dias sem extrato em c6bank/corrente/-/BRL (30/04/2026 → 09/05/2026)");
  });

  it("artifact_keys embutidos perdem o prefixo sha256", () => {
    const out = translateOffendingValue(
      "descontinuidade de saldo em c6bank/corrente entre f861374a39e9_c6bank_202601 e f861374a39e9_c6bank_202603",
    );
    expect(out).not.toMatch(/[0-9a-f]{12}_/);
    expect(out).toContain("c6bank_202601");
  });

  it("vazio/não-string → null (linha não renderiza)", () => {
    expect(translateOffendingValue("")).toBeNull();
    expect(translateOffendingValue(null)).toBeNull();
    expect(translateOffendingValue(undefined)).toBeNull();
    expect(translateOffendingValue(42)).toBeNull();
  });
});
