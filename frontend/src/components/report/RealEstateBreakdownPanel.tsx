"use client";

/**
 * Drill-down de imóvel gerador (ADR-227 §D3 apresentação dual · Sprint A15 Onda 5c).
 *
 * Modal/sidesheet com 4 colunas — Valor IRPF | Valor Mercado | Saldo
 * Devedor | Líquido — para acomodar o invariante "tabela cat_2 bruto;
 * líquido só em ``investivel_efetivo``" sem esconder a composição
 * econômica. Mobile: accordion com Líquido como header.
 */

import { useMemo } from "react";

import { MonetaryValue } from "@/components/report/MonetaryValue";
import { MarketValueStaleness } from "@/components/report/MarketValueStaleness";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export interface RealEstateBreakdownPanelProps {
  open: boolean;
  onClose: () => void;
  propertyLabel: string;
  valorIrpfBrl: number;
  valorMercadoBrl: number | null;
  saldoDevedorBrl: number;
  /** Dias desde valuation_date (ADR-227 §D5). */
  stalenessDays?: number | null;
}

function _liquido(valor: number, debt: number): number {
  return Math.max(0, valor - debt);
}

export function RealEstateBreakdownPanel({
  open,
  onClose,
  propertyLabel,
  valorIrpfBrl,
  valorMercadoBrl,
  saldoDevedorBrl,
  stalenessDays,
}: RealEstateBreakdownPanelProps) {
  const valorEfetivo = valorMercadoBrl ?? valorIrpfBrl;
  const liquido = useMemo(() => _liquido(valorEfetivo, saldoDevedorBrl), [valorEfetivo, saldoDevedorBrl]);

  return (
    <Dialog open={open} onOpenChange={(o) => (!o ? onClose() : null)}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{propertyLabel}</DialogTitle>
          <DialogDescription>
            Composição econômica completa do imóvel. A tabela de patrimônio reporta o valor
            bruto (declarado ou mercado) — o líquido econômico aparece apenas em &ldquo;Patrimônio
            investível efetivo&rdquo; para honrar o invariante de apresentação.
          </DialogDescription>
        </DialogHeader>

        <div className="hidden md:grid md:grid-cols-4 md:gap-4 md:py-4">
          <BreakdownColumn label="Valor IRPF" value={valorIrpfBrl} />
          <BreakdownColumn
            label="Valor Mercado"
            value={valorMercadoBrl}
            note={stalenessDays !== null && stalenessDays !== undefined ? (
              <MarketValueStaleness stalenessDays={stalenessDays} />
            ) : null}
          />
          <BreakdownColumn label="Saldo Devedor" value={saldoDevedorBrl} accent="negative" />
          <BreakdownColumn label="Líquido econômico" value={liquido} accent="primary" />
        </div>

        <details className="md:hidden">
          <summary className="cursor-pointer py-2 text-sm">
            <span style={{ color: "var(--surface-muted-foreground)" }}>
              Líquido econômico:
            </span>{" "}
            <strong>
              <MonetaryValue value={liquido} />
            </strong>
          </summary>
          <ul className="space-y-2 pt-3 text-sm">
            <li className="flex justify-between">
              <span>Valor IRPF</span>
              <MonetaryValue value={valorIrpfBrl} />
            </li>
            <li className="flex justify-between">
              <span>Valor Mercado</span>
              <MonetaryValue value={valorMercadoBrl} />
            </li>
            <li className="flex justify-between">
              <span>Saldo Devedor</span>
              <MonetaryValue value={saldoDevedorBrl} />
            </li>
          </ul>
        </details>

        <p
          className="text-xs"
          style={{ color: "var(--surface-muted-foreground)" }}
        >
          Metodologia: cat_2 (Imóveis de Renda) preserva valor bruto na tabela de patrimônio
          (consistência com cat_1 e veículos). Líquido econômico ={" "}
          <code>max(0, valor mercado − saldo devedor)</code> só entra em &ldquo;Patrimônio
          investível efetivo&rdquo;.
        </p>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface BreakdownColumnProps {
  label: string;
  value: number | null;
  accent?: "primary" | "negative";
  note?: React.ReactNode;
}

function BreakdownColumn({ label, value, accent, note }: BreakdownColumnProps) {
  const color =
    accent === "primary"
      ? "var(--brand-primary)"
      : accent === "negative"
        ? "var(--semantic-danger)"
        : "var(--surface-foreground)";
  return (
    <div className="space-y-1">
      <p
        className="text-xs uppercase tracking-wide"
        style={{ color: "var(--surface-muted-foreground)" }}
      >
        {label}
      </p>
      <p className="font-mono text-lg tabular-nums" style={{ color }}>
        <MonetaryValue value={value} />
      </p>
      {note}
    </div>
  );
}
