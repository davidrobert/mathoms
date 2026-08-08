"use client";

import { Clock } from "lucide-react";
import type { ReactNode } from "react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";

import type { ProvenanceEntry } from "./ReportProvenanceProvider";

/** A25.l5 (ADR-279) — popover N2 "Como chegamos a esse número".
 *
 * Copy EXATA do co-design product-designer + senior-cto (2026-06-10) —
 * régua COPY_GUIDELINES §6.3: zero jargão de pipeline no DOM. Disparo por
 * click/Enter/Space (não hover); Base UI cuida de Escape + retorno de foco.
 */

function Count({ value }: { value: number }) {
  return (
    <span className="font-mono font-semibold tabular-nums">{value}</span>
  );
}

function LiDocumentos({ count }: { count: number | null }) {
  if (count === null) return <>Li os documentos que você enviou</>;
  return (
    <>
      Li <Count value={count} /> {count === 1 ? "documento" : "documentos"} que você enviou
    </>
  );
}

function ConferiLancamentos({
  entries,
  repeated,
}: {
  entries: number;
  repeated: number | null;
}) {
  const lancamentos = entries === 1 ? "lançamento" : "lançamentos";
  if (repeated === null) {
    return (
      <>
        Conferi <Count value={entries} /> {lancamentos}
      </>
    );
  }
  if (repeated === 0) {
    return (
      <>
        Conferi <Count value={entries} /> {lancamentos}, sem repetições
      </>
    );
  }
  return (
    <>
      Conferi <Count value={entries} /> {lancamentos} — <Count value={repeated} /> apareciam
      repetidos e contei só uma vez
    </>
  );
}

function NeedsReviewBand() {
  return (
    <div
      className="mb-3 flex items-start gap-2 rounded-md bg-[color-mix(in_srgb,var(--semantic-alert)_15%,transparent)] p-2 text-xs"
      data-provenance-needs-review
    >
      {/* O ícone é objeto gráfico sobre o tint da própria cor — 1.4.11 pede
          3:1, e a cor base dava 1,86:1 em light. Par `-on-tint` sobe para
          5,60:1. Não é pareado por dev/check_tint_contrast.py (o `text-[…]`
          vive no filho, não no className do fundo). */}
      <Clock
        aria-hidden="true"
        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--semantic-alert-on-tint)]"
      />
      <p className="text-[var(--surface-popover-foreground)]">
        Ainda estou conferindo um detalhe deste número. Pode mudar levemente.
      </p>
    </div>
  );
}

function ProvenanceSteps({ entry }: { entry: ProvenanceEntry }) {
  return (
    <ul className="mt-2 space-y-1.5 text-sm">
      <li>
        <LiDocumentos count={entry.documentsCount} />
      </li>
      {entry.entriesCount !== null && (
        <li>
          <ConferiLancamentos entries={entry.entriesCount} repeated={entry.repeatedCount} />
        </li>
      )}
      {entry.entriesCount !== null && <li>Classifiquei cada lançamento por categoria</li>}
      <li>
        {entry.isPassthrough
          ? "Confirmei o saldo direto dos seus extratos"
          : "Calculei somando o que entra e subtraindo o que sai"}
      </li>
    </ul>
  );
}

interface ProvenancePopoverProps {
  entry: ProvenanceEntry;
  /** Espessura do selo: 1px (default) ou 1.5px no hero. */
  hero?: boolean;
  /** Conteúdo visível do selo — os dígitos formatados (sem o sinal +/−). */
  children: ReactNode;
}

const SEAL_BASE =
  "cursor-help underline decoration-dotted underline-offset-[3px] focus-visible:outline-none";

export function ProvenancePopover({ entry, hero = false, children }: ProvenancePopoverProps) {
  const sealColor = entry.needsReview
    ? "decoration-[var(--semantic-warning)]"
    : "decoration-[var(--border)] hover:decoration-[var(--brand-primary)] focus-visible:decoration-[var(--brand-primary)]";
  return (
    <Popover>
      <PopoverTrigger
        nativeButton={false}
        render={
          <span
            data-provenance-seal
            aria-label={`Como chegamos ao ${entry.label}`}
            className={cn(SEAL_BASE, hero ? "decoration-[1.5px]" : "decoration-1", sealColor)}
          />
        }
      >
        {children}
      </PopoverTrigger>
      <PopoverContent aria-label={`Como chegamos ao ${entry.label}`}>
        {entry.needsReview && <NeedsReviewBand />}
        <p className="font-semibold text-[var(--surface-popover-foreground)]">
          Como chegamos a esse número
        </p>
        <p className="mt-0.5 text-xs text-[var(--surface-muted-foreground)]">{entry.label}</p>
        <ProvenanceSteps entry={entry} />
        <p className="mt-3 border-t border-[var(--border)] pt-2 text-xs text-[var(--surface-muted-foreground)]">
          O número acima é o que vale. Aqui só mostro como conferi.
        </p>
      </PopoverContent>
    </Popover>
  );
}
