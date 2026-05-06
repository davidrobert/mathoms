"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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

import { ReviewActions } from "../_components/ReviewActions";
import { ReviewDetailHeader } from "../_components/ReviewDetailHeader";
import { JsonViewer } from "../_components/JsonViewer";
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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listStageReviews(workspaceId, runId);
      const found = list.find((r) => r.id === reviewId) ?? null;
      if (!found) {
        setError("Revisão não encontrada.");
      } else {
        setReview(found);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao carregar revisão");
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

  const handleSubmit = useCallback(
    async (req: StageReviewActionRequest) => {
      setSubmitting(true);
      try {
        const updated = await submitStageReview(workspaceId, runId, reviewId, req);
        setReview(updated);
        toast.success(
          req.action === "approve"
            ? "Revisão aprovada."
            : "Edição salva e revisão aprovada.",
          { duration: 3000 },
        );
        router.push(`/pipeline/runs/${runId}/reviews`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          toast.info("Esta revisão já foi processada.", { duration: 3000 });
          await load();
        } else {
          toast.error(
            err instanceof ApiError ? err.detail : "Erro ao processar revisão",
          );
        }
      } finally {
        setSubmitting(false);
      }
    },
    [workspaceId, runId, reviewId, router, load],
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
              {error ?? "Revisão não encontrada."}
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
    <div className="mx-auto max-w-content px-6 py-8">
      <ReviewDetailHeader review={review} runId={runId} />

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-label="Output original" className="space-y-3">
          <h2 className="text-sm font-medium text-foreground">
            Output original do stage
          </h2>
          <JsonViewer
            value={review.original_output_json}
            errorPaths={errorPaths}
          />
        </section>

        <section aria-label="Erros e ações" className="space-y-4">
          <div>
            <h2 className="mb-2 text-sm font-medium text-foreground">
              Erros de validação
            </h2>
            <ValidationErrorsPanel
              issues={review.validation_issues}
              errorsLegacy={review.validation_errors}
              onErrorClick={(path) => {
                const el = document.querySelector(`[data-json-path="${path}"]`);
                if (el && "scrollIntoView" in el) {
                  (el as HTMLElement).scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                  });
                }
              }}
            />
          </div>

          <ReviewActions
            review={review}
            submitting={submitting}
            onSubmit={handleSubmit}
          />
        </section>
      </div>
    </div>
  );
}
