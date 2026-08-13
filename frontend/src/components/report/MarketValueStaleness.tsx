"use client";

/**
 * Badge de staleness de valor de mercado (ADR-227 §D5 · Sprint A15 Onda 5c).
 *
 * Soft TTL: nunca troca fonte automaticamente. Badge sinaliza ao usuário.
 * - 0-12m: sem badge (componente retorna null).
 * - 12-24m: ``warning`` — "atualizado há N meses".
 * - >24m: ``critical`` — "atualização há mais de 2 anos".
 */

import { Badge } from "@/components/ui/badge";

export interface MarketValueStalenessProps {
  /** Dias desde ``valuation_date`` (computado pelo backend ou caller). */
  stalenessDays: number;
}

function _monthsFromDays(days: number): number {
  return Math.floor(days / 30);
}

export function MarketValueStaleness({ stalenessDays }: MarketValueStalenessProps) {
  if (stalenessDays < 365) return null;
  const months = _monthsFromDays(stalenessDays);
  if (stalenessDays < 730) {
    return (
      <Badge
        variant="outline"
        // Par `-on-tint` (ADR-372 · A40.l33): o âmbar base sobre o card dava
        // 1,88:1 — texto e borda do badge eram um só tom ilegível. A variante
        // escura é da mesma família, então o nível "atenção" não muda.
        style={{
          borderColor: "var(--semantic-alert-on-tint)",
          color: "var(--semantic-alert-on-tint)",
        }}
      >
        Atualizado há {months} meses
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      style={{
        borderColor: "var(--semantic-danger)",
        color: "var(--semantic-danger)",
      }}
    >
      Atualização há mais de 2 anos
    </Badge>
  );
}
