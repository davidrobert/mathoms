"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

import {
  ApiError,
  listStageReviews,
  submitStageReview,
  type StageReviewActionRequest,
  type StageReviewResponse,
} from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";

import { ReviewActions } from "../_components/ReviewActions";
import { ReviewDetailHeader } from "../_components/ReviewDetailHeader";
import { JsonViewer } from "../_components/JsonViewer";
import { countReviewItems } from "../_components/groupIssues";
import {
  extractErrorPaths,
  ValidationErrorsPanel,
} from "../_components/ValidationErrorsPanel";

/** Extrai o segmento "leaf" do JSONPath para casar com data-json-path do JsonViewer.
 * Ex.: `$.dividas_onus[0].discriminacao` → `discriminacao`. */
function stripJsonPath(path: string): string {
  const cleaned = path.replace(/\$\.?/, "").replace(/\[\d+\]/g, "");
  const segs = cleaned.split(".");
  const leaf = segs[segs.length - 1] ?? "";
  return leaf;
}

function successToast(req: StageReviewActionRequest, errorCount: number): string {
  if (req.action === "edit") return "Correções salvas. Análise retomada.";
  if (errorCount > 0) {
    const n = errorCount === 1 ? "1 documento ficou" : `${errorCount} documentos ficaram`;
    return `${n} de fora. Você pode revisá-los quando quiser.`;
  }
  return "Análise retomada com os itens como estão.";
}

export default function ReviewDetailPage() {
  const { workspace } = useWorkspace();
  const params = useParams<{ runId: string; reviewId: string }>();
  const runId = params?.runId;
  const reviewId = params?.reviewId;
  if (!workspace || !runId || !reviewId) return null;
  return (
    <ReviewDetailContent
      workspaceId={workspace.id}
      runId={runId}
      reviewId={reviewId}
    />
  );
}

function ReviewDetailContent({
  workspaceId,
  runId,
  reviewId,
}: {
  workspaceId: string;
  runId: string;
  reviewId: string;
}) {
  const router = useRouter();
  const [review, setReview] = useState<StageReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const jsonDetailsRef = useRef<HTMLDetailsElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listStageReviews(workspaceId, runId);
      const found = list.find((r) => r.id === reviewId) ?? null;
      if (!found) {
        setError("Conferência não encontrada.");
      } else {
        setReview(found);
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Erro ao carregar conferência",
      );
    } finally {
      setLoading(false);
    }
  }, [workspaceId, runId, reviewId]);

  useEffect(() => {
    load();
  }, [load]);

  const errorPaths = useMemo(() => {
    const issues = review?.validation_issues;
    if (issues && issues.length > 0) {
      // ADR-165: paths estruturados são confiáveis, não precisamos da heurística regex.
      const paths = new Set<string>();
      for (const issue of issues) {
        if (issue.path) paths.add(stripJsonPath(issue.path));
      }
      return paths;
    }
    return extractErrorPaths(review?.validation_errors ?? null);
  }, [review?.validation_issues, review?.validation_errors]);

  const counts = useMemo(
    () =>
      countReviewItems(
        review?.validation_issues ?? null,
        review?.validation_errors ?? null,
      ),
    [review?.validation_issues, review?.validation_errors],
  );

  const scrollToField = useCallback((path: string) => {
    const details = jsonDetailsRef.current;
    if (details) details.open = true;
    const el = document.querySelector(`[data-json-path="${path}"]`);
    if (el && "scrollIntoView" in el) {
      (el as HTMLElement).scrollIntoView({ behavior: "smooth", block: "center" });
      (el as HTMLElement).setAttribute("tabindex", "-1");
      (el as HTMLElement).focus({ preventScroll: true });
    }
  }, []);

  const handleSubmit = useCallback(
    async (req: StageReviewActionRequest) => {
      setSubmitting(true);
      try {
        const updated = await submitStageReview(workspaceId, runId, reviewId, req);
        setReview(updated);
        toast.success(successToast(req, counts.errors), { duration: 3000 });
        router.push(`/pipeline/runs/${runId}/reviews`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          toast.info("Esta conferência já foi concluída.", { duration: 3000 });
          await load();
        } else {
          toast.error(
            err instanceof ApiError ? err.detail : "Erro ao processar a ação",
          );
        }
      } finally {
        setSubmitting(false);
      }
    },
    [workspaceId, runId, reviewId, router, load, counts.errors],
  );

  if (loading) {
    return (
      <div className="mx-auto max-w-content px-6 py-8">
        <Skeleton className="mb-4 h-8 w-1/3" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Card>
          <CardContent>
            <p className="mb-3 text-sm text-loss">
              {error ?? "Conferência não encontrada."}
            </p>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              <RefreshCw className="mr-2 h-4 w-4" /> Tentar de novo
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 pb-24 lg:pb-8">
      <ReviewDetailHeader review={review} runId={runId} itemCount={counts.total} />

      <div className="space-y-6">
        <section aria-label="Itens para conferência">
          <ValidationErrorsPanel
            issues={review.validation_issues}
            errorsLegacy={review.validation_errors}
            onErrorClick={scrollToField}
          />
        </section>

        <ReviewActions
          review={review}
          submitting={submitting}
          onSubmit={handleSubmit}
          errorCount={counts.errors}
          warningCount={counts.warnings}
          className={cn(
            // Mobile (<lg): action bar fixo no fundo da viewport
            "fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 px-4 py-3 backdrop-blur",
            "pb-[max(0.75rem,env(safe-area-inset-bottom))]",
            // Desktop (lg+): fluxo normal, sem chrome do action bar
            "lg:static lg:inset-x-auto lg:bottom-auto",
            "lg:border-0 lg:bg-transparent lg:p-0 lg:pb-0 lg:backdrop-blur-none",
          )}
        />

        {review.original_output_json !== null &&
          review.original_output_json !== undefined && (
            <details
              ref={jsonDetailsRef}
              className="rounded-lg border border-border p-3"
            >
              <summary className="cursor-pointer select-none text-sm font-medium text-foreground hover:text-foreground/80">
                Ver dados extraídos (avançado)
              </summary>
              <p className="mt-2 text-xs text-muted-foreground">
                Estes são os dados que a leitura automática extraiu, exatamente
                como ficaram. Útil para conferir um valor específico.
              </p>
              <div className="mt-2">
                <JsonViewer
                  value={review.original_output_json}
                  errorPaths={errorPaths}
                />
              </div>
            </details>
          )}
      </div>
    </div>
  );
}
