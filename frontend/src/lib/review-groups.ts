import type { ValidationIssue } from "@/lib/api/pipeline";

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
