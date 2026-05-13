"use client";

// ADR-199 / ADR-208 — S_parecer (Parecer do Planejador).
// Aggregate-driven: lê do endpoint `GET .../planner-review`. Hand-coded
// (não data_source do snapshot E5, igual a PlanoDeAcao). Renderer único
// pós-ADR-129. CSS de print em `SParecer.print.css`.

import { useCallback } from "react";

import { ReportSection } from "../../ReportSection";
import { usePlannerReview } from "@/hooks/usePlannerReview";

import { ParecerHeroDiagnostico } from "./ParecerHeroDiagnostico";
import { ParecerHorizonteList } from "./ParecerHorizonteList";
import { ParecerMetricasTable } from "./ParecerMetricasTable";
import { ParecerRisksTable } from "./ParecerRisksTable";
import { PontosFortesList } from "./PontosFortesList";
import "./SParecer.print.css";

interface SParecerSectionProps {
  workspaceId: string;
  reportId: string;
}

export function SParecerSection({ workspaceId, reportId }: SParecerSectionProps) {
  const { state, reload } = usePlannerReview(workspaceId, reportId);
  const handleMutate = useCallback(async () => {
    await reload();
  }, [reload]);

  return (
    <ReportSection id="S_parecer" title="Parecer do Planejador">
      <div className="md:col-span-2 flex flex-col gap-6">
        {state.kind === "loading" && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Carregando parecer…
          </p>
        )}
        {state.kind === "not_generated" && <ParecerEmptyState />}
        {state.kind === "error" && (
          <p
            role="alert"
            className="text-sm text-[var(--semantic-loss)]"
            data-testid="parecer-error"
          >
            Não foi possível carregar o parecer — atualize a página.
          </p>
        )}
        {state.kind === "ready" && (
          <ParecerBody
            data={state.data}
            workspaceId={workspaceId}
            onMutate={handleMutate}
          />
        )}
      </div>
    </ReportSection>
  );
}

function ParecerEmptyState() {
  return (
    <div
      className="rounded-[var(--radius-card)] border border-dashed border-[var(--surface-border)] p-6 text-center"
      data-testid="parecer-empty"
    >
      <p className="font-heading text-base font-semibold text-[var(--surface-foreground)]">
        Parecer ainda não gerado
      </p>
      <p className="mt-1 text-sm text-[var(--surface-muted-foreground)]">
        Próximo relatório premium incluirá o parecer orientativo do
        planejador.
      </p>
    </div>
  );
}

interface ParecerBodyProps {
  data: import("@/lib/api").PlannerReviewResponse;
  workspaceId: string;
  onMutate: () => Promise<void>;
}

function ParecerBody({ data, workspaceId, onMutate }: ParecerBodyProps) {
  const { content } = data;
  const gated = content.meta.gated_counts;

  return (
    <>
      <ParecerHeroDiagnostico
        diagnostico={content.diagnostico_geral}
        meta={content.meta}
      />

      <div className="grid gap-6 md:grid-cols-2">
        <PontosFortesList
          pontos={content.pontos_fortes}
          gatedCount={gated.pontos_fortes}
        />
        <ParecerRisksTable
          riscos={content.riscos}
          gatedCount={gated.riscos}
        />
      </div>

      <ParecerHorizonteList
        horizon="execucao"
        sugestoes={content.sugestoes_execucao}
        workspaceId={workspaceId}
        gatedCount={gated.sugestoes_execucao}
        onMutate={onMutate}
      />
      <ParecerHorizonteList
        horizon="tatico"
        sugestoes={content.sugestoes_taticas}
        workspaceId={workspaceId}
        gatedCount={gated.sugestoes_taticas}
        onMutate={onMutate}
      />
      <ParecerHorizonteList
        horizon="estrategico"
        sugestoes={content.sugestoes_estrategicas}
        workspaceId={workspaceId}
        gatedCount={gated.sugestoes_estrategicas}
        onMutate={onMutate}
      />

      <ParecerMetricasTable
        metricas={content.metricas}
        gatedCount={gated.metricas}
      />

      <FiduciaryDisclaimer />
    </>
  );
}

function FiduciaryDisclaimer() {
  return (
    <aside
      className="md:col-span-2 mt-2 rounded-md border border-[var(--surface-border)] bg-[var(--surface-muted)] px-4 py-3 text-xs text-[var(--surface-muted-foreground)]"
      role="note"
      data-testid="parecer-disclaimer"
    >
      <strong className="font-semibold">Aviso fiduciário:</strong> Este parecer
      é orientativo, baseado nos dados disponíveis no momento da geração e não
      constitui recomendação personalizada de investimento. Decisões patrimoniais
      devem considerar contexto pessoal, fiscal e legal — quando aplicável,
      consulte profissional habilitado.
    </aside>
  );
}
