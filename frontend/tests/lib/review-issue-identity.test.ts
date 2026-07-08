/**
 * A32.l6 PR1 — identidade legível do documento no card de review.
 * Zero hash sha256 cru no corpo visível: o rótulo da ocorrência nunca
 * contém o prefixo content-addressed (ADR-084).
 */
import { describe, expect, it } from "vitest";

import type { ValidationIssue } from "@/lib/api/pipeline";
import {
  CROSS_DOC_LABEL,
  humanizeArtifactKey,
  issueDocumentId,
  issueDocumentLabel,
  occurrenceIdentityLabel,
} from "@/lib/review-issue-identity";

const HASH_PREFIX = /[0-9a-f]{12}_/;

function issue(context: ValidationIssue["context"]): ValidationIssue {
  return {
    code: "dedup.sentinel_period",
    severity: "error",
    path: null,
    context,
    legacy_message: "periodo implausivel na normalizacao E3",
  };
}

describe("issueDocumentLabel", () => {
  it("monta 'Instituição · Tipo · Período' da identidade projetada", () => {
    const label = issueDocumentLabel(
      issue({
        document_id: "doc-1",
        doc_bank_code: "c6bank",
        doc_type: "bank_statement",
        doc_e0_type: "extratoconta",
        doc_period: "202604",
      }),
    );
    expect(label).toContain("C6 Bank");
    expect(label).toContain("Extrato");
    expect(label).not.toMatch(HASH_PREFIX);
  });

  it("sem identidade no context → null", () => {
    expect(issueDocumentLabel(issue({ artifact_key: "x" }))).toBeNull();
  });
});

describe("issueDocumentId", () => {
  it("retorna a FK quando presente; null quando ausente", () => {
    expect(issueDocumentId(issue({ document_id: "doc-9" }))).toBe("doc-9");
    expect(issueDocumentId(issue({ document_id: null }))).toBeNull();
    expect(issueDocumentId(issue({}))).toBeNull();
  });
});

describe("humanizeArtifactKey", () => {
  it("remove prefixo sha256[:12] e sufixo de stage", () => {
    expect(
      humanizeArtifactKey("f861374a39e9_c6bank_extratoconta_202604-3_reconciled.json"),
    ).toBe("c6bank_extratoconta_202604");
  });

  it("key sem prefixo/sufixo passa intacta", () => {
    expect(humanizeArtifactKey("itau_BRL_202601_202604")).toBe("itau_BRL_202601_202604");
  });
});

describe("occurrenceIdentityLabel", () => {
  it("prefere identidade do documento sobre artifact_key", () => {
    const label = occurrenceIdentityLabel(
      issue({
        artifact_key: "f861374a39e9_c6bank_extratoconta_202604",
        doc_bank_code: "c6bank",
        doc_e0_type: "extratoconta",
        doc_period: "202604",
        doc_type: "bank_statement",
      }),
    );
    expect(label).toContain("C6 Bank");
    expect(label).not.toMatch(HASH_PREFIX);
  });

  it("fallback: artifact_key humanizado, nunca com hash", () => {
    const label = occurrenceIdentityLabel(
      issue({ artifact_key: "f861374a39e9_c6bank_extratoconta_202604" }),
    );
    expect(label).toBe("c6bank_extratoconta_202604");
    expect(label).not.toMatch(HASH_PREFIX);
  });

  it("cross-doc com artifact_key vazio → grupo 'Sequência de contas'", () => {
    expect(occurrenceIdentityLabel(issue({ artifact_key: "" }))).toBe(CROSS_DOC_LABEL);
  });

  it("sem context útil → mensagem técnica original", () => {
    expect(occurrenceIdentityLabel(issue({}))).toBe(
      "periodo implausivel na normalizacao E3",
    );
  });
});
