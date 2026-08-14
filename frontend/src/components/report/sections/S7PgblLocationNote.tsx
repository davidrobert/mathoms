import { AlertTriangle, Info } from "lucide-react";

import { matchIrpfToPeriod } from "@/lib/irpf/irpf-period-match";
import type { IrpfKpis } from "@/types/irpf";

interface PgblLocationNoteProps {
  irpfKpis: IrpfKpis | null;
  primaryYear: number | null;
}

export function PgblLocationNote({
  irpfKpis,
  primaryYear,
}: PgblLocationNoteProps) {
  if (!irpfKpis) return <PgblWithoutIrpf />;
  const gap = pgblStalenessGap(irpfKpis.ano_base, primaryYear);
  return <PgblWithIrpf anoBase={irpfKpis.ano_base} gap={gap} />;
}

function pgblStalenessGap(anoBase: number, primaryYear: number | null) {
  if (primaryYear === null) return null;
  return matchIrpfToPeriod([anoBase], primaryYear)?.defasadoAnos ?? null;
}

function PgblWithIrpf({
  anoBase,
  gap,
}: {
  anoBase: number;
  gap: number | null;
}) {
  const isStale = gap !== null && gap >= 2;
  const Icon = isStale ? AlertTriangle : Info;
  const className = isStale
    ? "flex items-start gap-2 text-sm leading-relaxed md:col-span-2 text-[var(--semantic-alert-on-tint)]"
    : "flex items-start gap-2 text-sm leading-relaxed md:col-span-2 text-[var(--surface-muted-foreground)]";
  return (
    <p role="note" data-testid="s7-pgbl-location" className={className}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        Ver dedução de PGBL em <PgblOptimizationLink /> — análise baseada no
        IRPF de {anoBase}
        {isStale && <>, defasado em {gap} anos. Importe o IRPF mais recente</>}.
      </span>
    </p>
  );
}

function PgblOptimizationLink() {
  return (
    <a
      href="#S_IRPF_OTIMIZACAO"
      className="underline decoration-dotted underline-offset-2 text-[var(--brand-info)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
    >
      Otimização Tributária
    </a>
  );
}

function PgblWithoutIrpf() {
  return (
    <p
      role="note"
      data-testid="s7-pgbl-without-irpf"
      className="flex items-start gap-2 text-sm leading-relaxed text-[var(--surface-muted-foreground)] md:col-span-2"
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        Dedução de PGBL não avaliada: não há declaração de IRPF processada.{" "}
        <PgblImportLink />.
      </span>
    </p>
  );
}

function PgblImportLink() {
  return (
    <a
      href="/documents"
      className="underline decoration-dotted underline-offset-2 text-[var(--brand-info)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
    >
      Importar declaração de IRPF
    </a>
  );
}
