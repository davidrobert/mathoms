"use client";

import { AlertTriangle, ArrowRight, ShieldAlert } from "lucide-react";

import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";
import {
  fiduciaryDisclaimer,
  type ProtectionBundle,
  type ProtectionPriority,
  type ProtectionRecommendation,
  type RiskInferred,
} from "./protectionBundle.types";

interface AcoesMitigacaoCardProps {
  bundle: ProtectionBundle | undefined;
  effectiveDate?: string | null;
  /** Callback do botão "Aceitar como Risco" (T05 implementa a mutation). */
  onAcceptRisk?: (risk: RiskInferred) => void;
}

const PRIORITY_RANK: Record<string, number> = {
  alta: 0,
  média: 1,
  media: 1,
  baixa: 2,
};

function priorityLabel(p: ProtectionPriority | string): { text: string; className: string } {
  const normalized = p?.toLowerCase?.() ?? "";
  if (normalized === "alta") {
    return {
      text: "Alta",
      className: "bg-[color-mix(in_srgb,var(--semantic-loss)_15%,transparent)] text-[var(--semantic-loss)]",
    };
  }
  if (normalized === "média" || normalized === "media") {
    return {
      text: "Média",
      className: "bg-[color-mix(in_srgb,var(--semantic-warning)_15%,transparent)] text-[var(--semantic-warning)]",
    };
  }
  return {
    text: "Baixa",
    className: "bg-[color-mix(in_srgb,var(--surface-border)_45%,transparent)] text-[var(--surface-foreground)]",
  };
}

function rankRecommendations(recs: ProtectionRecommendation[]): ProtectionRecommendation[] {
  return [...recs].sort((a, b) => {
    const ra = PRIORITY_RANK[(a.priority ?? "").toLowerCase()] ?? 9;
    const rb = PRIORITY_RANK[(b.priority ?? "").toLowerCase()] ?? 9;
    return ra - rb;
  });
}

function RecommendationItem({ rec }: { rec: ProtectionRecommendation }) {
  const pri = priorityLabel(rec.priority);
  return (
    <li className="flex items-start gap-2">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-warning)]" aria-hidden="true" />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold">{rec.rationale}</p>
          <span className={`rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase ${pri.className}`}>
            {pri.text}
          </span>
        </div>
        <p className="text-xs text-[var(--surface-muted-foreground)]">Categoria: {rec.category}</p>
      </div>
    </li>
  );
}

function InferredRiskItem({ risk, onAcceptRisk }: { risk: RiskInferred; onAcceptRisk?: (risk: RiskInferred) => void }) {
  return (
    <li className="rounded-md border border-[var(--surface-border)] p-3">
      <div className="flex items-start gap-2">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-loss)]" aria-hidden="true" />
        <div className="flex-1">
          <p className="text-sm font-semibold">{risk.name}</p>
          <p className="text-xs text-[var(--surface-muted-foreground)]">{risk.rationale}</p>
          {risk.estimated_impact_brl != null && (
            <p className="mt-1 text-xs">
              Impacto estimado: <MonetaryValue value={risk.estimated_impact_brl} compact />
            </p>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={() => onAcceptRisk?.(risk)}
        disabled={!onAcceptRisk}
        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[var(--brand-info)] hover:underline disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={`Aceitar ${risk.name} como Risco`}
      >
        Aceitar como Risco
        <ArrowRight className="h-3 w-3" aria-hidden="true" />
      </button>
    </li>
  );
}

function RecommendationsList({ recs }: { recs: ProtectionRecommendation[] }) {
  if (recs.length === 0) return null;
  return (
    <ul className="space-y-3" aria-label="Recomendações priorizadas">
      {recs.map((rec, i) => <RecommendationItem key={`rec-${i}`} rec={rec} />)}
    </ul>
  );
}

function AutoInferredList({ risks, onAcceptRisk }: { risks: RiskInferred[]; onAcceptRisk?: (risk: RiskInferred) => void }) {
  if (risks.length === 0) return null;
  return (
    <div>
      <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        Riscos auto-inferidos
      </h5>
      <ul className="space-y-3" aria-label="Riscos auto-inferidos pelos calculators">
        {/* TODO T05: handler real via mutation /risks */}
        {risks.map((risk, i) => <InferredRiskItem key={`risk-${i}`} risk={risk} onAcceptRisk={onAcceptRisk} />)}
      </ul>
    </div>
  );
}

/** S9-T04 (ADR-192 §D4) — Lista priorizada de ações de mitigação.
 *
 * Items: ação (rationale), prioridade (alta/média/baixa), categoria.
 * `auto_inferred_risks` ganham botão "Aceitar como Risco" (T05 handler).
 *
 * TODO: dados reais virão de T03 — recommendations + auto_inferred_risks
 * vêm vazios até T03 mergear.
 */
export function AcoesMitigacaoCard({ bundle, effectiveDate, onAcceptRisk }: AcoesMitigacaoCardProps) {
  const recommendations = rankRecommendations(bundle?.recommendations ?? []);
  const autoInferred = bundle?.auto_inferred_risks ?? [];
  const hasContent = recommendations.length > 0 || autoInferred.length > 0;

  return (
    <ReportCard variant="highlight" size="half" title="Ações de Mitigação">
      <section role="region" aria-labelledby="acoes-mitigacao-title" aria-describedby="acoes-mitigacao-disclaimer" className="space-y-4">
        <h4 id="acoes-mitigacao-title" className="sr-only">Lista priorizada de ações de mitigação</h4>
        {!hasContent ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhuma ação prioritária identificada — cobertura adequada para o perfil atual. Cadastre apólices novas para recalcular.
          </p>
        ) : (
          <>
            <RecommendationsList recs={recommendations} />
            <AutoInferredList risks={autoInferred} onAcceptRisk={onAcceptRisk} />
          </>
        )}
        <p id="acoes-mitigacao-disclaimer" className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
          {fiduciaryDisclaimer("wealth management", effectiveDate)}
        </p>
      </section>
    </ReportCard>
  );
}
