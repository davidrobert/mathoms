"use client";

import { PieChart } from "lucide-react";

import { Separator } from "@/components/ui/separator";
import { rebalanceamentoModoLabel } from "@/lib/goalPremissas";

import { AlocacaoBar } from "./AlocacaoBar";
import { CLASS_META, type Pcts } from "./constants";

interface AlocacaoSummaryProps {
  pcts: Pcts;
  instrumentosRf: string;
  instrumentosRv: string;
  rebalanceamento: string;
}

export function AlocacaoSummary({
  pcts,
  instrumentosRf,
  instrumentosRv,
  rebalanceamento,
}: AlocacaoSummaryProps) {
  return (
    <div className="rounded-lg border p-4 text-sm">
      <div className="mb-3 flex items-center gap-2">
        <PieChart className="h-4 w-4" />
        <h3 className="font-semibold">Resumo da alocacao</h3>
      </div>

      <AlocacaoBar className="mb-3" pcts={pcts} />

      <dl className="space-y-1">
        {CLASS_META.map(({ key, label, color }) => (
          <SummaryRow
            key={key}
            color={color}
            label={label}
            value={`${pcts[key]}%`}
          />
        ))}
        <Separator className="my-2" />
        {instrumentosRf && (
          <div className="flex justify-between text-xs">
            <dt className="text-muted-foreground">Instr. RF</dt>
            <dd>{instrumentosRf}</dd>
          </div>
        )}
        {instrumentosRv && (
          <div className="flex justify-between text-xs">
            <dt className="text-muted-foreground">Instr. RV</dt>
            <dd>{instrumentosRv}</dd>
          </div>
        )}
        <div className="flex justify-between text-xs">
          <dt className="text-muted-foreground">Rebalanceamento</dt>
          <dd>{rebalanceamentoModoLabel(rebalanceamento)}</dd>
        </div>
      </dl>
    </div>
  );
}

function SummaryRow({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value: string;
}) {
  return (
    <div className="flex justify-between">
      <dt className="flex items-center gap-1 text-muted-foreground">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: color }}
        />
        {label}
      </dt>
      <dd className="font-mono tabular-nums">{value}</dd>
    </div>
  );
}
