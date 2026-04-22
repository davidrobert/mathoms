"use client";

import { ArrowLeftRight, Download, TrendingDown, TrendingUp } from "lucide-react";
import type { TransactionSummary } from "@/lib/api";
import { formatCurrency, formatDateShort } from "@/lib/format";
import { cn } from "@/lib/cn";

function KpiCard({
  icon: Icon,
  label,
  value,
  valueClass,
}: {
  icon: typeof TrendingUp;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <div>
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className={cn("text-sm font-semibold tabular-nums", valueClass)}>{value}</p>
      </div>
    </div>
  );
}

export function SummaryBar({ summary }: { summary: TransactionSummary }) {
  const saldoClass = summary.saldo >= 0 ? "text-gain" : "text-loss";
  return (
    <>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard
          icon={TrendingUp}
          label="Receitas"
          value={formatCurrency(summary.total_receitas)}
          valueClass="text-gain"
        />
        <KpiCard
          icon={TrendingDown}
          label="Despesas"
          value={formatCurrency(summary.total_despesas)}
          valueClass="text-loss"
        />
        <KpiCard
          icon={ArrowLeftRight}
          label="Saldo"
          value={formatCurrency(summary.saldo)}
          valueClass={saldoClass}
        />
        <KpiCard
          icon={Download}
          label="Transações"
          value={summary.count.toLocaleString("pt-BR")}
        />
      </div>
      {summary.periodo_inicio && summary.periodo_fim && (
        <p className="mb-4 text-xs text-muted-foreground">
          Período: {formatDateShort(summary.periodo_inicio)} — {formatDateShort(summary.periodo_fim)}
        </p>
      )}
    </>
  );
}
