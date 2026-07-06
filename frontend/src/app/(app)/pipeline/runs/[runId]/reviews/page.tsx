"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw } from "lucide-react";

import { useWorkspace } from "@/lib/WorkspaceProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/Spinner";
import { PageHeader } from "@/components/PageHeader";

import { ReviewListItem } from "./_components/ReviewListItem";
import { useReviewList } from "./_components/useReviewList";
import type { StageReviewResponse } from "@/lib/api";

export default function ReviewListPage() {
  const { workspace } = useWorkspace();
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;
  if (!workspace || !runId) return null;
  return <ReviewListContent workspaceId={workspace.id} runId={runId} />;
}

function ReviewListContent({
  workspaceId,
  runId,
}: {
  workspaceId: string;
  runId: string;
}) {
  const { reviews, loading, error, resuming, resumeError, canResume, reload, resume } =
    useReviewList(workspaceId, runId);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link
        href="/pipeline"
        className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden className="h-3 w-3" /> Voltar ao pipeline
      </Link>
      <PageHeader
        title="Conferências pendentes"
        description={`Run ${runId.slice(0, 8)}…`}
      />

      {loading && <ReviewListSkeleton />}
      {!loading && error && <ReviewListError error={error} onRetry={reload} />}
      {!loading && !error && reviews?.length === 0 && <ReviewListEmpty />}
      {!loading && !error && reviews && reviews.length > 0 && (
        <ReviewListBody
          reviews={reviews}
          runId={runId}
          resuming={resuming}
          resumeError={resumeError}
          canResume={canResume}
          onResume={resume}
        />
      )}
    </div>
  );
}

function ReviewListBody({
  reviews,
  runId,
  resuming,
  resumeError,
  canResume,
  onResume,
}: {
  reviews: StageReviewResponse[];
  runId: string;
  resuming: boolean;
  resumeError: string | null;
  canResume: boolean;
  onResume: () => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      {canResume && (
        <ReadyToResumeCard
          reviewCount={reviews.length}
          resuming={resuming}
          resumeError={resumeError}
          onResume={onResume}
        />
      )}
      <div className="space-y-3">
        {reviews.map((r) => (
          <ReviewListItem key={r.id} review={r} runId={runId} />
        ))}
      </div>
    </div>
  );
}

function ReadyToResumeCard({
  reviewCount,
  resuming,
  resumeError,
  onResume,
}: {
  reviewCount: number;
  resuming: boolean;
  resumeError: string | null;
  onResume: () => Promise<void>;
}) {
  const reviewLabel =
    reviewCount === 1 ? "1 conferência" : `${reviewCount} conferências`;

  return (
    <Card aria-live="polite">
      <CardContent className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Tudo pronto para continuar</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Você concluiu {reviewLabel}. A análise continua de onde parou e isso
            costuma levar alguns minutos. Você pode acompanhar o progresso ou
            voltar quando estiver pronto.
          </p>
        </div>
        {resumeError && (
          <p
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
          >
            Não foi possível retomar a análise: {resumeError}
          </p>
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            autoFocus
            onClick={() => void onResume()}
            disabled={resuming}
            aria-busy={resuming}
            size="lg"
          >
            {resuming ? (
              <>
                <Spinner size="sm" />
                Retomando…
              </>
            ) : resumeError ? (
              "Tentar novamente"
            ) : (
              "Retomar análise"
            )}
          </Button>
          <Button
            variant="outline"
            size="lg"
            disabled={resuming}
            nativeButton={false}
            render={<Link href="/pipeline" />}
          >
            Voltar ao pipeline
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ReviewListError({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => Promise<void>;
}) {
  return (
    <Card>
      <CardContent>
        <p className="mb-3 text-sm text-loss">{error}</p>
        <Button size="sm" variant="outline" onClick={() => void onRetry()}>
          <RefreshCw className="mr-2 h-4 w-4" /> Tentar de novo
        </Button>
      </CardContent>
    </Card>
  );
}

function ReviewListEmpty() {
  return (
    <Card>
      <CardContent>
        <p className="mb-3 text-sm text-muted-foreground">
          Nenhuma conferência pendente nesta análise.
        </p>
        <Button
          size="sm"
          variant="outline"
          nativeButton={false}
          render={<Link href="/pipeline" />}
        >
          Voltar ao pipeline
        </Button>
      </CardContent>
    </Card>
  );
}

function ReviewListSkeleton() {
  return (
    <div aria-label="Carregando conferências" className="space-y-3">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-24 w-full rounded-lg" />
      ))}
    </div>
  );
}
