"use client";

/**
 * A10.4 · ADR-178 — Risks aggregate section.
 *
 * UI mínima: tabela `name | probability | impact_level | status`, com
 * botões "Editar" e "Linkar Decision". Bubble chart S9 vira projeção em
 * A10.5 (Wave 3); aqui só listamos para o aggregate ficar editável.
 *
 * Decisão UI rica fica em sprint posterior — foco é o aggregate vivo.
 */

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Pencil, Link2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ApiError,
  listRisks,
  type Risk,
  type RiskImpactLevel,
  type RiskProbability,
  type RiskStatus,
} from "@/lib/api";

interface RisksSectionProps {
  workspaceId: string;
}

const IMPACT_LABEL: Record<RiskImpactLevel, string> = {
  baixo: "Baixo",
  médio: "Médio",
  alto: "Alto",
  crítico: "Crítico",
};

const PROBABILITY_LABEL: Record<RiskProbability, string> = {
  baixa: "Baixa",
  média: "Média",
  alta: "Alta",
};

const STATUS_BADGE: Record<RiskStatus, string> = {
  Ativo:
    "rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
  Mitigado:
    "rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200",
  Aceito:
    "rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  Descartado:
    "rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 line-through",
};

export function RisksSection({ workspaceId }: RisksSectionProps) {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await listRisks(workspaceId);
      setRisks(res.risks);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Erro ao carregar riscos";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <section className="mt-8" data-testid="risks-section">
        <SectionHeading label="Riscos" />
        <div className="mt-4 space-y-2">
          <Skeleton className="h-10 rounded-lg" />
          <Skeleton className="h-10 rounded-lg" />
          <Skeleton className="h-10 rounded-lg" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="mt-8" data-testid="risks-section">
        <SectionHeading label="Riscos" />
        <EmptyState
          title="Erro ao carregar riscos"
          description={error}
          ctas={[
            {
              label: "Tentar novamente",
              onClick: () => void load(),
              variant: "secondary",
            },
          ]}
        />
      </section>
    );
  }

  if (risks.length === 0) {
    return (
      <section className="mt-8" data-testid="risks-section">
        <SectionHeading label="Riscos" />
        <EmptyState
          title="Nenhum risco cadastrado"
          description="Workspace novo recebe os 5 riscos universais (morte, invalidez, doença grave, desemprego, longevidade). Edite ou adicione específicos."
        />
      </section>
    );
  }

  return (
    <section className="mt-8" data-testid="risks-section">
      <SectionHeading label="Riscos" />
      <div className="mt-4 overflow-x-auto rounded-lg border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-3 py-2 text-left">Nome</th>
              <th scope="col" className="px-3 py-2 text-left">Probabilidade</th>
              <th scope="col" className="px-3 py-2 text-left">Impacto</th>
              <th scope="col" className="px-3 py-2 text-left">Status</th>
              <th scope="col" className="px-3 py-2 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-background">
            {risks.map((risk) => (
              <tr key={risk.id} data-testid={`risk-row-${risk.code}`}>
                <td className="px-3 py-2 font-medium">{risk.name}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {risk.probability ? PROBABILITY_LABEL[risk.probability] : "—"}
                </td>
                <td className="px-3 py-2">{IMPACT_LABEL[risk.impact_level]}</td>
                <td className="px-3 py-2">
                  <span className={STATUS_BADGE[risk.status]}>{risk.status}</span>
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label="Editar risco"
                      onClick={() =>
                        toast.info(
                          "Edição de Risk chega em sprint posterior — A10.4 entrega aggregate + lista.",
                        )
                      }
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label="Linkar Decision"
                      onClick={() =>
                        toast.info(
                          "Linkar Decision chega em sprint posterior — endpoint /risks/{id}/mitigations já está vivo.",
                        )
                      }
                    >
                      <Link2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
