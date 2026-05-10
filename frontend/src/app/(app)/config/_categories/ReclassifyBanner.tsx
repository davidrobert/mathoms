"use client";

/**
 * ReclassifyBanner — dev-only banner em CategoriesTab (W4).
 *
 * Permite ao desenvolvedor disparar reclassify pós-edição de keywords
 * sem aguardar próxima execução de pipeline. Extraído em 2026-05-10.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/Spinner";

export type ReclassifyStatus = "idle" | "success" | "conflict" | "error";

interface ReclassifyBannerProps {
  reclassifying: boolean;
  status: ReclassifyStatus;
  onReclassify: () => void;
}

export function ReclassifyBanner({
  reclassifying,
  status,
  onReclassify,
}: ReclassifyBannerProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium">Recategorizar e gerar novo relatório</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Aplica as keywords editadas a todas as transações (despesas e receitas),
            refaz a análise e cria um relatório novo no histórico. Os relatórios
            anteriores ficam preservados.
          </p>
          {status === "success" && (
            <p className="mt-1 text-xs text-gain">
              Recategorização iniciada. O novo relatório aparecerá no histórico ao
              concluir. <Link href="/pipeline" className="underline">Ver progresso.</Link>
            </p>
          )}
          {status === "conflict" && (
            <p className="mt-1 text-xs text-alert">
              Já há um reprocessamento em andamento.{" "}
              <Link href="/pipeline" className="underline">Ver progresso.</Link>
            </p>
          )}
          {status === "error" && (
            <p className="mt-1 text-xs text-loss">
              Não foi possível iniciar a recategorização. Tente novamente em instantes.
            </p>
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onReclassify}
          disabled={reclassifying}
          className="shrink-0"
        >
          {reclassifying ? <Spinner size="sm" className="mr-2" /> : null}
          Recategorizar transações
        </Button>
      </div>
    </div>
  );
}
