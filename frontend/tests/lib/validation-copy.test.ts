/**
 * Tests para `frontend/src/lib/validation-copy.ts` (ADR-165 onda 3).
 *
 * Cobre: dicionário, getCopy, formatCopy, summarizeIssues, fallbacks.
 */
import { describe, expect, it } from "vitest";

import {
  formatCopy,
  getCopy,
  summarizeIssues,
  UNKNOWN_CODE_COPY,
  VALIDATION_COPY,
} from "@/lib/validation-copy";
import type { ValidationIssue } from "@/lib/api/pipeline";

const issue = (
  code: string,
  severity: "error" | "warning" = "error",
  context: Record<string, string | number | boolean | null> = {},
): ValidationIssue => ({
  code,
  severity,
  path: "$.x",
  context,
  legacy_message: `legacy: ${code}`,
});

describe("getCopy", () => {
  it("retorna copy registrado para code conhecido", () => {
    const copy = getCopy("e16.pii.unmasked_cpf");
    expect(copy.title).toBe("Documento exposto na declaração");
    expect(copy.suggestedAction).toBe("Mascarar documento");
  });

  it("retorna UNKNOWN_CODE_COPY para code não registrado", () => {
    const copy = getCopy("does.not.exist");
    expect(copy).toBe(UNKNOWN_CODE_COPY);
  });

  it("legacy.unmigrated tem entrada explícita (não cai em UNKNOWN)", () => {
    const copy = getCopy("legacy.unmigrated");
    expect(copy).not.toBe(UNKNOWN_CODE_COPY);
    expect(copy.title).toBe("Item identificado pelo sistema");
  });
});

describe("VALIDATION_COPY coverage", () => {
  it("todos os codes E1.6 da onda 1 têm entrada", () => {
    const e16Codes = [
      "e16.pii.unmasked_cpf",
      "e16.reconcile.ir_pago_divergente",
      "e16.imposto.exclusivos_simultaneos",
      "e16.pgbl.deducao_em_simplificado",
      "e16.dependente.idade_acima_do_limite",
      "e16.confidence.out_of_range",
      "e16.contribuinte.exercicio_anterior_a_ano_base",
      "e16.contribuinte.exercicio_distante_de_ano_base",
    ];
    for (const code of e16Codes) {
      expect(VALIDATION_COPY).toHaveProperty(code);
    }
  });

  it("todos os codes E1/E1.5/E2-llm da onda 4 têm entrada", () => {
    const codes = [
      "e1.members.empty",
      "e1.member.invalid_key",
      "e1.titular.unknown_key",
      "e15.items.empty",
      "e15.item.missing_member_key",
      "e2llm.missing.source_file",
      "e2llm.transaction.invalid_date",
      "e2llm.investment.invalid_maturity_date",
    ];
    for (const code of codes) {
      expect(VALIDATION_COPY).toHaveProperty(code);
    }
  });

  it("todas as copies têm campos obrigatórios", () => {
    for (const [code, copy] of Object.entries(VALIDATION_COPY)) {
      expect(copy.title, `title vazio: ${code}`).toBeTruthy();
      expect(copy.cardSummary, `cardSummary vazio: ${code}`).toBeTruthy();
      expect(copy.description, `description vazio: ${code}`).toBeTruthy();
      expect(copy.suggestedAction, `suggestedAction vazio: ${code}`).toBeTruthy();
    }
  });
});

describe("formatCopy", () => {
  it("interpola chave presente no context", () => {
    const out = formatCopy("Olá ${nome}!", { nome: "Maria" });
    expect(out).toBe("Olá Maria!");
  });

  it("mantém placeholder literal quando chave ausente", () => {
    const out = formatCopy("X = ${y}", {});
    expect(out).toBe("X = ${y}");
  });

  it("mantém placeholder quando valor é null", () => {
    const out = formatCopy("X = ${y}", { y: null });
    expect(out).toBe("X = ${y}");
  });

  it("formata chaves _brl com Intl pt-BR (sem símbolo R$)", () => {
    const out = formatCopy("Valor R$ ${total_brl}", { total_brl: 1234.5 });
    expect(out).toBe("Valor R$ 1.234,50");
  });

  it("aceita string decimal em chave _brl", () => {
    const out = formatCopy("X = ${valor_brl}", { valor_brl: "999.99" });
    expect(out).toBe("X = 999,99");
  });

  it("retorna template inalterado quando não há placeholders", () => {
    const out = formatCopy("Sem interpolação aqui", { qualquer: "coisa" });
    expect(out).toBe("Sem interpolação aqui");
  });

  it("interpola números e booleanos como strings simples", () => {
    const out = formatCopy("idade=${idade} adulto=${adulto}", {
      idade: 25,
      adulto: true,
    });
    expect(out).toBe("idade=25 adulto=true");
  });
});

describe("summarizeIssues", () => {
  it("zero issues → frase vazia padrão", () => {
    expect(summarizeIssues([])).toBe("Sem itens para revisar.");
  });

  it("uma issue → cardSummary interpolado", () => {
    const i = issue("e16.pii.unmasked_cpf", "error", {
      section_label: "Dívidas e ônus",
    });
    const out = summarizeIssues([i]);
    expect(out).toContain("Dívidas e ônus");
  });

  it("N issues do mesmo code → '${N} ${title pluralizado}'", () => {
    const issues = [
      issue("e16.pii.unmasked_cpf", "error", { section_label: "A" }),
      issue("e16.pii.unmasked_cpf", "error", { section_label: "B" }),
      issue("e16.pii.unmasked_cpf", "error", { section_label: "C" }),
    ];
    const out = summarizeIssues(issues);
    expect(out).toMatch(/^3 documentos expostos/i);
  });

  it("codes mistos com errors + warnings → contagens + principal", () => {
    const issues = [
      issue("e16.pii.unmasked_cpf", "error", { section_label: "Bens" }),
      issue("e16.reconcile.ir_pago_divergente", "warning", {
        ir_pago_brl: "100",
        diff_brl: "20",
      }),
      issue("e16.dependente.idade_acima_do_limite", "warning", {
        nome: "X",
        idade: 30,
      }),
    ];
    const out = summarizeIssues(issues);
    expect(out).toMatch(/^1 erro \+ 2 avisos · principal:/);
  });

  it("codes mistos só com warnings → 'N itens · principal: X'", () => {
    const issues = [
      issue("e16.reconcile.ir_pago_divergente", "warning", {
        ir_pago_brl: "100",
        diff_brl: "20",
      }),
      issue("e16.dependente.idade_acima_do_limite", "warning", {
        nome: "X",
        idade: 30,
      }),
    ];
    const out = summarizeIssues(issues);
    expect(out).toMatch(/^2 itens para revisar · principal:/);
  });

  it("code desconhecido → cai em UNKNOWN_CODE_COPY (não quebra)", () => {
    const i = issue("totally.unknown.code");
    const out = summarizeIssues([i]);
    expect(out).toContain("Item para revisar");
  });
});
