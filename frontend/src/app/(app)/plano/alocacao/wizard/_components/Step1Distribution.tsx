"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AlocacaoBar } from "./AlocacaoBar";
import { PRESETS, type Pcts } from "./constants";

interface Step1DistributionProps {
  pcts: Pcts;
  onChange: (next: Pcts) => void;
  soma: number;
  somaValida: boolean;
}

export function Step1Distribution({
  pcts,
  onChange,
  soma,
  somaValida,
}: Step1DistributionProps) {
  const setField = (key: keyof Pcts, value: number) => {
    onChange({ ...pcts, [key]: value });
  };

  return (
    <div>
      <h2 className="text-lg font-semibold">Distribua seus investimentos</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Defina a alocacao percentual ideal por classe de ativo.
      </p>

      <PresetButtons pcts={pcts} onSelect={onChange} />

      <div className="mt-6 grid grid-cols-2 gap-4">
        <PctInput
          id="rf"
          label="Renda fixa (%)"
          value={pcts.renda_fixa_pct}
          onChange={(v) => setField("renda_fixa_pct", v)}
        />
        <PctInput
          id="acoes"
          label="Acoes (%)"
          value={pcts.acoes_pct}
          onChange={(v) => setField("acoes_pct", v)}
        />
        <PctInput
          id="imoveis"
          label="Imoveis/REITs (%)"
          value={pcts.imoveis_reits_pct}
          onChange={(v) => setField("imoveis_reits_pct", v)}
        />
        <PctInput
          id="usd"
          label="Liquidez USD (%)"
          value={pcts.liquidez_usd_pct}
          onChange={(v) => setField("liquidez_usd_pct", v)}
        />
      </div>

      <SumIndicator soma={soma} somaValida={somaValida} />

      <AlocacaoBar className="mt-3" pcts={pcts} />
    </div>
  );
}

function PresetButtons({
  pcts,
  onSelect,
}: {
  pcts: Pcts;
  onSelect: (next: Pcts) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {Object.entries(PRESETS).map(([name, preset]) => {
        const isActive =
          pcts.renda_fixa_pct === preset.renda_fixa_pct &&
          pcts.acoes_pct === preset.acoes_pct &&
          pcts.imoveis_reits_pct === preset.imoveis_reits_pct &&
          pcts.liquidez_usd_pct === preset.liquidez_usd_pct;
        return (
          <Button
            key={name}
            variant={isActive ? "default" : "outline"}
            size="sm"
            onClick={() => onSelect(preset)}
            type="button"
          >
            {name}
          </Button>
        );
      })}
    </div>
  );
}

function PctInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="number"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 font-mono tabular-nums"
      />
    </div>
  );
}

function SumIndicator({
  soma,
  somaValida,
}: {
  soma: number;
  somaValida: boolean;
}) {
  return (
    <div className="mt-4 flex items-center gap-2 text-sm">
      {somaValida ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <XCircle className="h-4 w-4 text-destructive" />
      )}
      <span className={somaValida ? "text-emerald-600" : "text-destructive"}>
        Total: <span className="font-mono tabular-nums">{soma}%</span>
        {!somaValida && " — deve somar 100%"}
      </span>
    </div>
  );
}
