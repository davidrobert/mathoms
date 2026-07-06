/**
 * A29.l1 — agrupamento de issues/linhas legacy da tela de conferência.
 * Fixture espelha o caso real do dogfood (run c3d37532): 7× período
 * implausível + 11× banco indeterminável, todas strings idênticas.
 */
import { describe, expect, it } from "vitest";

import {
  countReviewItems,
  groupIssuesByCode,
  groupLegacyLines,
  normalizeLegacyMessage,
} from "@/app/(app)/pipeline/runs/[runId]/reviews/_components/groupIssues";
import type { ValidationIssue } from "@/lib/api/pipeline";

const LEGACY_18 = [
  ...Array(7).fill(
    "periodo implausivel na normalizacao E3; documento requer revisao",
  ),
  ...Array(11).fill(
    "extrato sem banco determinavel; documento requer revisao",
  ),
].join("\n");

function issue(over: Partial<ValidationIssue>): ValidationIssue {
  return {
    code: "e16.pii.unmasked_cpf",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "msg",
    ...over,
  };
}

describe("groupLegacyLines", () => {
  it("18 linhas duplicadas → 2 grupos ordenados por tamanho", () => {
    const groups = groupLegacyLines(LEGACY_18);
    expect(groups).toHaveLength(2);
    expect(groups[0]!.lines).toHaveLength(11);
    expect(groups[0]!.representative).toMatch(/extrato sem banco/);
    expect(groups[1]!.lines).toHaveLength(7);
  });

  it("linhas que diferem só em índice/valor agrupam juntas", () => {
    const groups = groupLegacyLines(
      "dividas_onus[0] contém CPF\ndividas_onus[3] contém CPF\ncampo x vale 12,50\ncampo x vale 99,00",
    );
    expect(groups).toHaveLength(2);
    expect(groups[0]!.lines).toHaveLength(2);
  });

  it("null/vazio → sem grupos", () => {
    expect(groupLegacyLines(null)).toHaveLength(0);
    expect(groupLegacyLines("  \n ")).toHaveLength(0);
  });
});

describe("normalizeLegacyMessage", () => {
  it("neutraliza índices, números e espaços", () => {
    expect(normalizeLegacyMessage("a[12]  b 3,50")).toBe(
      normalizeLegacyMessage("a[7] b 900"),
    );
  });
});

describe("groupIssuesByCode", () => {
  it("agrupa por code, erros antes de avisos, maior grupo primeiro", () => {
    const issues = [
      issue({ code: "w.a", severity: "warning" }),
      issue({ code: "w.a", severity: "warning" }),
      issue({ code: "w.a", severity: "warning" }),
      issue({ code: "e.b", severity: "error" }),
    ];
    const groups = groupIssuesByCode(issues);
    expect(groups.map((g) => g.key)).toEqual(["e.b", "w.a"]);
    expect(groups[1]!.issues).toHaveLength(3);
  });

  it("legacy.unmigrated sub-agrupa por mensagem normalizada", () => {
    const issues = [
      issue({ code: "legacy.unmigrated", legacy_message: "periodo implausivel x" }),
      issue({ code: "legacy.unmigrated", legacy_message: "periodo implausivel y" }),
      issue({ code: "legacy.unmigrated", legacy_message: "banco vazio" }),
    ];
    // "x"/"y" diferem em texto (não em número) → grupos distintos; o ponto
    // é não colapsar tudo num grupo genérico único por code.
    const groups = groupIssuesByCode(issues);
    expect(groups.length).toBeGreaterThan(1);
  });
});

describe("countReviewItems", () => {
  it("issues estruturadas: separa erros e avisos", () => {
    const counts = countReviewItems(
      [issue({ severity: "error" }), issue({ severity: "warning" })],
      null,
    );
    expect(counts).toEqual({ total: 2, errors: 1, warnings: 1 });
  });

  it("fallback legacy: cada linha conta como erro", () => {
    const counts = countReviewItems(null, LEGACY_18);
    expect(counts).toEqual({ total: 18, errors: 18, warnings: 0 });
  });
});
