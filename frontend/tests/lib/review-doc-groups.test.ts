/**
 * A32.l6 PR3 — agrupamento por documento (visão default da review).
 * Critério da lane: run de 49 itens colapsa para a contagem real de
 * documentos-fonte; 1 doc órfão com 3 codes = 1 card, 1 decisão.
 */
import { describe, expect, it } from "vitest";

import type { ValidationIssue } from "@/lib/api/pipeline";
import { codeSubgroups, groupIssuesByDocument } from "@/lib/review-groups";

function issue(over: Partial<ValidationIssue>): ValidationIssue {
  return {
    code: "dedup.sentinel_period",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "msg",
    ...over,
  };
}

function docIssue(docId: string, code: string, severity: "error" | "warning" = "error") {
  return issue({
    code,
    severity,
    context: {
      document_id: docId,
      artifact_key: `f861374a39e9_c6bank_extratoconta_${docId}`,
      doc_bank_code: "c6bank",
      doc_type: "bank_statement",
      doc_e0_type: "extratoconta",
      doc_period: "202604",
    },
  });
}

describe("groupIssuesByDocument", () => {
  it("run de 49 itens colapsa para a contagem real de documentos-fonte", () => {
    // 7 docs × 7 issues (cascata) = 49 itens → 7 cards.
    const issues = Array.from({ length: 7 }).flatMap((_, d) =>
      Array.from({ length: 7 }).map((_, i) =>
        docIssue(`doc-${d}`, i % 2 === 0 ? "domain.balance_gap" : "domain.temporal_gap", "warning"),
      ),
    );
    expect(issues).toHaveLength(49);
    const groups = groupIssuesByDocument(issues);
    expect(groups).toHaveLength(7);
  });

  it("1 doc órfão com 3 codes = 1 card, 1 decisão", () => {
    const issues = [
      docIssue("doc-orfao", "extract.missing_required_field"),
      docIssue("doc-orfao", "dedup.sentinel_period"),
      docIssue("doc-orfao", "domain.anachronic_transaction", "warning"),
    ];
    const groups = groupIssuesByDocument(issues);
    expect(groups).toHaveLength(1);
    expect(groups[0]!.documentId).toBe("doc-orfao");
    expect(groups[0]!.severity).toBe("error");
    expect(codeSubgroups(groups[0]!)).toHaveLength(3);
  });

  it("rótulo do card é a identidade legível, nunca hash cru", () => {
    const groups = groupIssuesByDocument([docIssue("doc-1", "dedup.sentinel_period")]);
    expect(groups[0]!.label).toContain("C6 Bank");
    expect(groups[0]!.label).not.toMatch(/[0-9a-f]{12}_/);
  });

  it("sem document_id agrupa por artifact_key; cross-doc vai para 'Sequência de contas'", () => {
    const groups = groupIssuesByDocument([
      issue({ context: { artifact_key: "itau_extratoconta_202601" } }),
      issue({ context: { artifact_key: "itau_extratoconta_202601" } }),
      issue({
        code: "domain.balance_gap",
        severity: "warning",
        context: { artifact_key: "" },
      }),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[0]!.key).toBe("key:itau_extratoconta_202601");
    expect(groups[1]!.kind).toBe("cross_doc");
    expect(groups[1]!.label).toBe("Sequência de contas");
  });

  it("sentinela truncated vira grupo próprio no fim, sem ações", () => {
    const groups = groupIssuesByDocument([
      docIssue("doc-1", "domain.balance_gap", "warning"),
      issue({
        code: "domain.balance_gap",
        severity: "warning",
        context: { truncated: true, remaining: 10 },
        legacy_message: "e mais 10 ocorrencia(s) de domain.balance_gap",
      }),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[1]!.kind).toBe("truncated");
    expect(groups[1]!.label).toMatch(/e mais 10/);
  });

  it("erros ordenam antes de avisos; grupo maior primeiro", () => {
    const groups = groupIssuesByDocument([
      docIssue("doc-w", "domain.temporal_gap", "warning"),
      docIssue("doc-e", "dedup.sentinel_period", "error"),
      docIssue("doc-w", "domain.balance_gap", "warning"),
    ]);
    expect(groups.map((g) => g.documentId)).toEqual(["doc-e", "doc-w"]);
  });
});
