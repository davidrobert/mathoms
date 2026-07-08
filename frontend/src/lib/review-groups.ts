import type { ValidationIssue } from "@/lib/api/pipeline";
import {
  CROSS_DOC_LABEL,
  issueDocumentId,
  issueDocumentLabel,
  occurrenceIdentityLabel,
} from "@/lib/review-issue-identity";

export interface IssueGroup {
  key: string;
  severity: "error" | "warning";
  issues: ValidationIssue[];
}

export interface LegacyGroup {
  key: string;
  representative: string;
  lines: string[];
}

/** Chave de dedup para mensagens legacy: índices e números viram placeholders
 * para que ocorrências do mesmo problema em documentos diferentes agrupem. */
export function normalizeLegacyMessage(message: string): string {
  return message
    .replace(/\[\d+\]/g, "[]")
    .replace(/\d+([.,]\d+)?/g, "#")
    .replace(/\s+/g, " ")
    .trim();
}

function groupKey(issue: ValidationIssue): string {
  if (issue.code === "legacy.unmigrated") {
    return `legacy:${normalizeLegacyMessage(issue.legacy_message)}`;
  }
  return issue.code;
}

/** Agrupa issues estruturadas por code (issues legacy agrupam por mensagem
 * normalizada — senão 18 itens colapsam num grupo genérico único).
 * Ordem: erros antes de avisos; dentro, maior grupo primeiro. */
export function groupIssuesByCode(issues: ValidationIssue[]): IssueGroup[] {
  const map = new Map<string, ValidationIssue[]>();
  for (const issue of issues) {
    const key = groupKey(issue);
    map.set(key, [...(map.get(key) ?? []), issue]);
  }
  const groups: IssueGroup[] = [...map.entries()].map(([key, items]) => ({
    key,
    severity: items.some((i) => i.severity === "error") ? "error" : "warning",
    issues: items,
  }));
  return groups.sort(compareGroups);
}

function compareGroups(
  a: { severity: string; issues?: unknown[]; lines?: unknown[] },
  b: { severity: string; issues?: unknown[]; lines?: unknown[] },
): number {
  if (a.severity !== b.severity) return a.severity === "error" ? -1 : 1;
  const sizeA = (a.issues ?? a.lines ?? []).length;
  const sizeB = (b.issues ?? b.lines ?? []).length;
  return sizeB - sizeA;
}

/** Agrupa a string legacy `validation_errors` (linhas duplicadas por
 * documento) em grupos com contador. */
export function groupLegacyLines(errors: string | null): LegacyGroup[] {
  const lines = (errors ?? "")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const map = new Map<string, string[]>();
  for (const line of lines) {
    const key = normalizeLegacyMessage(line);
    map.set(key, [...(map.get(key) ?? []), line]);
  }
  return [...map.entries()]
    .map(([key, group]) => ({ key, representative: group[0]!, lines: group }))
    .sort((a, b) => b.lines.length - a.lines.length);
}

/** Contagens para hierarquia de ações e h1 — linhas legacy contam como erro
 * (vêm de `validation.errors`, que marca `valid=false`). */
export function countReviewItems(
  issues: ValidationIssue[] | null,
  errorsLegacy: string | null,
): { total: number; errors: number; warnings: number } {
  if (issues && issues.length > 0) {
    const errors = issues.filter((i) => i.severity === "error").length;
    return { total: issues.length, errors, warnings: issues.length - errors };
  }
  const lines = (errorsLegacy ?? "")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  return { total: lines.length, errors: lines.length, warnings: 0 };
}

// ── Agrupamento por documento (A32.l6 PR3) ─────────────────────────────────
//
// Visão default da tela de review: cascatas do mesmo documento colapsam em
// 1 card, 1 decisão. Render-side puro — granularidade de StageReview e o
// contrato do backend não mudam. A visão por-code (acima) vira toggle.

export type DocumentGroupKind = "document" | "cross_doc" | "truncated";

export interface DocumentIssueGroup {
  key: string;
  /** Rótulo legível do card — identidade do documento, nunca hash cru. */
  label: string;
  documentId: string | null;
  severity: "error" | "warning";
  kind: DocumentGroupKind;
  issues: ValidationIssue[];
}

function contextString(issue: ValidationIssue, key: string): string | null {
  const value = issue.context[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

type DocumentGroupSeed = Pick<
  DocumentIssueGroup,
  "key" | "label" | "documentId" | "kind"
>;

function truncatedSeed(issue: ValidationIssue): DocumentGroupSeed {
  return {
    key: `truncated:${issue.code}`,
    label: issue.legacy_message,
    documentId: null,
    kind: "truncated",
  };
}

function documentSeed(issue: ValidationIssue, documentId: string): DocumentGroupSeed {
  return {
    key: `doc:${documentId}`,
    label: issueDocumentLabel(issue) ?? occurrenceIdentityLabel(issue),
    documentId,
    kind: "document",
  };
}

function artifactKeySeed(issue: ValidationIssue, artifactKey: string): DocumentGroupSeed {
  return {
    key: `key:${artifactKey}`,
    label: occurrenceIdentityLabel(issue),
    documentId: null,
    kind: "document",
  };
}

function documentGroupSeed(issue: ValidationIssue): DocumentGroupSeed {
  if (issue.context["truncated"] === true) return truncatedSeed(issue);
  const documentId = issueDocumentId(issue);
  if (documentId) return documentSeed(issue, documentId);
  const artifactKey = contextString(issue, "artifact_key");
  if (artifactKey) return artifactKeySeed(issue, artifactKey);
  return { key: "cross-doc", label: CROSS_DOC_LABEL, documentId: null, kind: "cross_doc" };
}

function compareDocumentGroups(a: DocumentIssueGroup, b: DocumentIssueGroup): number {
  if (a.kind === "truncated" || b.kind === "truncated") {
    return a.kind === b.kind ? 0 : a.kind === "truncated" ? 1 : -1;
  }
  if (a.severity !== b.severity) return a.severity === "error" ? -1 : 1;
  if (a.issues.length !== b.issues.length) return b.issues.length - a.issues.length;
  return a.label.localeCompare(b.label, "pt-BR");
}

/** Agrupa issues pelo documento de origem (document_id → artifact_key →
 * balde cross-doc). Cascata de N codes do mesmo doc = 1 grupo. */
export function groupIssuesByDocument(issues: ValidationIssue[]): DocumentIssueGroup[] {
  const map = new Map<string, DocumentIssueGroup>();
  for (const issue of issues) {
    const seed = documentGroupSeed(issue);
    const existing = map.get(seed.key);
    if (existing) {
      existing.issues.push(issue);
      if (issue.severity === "error") existing.severity = "error";
    } else {
      map.set(seed.key, { ...seed, severity: issue.severity, issues: [issue] });
    }
  }
  return [...map.values()].sort(compareDocumentGroups);
}

/** Sub-grupos por code dentro de um grupo-documento, erros primeiro. */
export function codeSubgroups(group: DocumentIssueGroup): IssueGroup[] {
  return groupIssuesByCode(group.issues);
}
