/**
 * Copy user-facing para ValidationIssue (ADR-165 onda 3).
 *
 * Convenções (docs/COPY_GUIDELINES.md):
 * - PT-BR, segunda pessoa de respeito.
 * - Sem jargão de implementação.
 * - Sem emoji, sem exclamação.
 * - Tom calmo mesmo em error.
 * - Descrições suportam interpolação ${chave} via formatCopy().
 *
 * Dicionários por stage vivem em `validation-copy.registry.ts` para manter
 * este arquivo abaixo do limite de 500 linhas (CLAUDE.md).
 */

import type { ValidationIssue } from "@/lib/api/pipeline";

import {
  E16_COPY,
  E1_COPY,
  E15_COPY,
  E2LLM_COPY,
  LEGACY_COPY,
  type ValidationCopy,
} from "./validation-copy.registry";

export type { ValidationCopy } from "./validation-copy.registry";

export type ValidationCode =
  | "e1.members.empty"
  | "e1.member.invalid_key"
  | "e1.member.duplicate_key"
  | "e1.member.empty_full_name"
  | "e1.member.empty_short_name"
  | "e1.member.unexpected_role"
  | "e1.member.invalid_cpf"
  | "e1.member.invalid_birth_date"
  | "e1.account.missing_institution"
  | "e1.account.non_standard_type"
  | "e1.titular.unknown_key"
  | "e1.titular.missing"
  | "e1.titular.multiple"
  | "e15.items.empty"
  | "e15.item.empty_code"
  | "e15.item.empty_description"
  | "e15.item.non_standard_category"
  | "e15.item.missing_member_key"
  | "e15.item.invalid_year"
  | "e15.totals.assets_mismatch"
  | "e15.totals.net_worth_mismatch"
  | "e15.contribuinte.invalid_reference_year"
  | "e2llm.missing.source_file"
  | "e2llm.missing.institution"
  | "e2llm.empty.no_data"
  | "e2llm.invalid_period_format"
  | "e2llm.transaction.invalid_date"
  | "e2llm.transaction.empty_description"
  | "e2llm.transaction.zero_amount"
  | "e2llm.investment.non_standard_type"
  | "e2llm.investment.missing_institution"
  | "e2llm.investment.non_positive_value"
  | "e2llm.investment.invalid_applied_date"
  | "e2llm.investment.invalid_maturity_date"
  | "e16.pii.unmasked_cpf"
  | "e16.reconcile.ir_pago_divergente"
  | "e16.imposto.exclusivos_simultaneos"
  | "e16.pgbl.deducao_em_simplificado"
  | "e16.dependente.idade_acima_do_limite"
  | "e16.confidence.out_of_range"
  | "e16.contribuinte.exercicio_anterior_a_ano_base"
  | "e16.contribuinte.exercicio_distante_de_ano_base"
  | "legacy.unmigrated";

export const VALIDATION_COPY: Record<ValidationCode, ValidationCopy> = {
  ...E1_COPY,
  ...E15_COPY,
  ...E2LLM_COPY,
  ...E16_COPY,
  "legacy.unmigrated": LEGACY_COPY,
} as Record<ValidationCode, ValidationCopy>;

export const UNKNOWN_CODE_COPY: ValidationCopy = {
  title: "Item identificado pelo sistema",
  cardSummary: "Item para revisar nesta etapa",
  description:
    "Este item ainda não tem descrição amigável nesta versão do app. " +
    "Veja o detalhe técnico abaixo para entender o que foi sinalizado.",
  suggestedAction: "Ver detalhes",
};

export function getCopy(code: string): ValidationCopy {
  return VALIDATION_COPY[code as ValidationCode] ?? UNKNOWN_CODE_COPY;
}

/** Interpola `${chave}` no template usando `context`. Chave ausente mantém o
 * placeholder literal (sinaliza copy quebrada melhor que vazio). Chaves `_brl`
 * são formatadas com Intl pt-BR (sem o símbolo R$). */
export function formatCopy(
  template: string,
  context: Record<string, unknown>,
): string {
  return template.replace(/\$\{(\w+)\}/g, (match, key: string) => {
    if (!(key in context)) return match;
    const value = context[key];
    if (value === null || value === undefined) return match;
    if (key.endsWith("_brl")) return formatBrlPlain(value);
    return String(value);
  });
}

function formatBrlPlain(value: unknown): string {
  const num =
    typeof value === "string"
      ? Number(value)
      : typeof value === "number"
        ? value
        : NaN;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

const PLURAL_OVERRIDES: Record<string, string> = {
  "Documento exposto na declaração": "Documentos expostos na declaração",
  "Imposto pago não bate com retenções": "Impostos pagos não batem com retenções",
  "Imposto a pagar e a restituir ao mesmo tempo":
    "Impostos a pagar e a restituir ao mesmo tempo",
  "Dependente acima do limite de idade": "Dependentes acima do limite de idade",
  "Indicador de confiança inválido": "Indicadores de confiança inválidos",
  "Exercício anterior ao ano-base": "Exercícios anteriores ao ano-base",
  "Distância incomum entre exercício e ano-base":
    "Distâncias incomuns entre exercício e ano-base",
  "Dedução de PGBL no modelo simplificado": "Deduções de PGBL no modelo simplificado",
  "Item identificado pelo sistema": "Itens identificados pelo sistema",
  "Item sem código": "Itens sem código",
  "Item sem descrição": "Itens sem descrição",
  "Categoria de item incomum": "Categorias de item incomuns",
  "Item sem dono identificado": "Itens sem dono identificado",
  "Ano-base do item inválido": "Anos-base de itens inválidos",
};

const ptPlural = (count: number, singular: string): string =>
  count === 1 ? singular : (PLURAL_OVERRIDES[singular] ?? `${singular}s`);

function summarizeSingleCode(issues: ValidationIssue[]): string {
  const copy = getCopy(issues[0]!.code);
  return `${issues.length} ${ptPlural(issues.length, copy.title).toLowerCase()}`;
}

function summarizeMixed(issues: ValidationIssue[]): string {
  const errors = issues.filter((i) => i.severity === "error");
  const warnings = issues.filter((i) => i.severity === "warning");
  const principal = errors[0] ?? warnings[0]!;
  const principalSummary = formatCopy(
    getCopy(principal.code).cardSummary,
    principal.context,
  );
  if (errors.length > 0 && warnings.length > 0) {
    const errLabel = errors.length === 1 ? "erro" : "erros";
    const warnLabel = warnings.length === 1 ? "aviso" : "avisos";
    return `${errors.length} ${errLabel} + ${warnings.length} ${warnLabel} · principal: ${principalSummary}`;
  }
  return `${issues.length} itens para revisar · principal: ${principalSummary}`;
}

/**
 * Resume um conjunto de ValidationIssue em uma frase única para o card.
 * 0 → "Sem itens..."; 1 → cardSummary; N mesmo code → "${N} ${plural}";
 * N mistos → contagens + principal.
 */
export function summarizeIssues(issues: ValidationIssue[]): string {
  if (issues.length === 0) return "Sem itens para revisar.";
  if (issues.length === 1) {
    return formatCopy(getCopy(issues[0]!.code).cardSummary, issues[0]!.context);
  }
  const codes = new Set(issues.map((i) => i.code));
  if (codes.size === 1) return summarizeSingleCode(issues);
  return summarizeMixed(issues);
}
