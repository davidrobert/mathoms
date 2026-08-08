"use client";

import type { CascataPayload, CascataTrigger, TributarioBundle } from "@/lib/api";
import { ReportCard } from "../ReportCard";
import { DISCLAIMER_SENTENCE, HEADER_TITLE } from "./CascataFiscalCard.copy";
import {
  ProtectionAndPremises,
  RegimeSubheader,
} from "./CascataFiscalCard.header";
import { CascataLayers } from "./CascataFiscalCard.layers";
import { PgblBlock } from "./CascataFiscalCard.pgbl";
import {
  AnexoPendenteState,
  LucroRealState,
  PerfilPendenteState,
} from "./CascataFiscalCard.states";
import {
  SEVERITY,
  TRIGGER_TITLE,
  renderTriggerBody,
} from "./CascataFiscalCard.triggers";

/** Sprint A16 L2 P5 (ADR-236 §D5) — Card "Tributário PJ — Cascata Fiscal".
 *
 * Substitui o uso anterior de `<NarrativeChartCard chartId="impostos_pj"/>`
 * em `S8PrevidenciaSection`. Renderiza a cascata calculada por
 * `pipeline/domain/services/tributario/cascata_calculator.py` (P3) +
 * adapter (P4), exposta no E5 output como `data.tributario`.
 *
 * Estados:
 *   - Cascata completa (Simples Anexo III/V, Lucro Presumido, MEI).
 *   - Empty state "perfil tributário pendente" (regime/anexo ausente).
 *   - Empty state "Lucro Real" (regime fora do escopo V1; cascata V2).
 *   - Bloco PGBL com flag para `declaracao_simplificada` + estado neutro
 *     para `renda_tributavel_pf_zerada`.
 *   - 0-5 decision triggers (T1-T5) como callouts severity-tipados.
 *
 * Co-design product-designer + financial-planner (2026-05-21):
 *   - Steps verticais (`<dl>`) > waterfall — densidade do card.
 *   - Carga total como linha final da cascata (não KPI hero).
 *   - Triggers com cor + ícone redundante (daltonismo).
 *   - Copy CRC: "Trade-off observado" / "Sinal de atenção" / "Oportunidade".
 *   - Frase de proteção sob header (blinda card inteiro contra
 *     interpretação como conselho).
 *
 * As partes vivem em módulos irmãos `CascataFiscalCard.*`: copy, preâmbulo
 * (header), steps (layers), bloco PGBL, estados vazios e triggers.
 */

interface CascataFiscalCardProps {
  tributario: TributarioBundle | undefined;
}

export function CascataFiscalCard({ tributario }: CascataFiscalCardProps) {
  const cascata = tributario?.cascata;
  if (!tributario || !cascata || cascata.motivo_nao_suportado === "perfil_incompleto") {
    return <PerfilPendenteState />;
  }
  if (cascata.regime_nao_suportado && cascata.motivo_nao_suportado === "lucro_real") {
    return <LucroRealState />;
  }
  if (cascata.motivo_nao_suportado === "anexo_simples_pendente") {
    return <AnexoPendenteState />;
  }
  return <CascataFullCard tributario={tributario} cascata={cascata} />;
}

function CascataFullCard({
  tributario,
  cascata,
}: {
  tributario: TributarioBundle;
  cascata: CascataPayload;
}) {
  return (
    <ReportCard
      variant="feature"
      size="full"
      title={HEADER_TITLE}
      headerRight={<RegimeSubheader cascata={cascata} />}
    >
      <section
        role="region"
        aria-labelledby="cascata-fiscal-title"
        aria-describedby="cascata-fiscal-disclaimer"
        className="space-y-6"
      >
        <h4 id="cascata-fiscal-title" className="sr-only">
          {HEADER_TITLE} — {cascata.regime_label}
        </h4>
        <ProtectionAndPremises />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
          <CascataLayers cascata={cascata} />
          <PgblBlock cascata={cascata} />
        </div>
        <TriggersList triggers={cascata.triggers} />
        <FiduciaryDisclaimer temContador={Boolean(tributario.contador_nome)} />
      </section>
    </ReportCard>
  );
}

/** A40.l4 (ADR-319): o nome do contador é PII de terceiro — e com frequência
 * pessoa física. O disclaimer precisa dizer que há contador no perfil, não
 * quem ele é; o relatório é o artefato que a família mostra a terceiros. */
function FiduciaryDisclaimer({ temContador }: { temContador: boolean }) {
  return (
    <p
      id="cascata-fiscal-disclaimer"
      className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]"
    >
      {DISCLAIMER_SENTENCE}
      {temContador ? " Há contador cadastrado no perfil da PJ." : ""}
    </p>
  );
}

/* ─── Decision triggers (callouts) ─────────────────────────────────── */

function TriggersList({ triggers }: { triggers: CascataTrigger[] }) {
  if (triggers.length === 0) return null;
  return (
    <section
      aria-labelledby="cascata-triggers-title"
      className="space-y-3"
    >
      <h4
        id="cascata-triggers-title"
        className="font-display text-sm font-semibold text-[var(--surface-foreground)]"
      >
        Pontos de atenção
      </h4>
      <ul className="space-y-3" aria-label="Pontos de atenção tributária">
        {triggers.map((t) => (
          <li key={t.code}>
            <TriggerCallout trigger={t} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TriggerCallout({ trigger }: { trigger: CascataTrigger }) {
  const style = SEVERITY[trigger.severity];
  const title = TRIGGER_TITLE[trigger.code] ?? trigger.title;
  const body = renderTriggerBody(trigger);
  return (
    <div
      className={`flex items-start gap-2 rounded-md border-l-4 ${style.borderClass} bg-[var(--surface-card)] p-3`}
      aria-label={`${style.ariaSeverity}: ${title}`}
    >
      <style.Icon
        className={`mt-0.5 h-4 w-4 shrink-0 ${style.iconClass}`}
        aria-hidden="true"
      />
      <div className="flex-1 space-y-1">
        <p className="text-sm font-semibold text-[var(--surface-foreground)]">
          {title}
        </p>
        <p className="text-xs leading-relaxed text-[var(--surface-foreground)]">
          {body}
        </p>
      </div>
    </div>
  );
}
