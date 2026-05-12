"use client";

import { CheckCircle, Circle } from "lucide-react";

import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";
import {
  fiduciaryDisclaimer,
  type ProtectionBundle,
} from "./protectionBundle.types";

interface SucessaoCardProps {
  bundle: ProtectionBundle | undefined;
  effectiveDate?: string | null;
}

interface ChecklistItem {
  id: string;
  label: string;
  done: boolean;
  hint?: string;
}

/** Deriva o checklist sucessório a partir do bundle.
 *
 * T03 popula sinais refinados; até lá defaults conservadores.
 */
function deriveChecklist(bundle: ProtectionBundle | undefined): {
  items: ChecklistItem[];
  itcmdEstimate: number | null;
} {
  const sucessoriaPolicies = (bundle?.policies ?? []).filter(
    (p) => p.category === "sucessorio" && p.status === "Ativa",
  );
  const sucessoriaGap = bundle?.gap_analysis?.["sucessorio"];
  const sucessoriaRecs = (bundle?.recommendations ?? []).filter(
    (r) => r.category === "sucessorio",
  );
  return {
    items: buildChecklistItems(sucessoriaPolicies.length, sucessoriaGap, sucessoriaRecs.length),
    itcmdEstimate:
      sucessoriaGap?.ideal_brl !== null && sucessoriaGap?.ideal_brl !== undefined
        ? sucessoriaGap.ideal_brl
        : null,
  };
}

function buildTestamentoItem(activeSucessoriaCount: number, recsCount: number): ChecklistItem {
  return {
    id: "testamento",
    label: "Testamento registrado em cartório",
    done: recsCount === 0 && activeSucessoriaCount > 0,
    hint: recsCount > 0
      ? "Recomendação: revisar/lavrar testamento conforme metodologia sucessória."
      : undefined,
  };
}

function buildBeneficiariosItem(activeSucessoriaCount: number): ChecklistItem {
  return {
    id: "beneficiarios_previdencia",
    label: "Beneficiários de previdência declarados",
    done: activeSucessoriaCount > 0,
    hint: activeSucessoriaCount === 0
      ? "Sem apólice sucessória ativa — beneficiários podem não estar formalizados."
      : undefined,
  };
}

function buildItcmdItem(gap: ProtectionBundle["gap_analysis"][string] | undefined): ChecklistItem {
  return {
    id: "itcmd",
    label: "ITCMD estimado por estado",
    done: gap !== undefined && gap.ideal_brl !== null && gap.ideal_brl !== undefined,
    hint: gap?.methodology
      ? `Calculado via ${gap.methodology}.`
      : "Calculator ITCMD ainda não rodou — alíquota varia por estado (SP 4%, RJ até 8%, MG 5%).",
  };
}

function buildChecklistItems(
  activeSucessoriaCount: number,
  gap: ProtectionBundle["gap_analysis"][string] | undefined,
  recsCount: number,
): ChecklistItem[] {
  return [
    buildTestamentoItem(activeSucessoriaCount, recsCount),
    buildBeneficiariosItem(activeSucessoriaCount),
    {
      id: "holding",
      label: "Holding patrimonial avaliada",
      done: false,
      hint: "Mathoms não emite recomendação fiduciária de holding — consultar planejador CFP®.",
    },
    buildItcmdItem(gap),
  ];
}

function ChecklistItemRow({ item }: { item: ChecklistItem }) {
  const Icon = item.done ? CheckCircle : Circle;
  const iconColor = item.done ? "text-[var(--semantic-gain)]" : "text-[var(--surface-muted-foreground)]";
  return (
    <li className="flex items-start gap-2">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor}`} aria-hidden="true" />
      <div className="flex-1">
        <p className={`text-sm ${item.done ? "font-medium" : "font-semibold"}`}>{item.label}</p>
        {item.hint && (
          <p className="text-xs text-[var(--surface-muted-foreground)]">{item.hint}</p>
        )}
      </div>
    </li>
  );
}

function ItcmdBlock({ value }: { value: number | null }) {
  if (value === null) return null;
  return (
    <div className="rounded-md bg-[var(--surface-muted)] p-3">
      <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        ITCMD estimado
      </p>
      <p className="mt-1">
        <MonetaryValue value={value} compact data-testid="sucessao-itcmd" />
      </p>
    </div>
  );
}

/** S9-T04 (ADR-192 §D4) — Checklist sucessório.
 *
 * Items: testamento, beneficiários previdência, holding, ITCMD estimado.
 * Variant `warn` quando há gap. Disclaimer fiduciário sucessório.
 *
 * TODO: dados reais virão de T03 — `gap_analysis.sucessorio.ideal_brl`
 * popula via calculator `itcmd_estimated`.
 */
export function SucessaoCard({ bundle, effectiveDate }: SucessaoCardProps) {
  const { items, itcmdEstimate } = deriveChecklist(bundle);
  const hasGap = items.some((i) => !i.done);
  const variant = hasGap ? "warn" : "success";
  return (
    <ReportCard variant={variant} size="half" title="Planejamento Sucessório">
      <section role="region" aria-labelledby="sucessao-title" aria-describedby="sucessao-disclaimer" className="space-y-4">
        <h4 id="sucessao-title" className="sr-only">Checklist de planejamento sucessório</h4>
        <ul className="space-y-2" aria-label="Itens do checklist sucessório">
          {items.map((item) => <ChecklistItemRow key={item.id} item={item} />)}
        </ul>
        <ItcmdBlock value={itcmdEstimate} />
        <p id="sucessao-disclaimer" className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
          {fiduciaryDisclaimer("metodologia sucessória BR", effectiveDate)}
        </p>
      </section>
    </ReportCard>
  );
}
