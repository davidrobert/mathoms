"use client";

/**
 * Inline de declaração de valor de mercado por imóvel (ADR-227 §D2 · Sprint A15 Onda 5b).
 *
 * Renderiza por imóvel locado/comercial: latest declaração + form para nova
 * entrada (POST append-only) + histórico com botão "marcar como erro"
 * (PATCH /supersede).
 */

import { useEffect, useState } from "react";

import { MonetaryValue } from "@/components/report/MonetaryValue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createPropertyMarketValue,
  listPropertyMarketValues,
  supersedePropertyMarketValue,
  type PropertyMarketValueResponse,
} from "@/lib/api/property-market-values";

export interface MarketValueInlineProps {
  workspaceId: string;
  propertyId: string;
  propertyLabel: string;
  /** Valor IRPF de referência (rendido pelo caller; mostrado como contraponto). */
  valorIrpfBrl?: number | null;
}

function _toNumber(value: string): number | null {
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : null;
}

function _todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function _findLatest(rows: PropertyMarketValueResponse[]): PropertyMarketValueResponse | null {
  return rows.find((r) => r.superseded_by_id === null) ?? null;
}

export function MarketValueInline({
  workspaceId,
  propertyId,
  propertyLabel,
  valorIrpfBrl,
}: MarketValueInlineProps) {
  const [rows, setRows] = useState<PropertyMarketValueResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [valor, setValor] = useState("");
  const [date, setDate] = useState(_todayIso());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = _findLatest(rows);

  const reload = async () => {
    setLoading(true);
    try {
      const data = await listPropertyMarketValues(workspaceId, { propertyId });
      setRows(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, propertyId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valor) return;
    setError(null);
    setSubmitting(true);
    try {
      await createPropertyMarketValue(workspaceId, {
        property_id: propertyId,
        valor_brl: valor,
        valuation_date: date,
      });
      setValor("");
      setDate(_todayIso());
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSupersede = async (row: PropertyMarketValueResponse) => {
    if (!latest || latest.id === row.id) return;
    await supersedePropertyMarketValue(workspaceId, row.id, latest.id);
    await reload();
  };

  return (
    <section
      aria-label={`Valor de mercado de ${propertyLabel}`}
      className="rounded-md border p-4 space-y-3"
      style={{ borderColor: "var(--surface-border)" }}
    >
      <header className="flex flex-col gap-1">
        <h3 className="text-sm font-medium">{propertyLabel}</h3>
        <div className="flex gap-4 text-xs" style={{ color: "var(--surface-muted-foreground)" }}>
          {valorIrpfBrl !== null && valorIrpfBrl !== undefined && (
            <span>
              IRPF: <MonetaryValue value={valorIrpfBrl} />
            </span>
          )}
          {latest && (
            <span>
              Mercado (mais recente, {latest.valuation_date}): <MonetaryValue value={_toNumber(latest.valor_brl)} />
            </span>
          )}
        </div>
      </header>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1 grid gap-1">
          <Label htmlFor={`mv-valor-${propertyId}`}>Novo valor de mercado (BRL)</Label>
          <Input
            id={`mv-valor-${propertyId}`}
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="1200000.00"
          />
        </div>
        <div className="grid gap-1">
          <Label htmlFor={`mv-date-${propertyId}`}>Data</Label>
          <Input
            id={`mv-date-${propertyId}`}
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={!valor || submitting}>
          {submitting ? "Salvando…" : "Declarar"}
        </Button>
      </form>

      {error && (
        <p role="alert" className="text-sm" style={{ color: "var(--semantic-danger)" }}>
          {error}
        </p>
      )}

      {!loading && rows.length > 1 && (
        <details className="text-sm">
          <summary
            className="cursor-pointer"
            style={{ color: "var(--surface-muted-foreground)" }}
          >
            Ver histórico ({rows.length} declarações)
          </summary>
          <ul className="mt-2 space-y-1 text-xs">
            {rows.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-2">
                <span>
                  {row.valuation_date} ·{" "}
                  <MonetaryValue value={_toNumber(row.valor_brl)} />{" "}
                  {row.superseded_by_id && <em>(corrigido)</em>}
                </span>
                {!row.superseded_by_id && latest && latest.id !== row.id && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSupersede(row)}
                  >
                    Marcar como erro
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
