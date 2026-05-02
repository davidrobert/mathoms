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
  const { reviews, loading, error, resuming, reload } = useReviewList(
    workspaceId,
    runId,
  );

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link
        href="/pipeline"
        className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden className="h-3 w-3" /> Voltar ao pipeline
      </Link>
      <PageHeader
        title="Revisões pendentes"
        description={`Run ${runId.slice(0, 8)}…`}
      />

      {loading && <ReviewListSkeleton />}
      {!loading && error && <ReviewListError error={error} onRetry={reload} />}
      {!loading && !error && reviews?.length === 0 && <ReviewListEmpty />}
      {!loading && !error && reviews && reviews.length > 0 && (
        <ReviewListBody reviews={reviews} runId={runId} resuming={resuming} />
      )}
    </div>
  );
}

function ReviewListBody({
  reviews,
  runId,
  resuming,
}: {
  reviews: StageReviewResponse[];
  runId: string;
  resuming: boolean;
}) {
  return (
    <div className="space-y-3">
      {resuming && (
        <p
          role="status"
          className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground"
        >
          <Spinner size="sm" />
          Retomando pipeline…
        </p>
      )}
      {reviews.map((r) => (
        <ReviewListItem key={r.id} review={r} runId={runId} />
      ))}
    </div>
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
          Nenhuma revisão pendente neste run.
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
    <div aria-label="Carregando revisões" className="space-y-3">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-24 w-full rounded-lg" />
      ))}
    </div>
  );
}
