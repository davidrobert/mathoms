/**
 * Tradução do `offending_value` cru para linguagem humana (A32.l6 PR2).
 *
 * O valor ofensor nunca aparece cru no corpo visível do card: `banco=''`
 * vira frase, datas ISO viram dd/mm/aaaa, artifact_keys embutidos perdem o
 * prefixo sha256. O valor original permanece sob "Detalhes técnicos".
 */

import { humanizeArtifactKey } from "@/lib/review-issue-identity";

const ISO_DATE_RE = /\b(\d{4})-(\d{2})-(\d{2})\b/g;
const EMBEDDED_HASH_RE = /\b[0-9a-f]{12}_/g;
const EMPTY_FIELD_RE = /^(\w+)=''$/;

/** Nomes de campo do domínio → rótulo humano. */
const FIELD_LABELS: Record<string, string> = {
  banco: "instituição",
  tipo: "tipo de documento",
  periodo: "período",
};

function formatIsoDates(text: string): string {
  return text.replace(ISO_DATE_RE, (_m, y: string, mo: string, d: string) => `${d}/${mo}/${y}`);
}

/**
 * Traduz o valor ofensor cru em frase exibível; `null` quando não há valor
 * (o chamador simplesmente não renderiza a linha).
 */
export function translateOffendingValue(value: unknown): string | null {
  if (typeof value !== "string" || value.trim().length === 0) return null;
  const emptyField = EMPTY_FIELD_RE.exec(value.trim());
  if (emptyField?.[1]) {
    const label = FIELD_LABELS[emptyField[1].toLowerCase()] ?? emptyField[1];
    return `O campo de ${label} veio em branco na nossa leitura.`;
  }
  const withoutHashes = value.replace(EMBEDDED_HASH_RE, "");
  const humanized = withoutHashes
    .split(" ")
    .map((token) => (token.endsWith(".json") ? humanizeArtifactKey(token) : token))
    .join(" ");
  return formatIsoDates(humanized);
}
