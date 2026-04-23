import { cn } from "@/lib/cn";

export type Currency = "BRL" | "USD";

interface MonetaryValueProps {
  value: number | null | undefined;
  currency?: Currency;
  /** Formata como número abreviado (1.2M, 850k). Default: false. */
  compact?: boolean;
  /** Esconde o símbolo da moeda — útil em tabelas densas. */
  hideSymbol?: boolean;
  /** Casas decimais. Default: 2. */
  fractionDigits?: number;
  /** Destaca sinal (verde positivo, vermelho negativo). */
  signed?: boolean;
  /** Tooltip nativo — útil em compact p/ exibir valor completo. */
  title?: string;
  className?: string;
}

/** F9 · ADR-076 · F1.1 — Exibe valor monetário com tipografia canônica.
 *
 * Regras:
 * - font-mono + tabular-nums para alinhamento em colunas
 * - locale pt-BR (vírgula decimal, ponto milhar)
 * - nullable safe: renderiza "—" se null/undefined
 *
 * Uso:
 *   <MonetaryValue value={1234567.89} />         → R$ 1.234.567,89
 *   <MonetaryValue value={-500} signed />        → em vermelho, com sinal
 *   <MonetaryValue value={1_500_000} compact />  → R$ 1,5 mi
 *   <MonetaryValue value={null} />               → —
 */
export function MonetaryValue({
  value,
  currency = "BRL",
  compact = false,
  hideSymbol = false,
  fractionDigits = 2,
  signed = false,
  title,
  className,
}: MonetaryValueProps) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className={cn("font-mono tabular-nums text-muted-foreground", className)}>—</span>;
  }

  const locale = currency === "BRL" ? "pt-BR" : "en-US";
  const formatter = new Intl.NumberFormat(locale, {
    style: hideSymbol ? "decimal" : "currency",
    currency,
    notation: compact ? "compact" : "standard",
    minimumFractionDigits: compact ? 0 : fractionDigits,
    maximumFractionDigits: compact ? 1 : fractionDigits,
  });

  const formatted = formatter.format(value);
  const colorClass = signed
    ? value > 0
      ? "text-gain"
      : value < 0
        ? "text-loss"
        : "text-muted-foreground"
    : undefined;

  return (
    <span className={cn("font-mono tabular-nums", colorClass, className)} title={title}>
      {signed && value > 0 ? "+" : ""}
      {formatted}
    </span>
  );
}
