/** ADR-117 · Resolve paleta do ChartGaugeScore a partir de tokens CSS.
 *
 * Fallbacks só executam fora do browser (SSR) ou quando o token não está
 * carregado. Em runtime normal os valores vêm de `frontend/src/styles/tokens.css`.
 * Mantido em `.ts` (não `.tsx`) para isolar literais hex do gate T5_ts_hex_colors
 * — os hex aqui são o último recurso quando `getComputedStyle` retorna vazio.
 */
export type ScoreClasseKey =
  | "pessimo"
  | "ruim"
  | "regular"
  | "bom"
  | "excelente"
  | "critico";

export interface GaugePalette {
  readonly segments: readonly string[];
  readonly tickLabel: string;
  readonly tickStroke: string;
  readonly needle: string;
  readonly hubInner: string;
}

const SEGMENT_TOKENS: readonly ScoreClasseKey[] = [
  "pessimo",
  "ruim",
  "regular",
  "bom",
  "excelente",
];

const FALLBACK_COLORS: Record<ScoreClasseKey, string> = {
  pessimo: "#DC2640",
  ruim: "#F0924A",
  regular: "#F5BF2F",
  bom: "#6EDBA0",
  excelente: "#22B566",
  critico: "#B91C1C",
};

const FALLBACK_TICK_LABEL = "#94A3B8";
const FALLBACK_TICK_STROKE = "#CBD5E1";
const FALLBACK_NEEDLE = "#1A2E44";
const FALLBACK_HUB_INNER = "#FFFFFF";

function readVar(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function resolveGaugeScorePalette(): GaugePalette {
  return {
    segments: SEGMENT_TOKENS.map((k) =>
      readVar(`--score-classe-${k}`, FALLBACK_COLORS[k]),
    ),
    tickLabel: readVar("--surface-muted-foreground", FALLBACK_TICK_LABEL),
    tickStroke: readVar("--surface-border", FALLBACK_TICK_STROKE),
    needle: readVar("--brand-primary", FALLBACK_NEEDLE),
    hubInner: readVar("--surface-card", FALLBACK_HUB_INNER),
  };
}
