import type { FluxoJanelaInterativa } from "@/types/report-analysis";

const MONTHS = [
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
] as const;

function formatMonth(value: string | null): string | null {
  const match = /^(\d{4})-(\d{2})$/.exec(value ?? "");
  if (!match) return null;
  const month = Number(match[2]);
  if (month < 1 || month > 12) return null;
  return `${MONTHS[month - 1]}/${match[1].slice(2)}`;
}

/** Base temporal curta, impressa junto ao agregado selecionado. */
export function formatInteractiveWindowBasis(
  janela: Pick<
    FluxoJanelaInterativa,
    "janela_meses" | "mes_inicio" | "mes_fim"
  >,
): string {
  const count =
    janela.janela_meses === 1
      ? "1 mês documentado"
      : `${janela.janela_meses} meses documentados`;
  const start = formatMonth(janela.mes_inicio);
  const end = formatMonth(janela.mes_fim);
  if (!start || !end) return count;
  if (start === end) return `${count} · ${start}`;
  return `${count} · ${start} — ${end}`;
}
