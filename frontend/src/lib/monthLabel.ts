// Rótulo curto de mês em pt-BR. Extraído de `format.ts` na F5 porque o
// arquivo cruzou 500 linhas (CLAUDE.md §Code style) — o gate
// `code-style-baseline` reprova, e mês é uma responsabilidade coesa o
// bastante para viver sozinha.

export const MONTH_SHORT_PT_LOWER = [
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

/** Timestamp ISO → mês curto pt-BR ("2026-08-11T00:00:00Z" → "ago/2026").
 *
 * Lê as partes em **UTC**, não em local: o rótulo é um balde de mês, e um
 * registro criado à meia-noite UTC apareceria no mês anterior para quem está
 * em UTC-3 — o inbox mostraria "jul" para uma sugestão de agosto. Fora isso,
 * fixa o valor em teste sem depender do TZ da máquina.
 * Retorna "—" para input ausente ou não-parseável. */
export function formatMonthShortPtBR(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${MONTH_SHORT_PT_LOWER[d.getUTCMonth()]}/${d.getUTCFullYear()}`;
}
