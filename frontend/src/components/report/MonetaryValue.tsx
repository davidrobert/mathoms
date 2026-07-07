"use client";

import { cn } from "@/lib/cn";
import { ProvenancePopover } from "./provenance/ProvenancePopover";
import { useProvenanceEntry } from "./provenance/ReportProvenanceProvider";

// A33.l2 P4 (co-design product-designer 2026-07-07): EUR/GBP para contas
// multi-moeda Wise — Intl.NumberFormat já formata os símbolos.
export type Currency = "BRL" | "USD" | "EUR" | "GBP";

/** Onda 10 #1 — tamanhos canônicos para valores monetários cross-rota.
 *
 * - `hero`: número-protagonista (Patrimônio em /plano IFHeroCard,
 *   gauge equivalente no relatório). Display extra-bold 4xl.
 * - `kpi`: KPI de coluna ou card (PlanoKpiRow, ReservaEmergenciaCard).
 *   Mono bold 3.5xl — alinha em grade.
 * - `body`: default — herda o `font-size` do contêiner pai (cuidado
 *   regressivo: nenhum tamanho explícito é forçado, preservando
 *   call-sites pré-Onda 10).
 *
 * `hero`/`kpi` aplicam `text-style-*` do design-tokens (`tokens.css`
 * §text-style-hero/kpi-value). Cores via `signed` continuam agnósticas
 * ao size.
 */
export type MonetaryValueSize = "hero" | "kpi" | "body";

const SIZE_CLASS: Record<MonetaryValueSize, string> = {
  hero: "text-style-hero",
  kpi: "text-style-kpi-value",
  body: "font-mono",
};

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
  /** Tipografia canônica — ver `MonetaryValueSize`. Default: `body`. */
  size?: MonetaryValueSize;
  /** Tooltip nativo — útil em compact p/ exibir valor completo. */
  title?: string;
  className?: string;
  /** Test hook (Vitest/Playwright). */
  "data-testid"?: string;
  /** A25.l5 (ADR-279) — selo de proveniência N1. Ausente ⇒ render idêntico
   * (zero selo/handler). Presente, ativa selo+popover N2 SE o
   * `ReportProvenanceProvider` tiver dados para o campo (flag on). */
  provenance?: { fieldId: string };
}

/** F9 · ADR-076 · F1.1 + Onda 10 #1 — Exibe valor monetário com
 * tipografia canônica.
 *
 * Regras:
 * - tabular-nums para alinhamento em colunas
 * - locale pt-BR (vírgula decimal, ponto milhar)
 * - nullable safe: renderiza "—" se null/undefined
 * - `size` aplica `text-style-*` do design-tokens (família + size + weight)
 *
 * Uso:
 *   <MonetaryValue value={1234567.89} />              → corpo (mono sm)
 *   <MonetaryValue value={1234567.89} size="hero" />  → display 4xl
 *   <MonetaryValue value={-500} signed />             → em vermelho
 *   <MonetaryValue value={1_500_000} compact />       → R$ 1,50 mi
 *   <MonetaryValue value={null} />                    → —
 */
export function MonetaryValue({
  value,
  currency = "BRL",
  compact = false,
  hideSymbol = false,
  fractionDigits = 2,
  signed = false,
  size = "body",
  title,
  className,
  "data-testid": dataTestId,
  provenance,
}: MonetaryValueProps) {
  const provenanceEntry = useProvenanceEntry(provenance?.fieldId);
  const sizeClass = SIZE_CLASS[size];
  if (value === null || value === undefined || Number.isNaN(value)) {
    return (
      <span
        className={cn(sizeClass, "tabular-nums text-muted-foreground", className)}
        data-testid={dataTestId}
      >
        —
      </span>
    );
  }

  const locale = currency === "BRL" ? "pt-BR" : "en-US";
  const formatter = new Intl.NumberFormat(locale, {
    style: hideSymbol ? "decimal" : "currency",
    currency,
    notation: compact ? "compact" : "standard",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });

  const formatted = formatter.format(value);
  const colorClass = signed
    ? value > 0
      ? "text-gain"
      : value < 0
        ? "text-loss"
        : "text-muted-foreground"
    : undefined;

  if (provenanceEntry) {
    // Selo só nos dígitos: sinal +/− fica fora do sublinhado pontilhado.
    const negative = formatted.startsWith("-");
    const digits = negative ? formatted.slice(1) : formatted;
    return (
      <span
        className={cn(sizeClass, "tabular-nums", colorClass, className)}
        title={title}
        data-testid={dataTestId}
      >
        {signed && value > 0 ? "+" : ""}
        {negative ? "-" : ""}
        <ProvenancePopover entry={provenanceEntry} hero={size === "hero"}>
          {digits}
        </ProvenancePopover>
      </span>
    );
  }

  return (
    <span
      className={cn(sizeClass, "tabular-nums", colorClass, className)}
      title={title}
      data-testid={dataTestId}
    >
      {signed && value > 0 ? "+" : ""}
      {formatted}
    </span>
  );
}
