import type { ReactNode } from "react";

/** ADR-117 · Fase 3 — layouts de 2 colunas.
 *
 * - TwoColCards: grid 1fr 1fr simples (`.two-col`).
 * - SplitCards: grid 1fr 1fr com min-height equalizado (`.split-cards`).
 */
export function TwoColCards({
  children,
  gap = 20,
  className,
}: {
  readonly children: ReactNode;
  readonly gap?: number;
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap,
      }}
    >
      {children}
    </div>
  );
}

export function SplitCards({
  children,
  gap = 16,
  minHeight = 200,
  className,
}: {
  readonly children: ReactNode;
  readonly gap?: number;
  readonly minHeight?: number;
  readonly className?: string;
}) {
  return (
    <div
      className={className}
      data-split-cards
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap,
        alignItems: "stretch",
        ["--split-min-height" as string]: `${minHeight}px`,
      }}
    >
      {children}
    </div>
  );
}
