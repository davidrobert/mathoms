"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertCircle, AlertTriangle, ArrowRight, CheckCircle2 } from "lucide-react";

import {
  ApiError,
  listPipelineRuns,
  listStageReviews,
  resumePipelineRun,
  type DocumentResponse,
  type StageReviewResponse,
} from "@/lib/api";
import type { ValidationIssue } from "@/lib/api/pipeline";
import { getCopy } from "@/lib/validation-copy";
import { groupIssuesByCode, groupLegacyLines } from "@/lib/review-groups";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/Spinner";

const SAMPLE_SIZE = 4;

export interface QueueSample {
  label: string;
  documentId: string | null;
}

export interface QueueGroup {
  key: string;
  title: string;
  description: string;
  severity: "error" | "warning";
  count: number;
  countIsExact: boolean;
  samples: QueueSample[];
  documentIds: string[];
}

interface PendingState {
  runId: string;
  pendingReviews: StageReviewResponse[];
}

interface FixHandlers {
  onFixDocument: (documentId: string) => void;
  onFixSequence: (documentIds: string[]) => void;
}

function isSentinel(issue: ValidationIssue): boolean {
  return issue.context["truncated"] === true;
}

function issueSample(issue: ValidationIssue, docs: DocumentResponse[]): QueueSample {
  const docId = issue.context["document_id"];
  const doc = docs.find((d) => d.id === docId);
  const label =
    doc?.original_name ??
    String(issue.context["artifact_key"] ?? issue.legacy_message ?? "");
  return { label, documentId: doc ? doc.id : null };
}

function uniqueDocumentIds(issues: ValidationIssue[]): string[] {
  return [
    ...new Set(issues.map((i) => i.context["document_id"]).filter((v): v is string => !!v)),
  ];
}

function truncatedRemaining(issues: ValidationIssue[]): number {
  return issues
    .filter(isSentinel)
    .reduce((acc, i) => acc + Number(i.context["remaining"] ?? 0), 0);
}

function groupFromIssues(
  key: string,
  issues: ValidationIssue[],
  docs: DocumentResponse[],
): QueueGroup {
  const real = issues.filter((i) => !isSentinel(i));
  const remaining = truncatedRemaining(issues);
  const copy = getCopy(real[0]?.code ?? key);
  return {
    key,
    title: copy.title,
    description: copy.description.replace(/\$\{\w+\}/g, "").trim(),
    severity: real.some((i) => i.severity === "error") ? "error" : "warning",
    count: real.length + remaining,
    countIsExact: remaining === 0,
    samples: real.slice(0, SAMPLE_SIZE).map((i) => issueSample(i, docs)),
    documentIds: uniqueDocumentIds(real),
  };
}

function legacyGroup(g: { key: string; representative: string; lines: string[] }): QueueGroup {
  return {
    key: g.key,
    title: g.representative.split(/[;.]/)[0]?.trim() ?? g.representative,
    description: "",
    severity: "warning",
    count: g.lines.length,
    countIsExact: true,
    samples: [],
    documentIds: [],
  };
}

/** Constrói os grupos da fila a partir das reviews pendentes: issues
 * estruturadas (A29.l2) quando existem, senão grupos legacy sem link. */
export function buildQueueGroups(
  reviews: StageReviewResponse[],
  docs: DocumentResponse[],
): QueueGroup[] {
  const structured = reviews.flatMap((r) => r.validation_issues ?? []);
  if (structured.length > 0) {
    return groupIssuesByCode(structured).map((g) => groupFromIssues(g.key, g.issues, docs));
  }
  return reviews.flatMap((r) => groupLegacyLines(r.validation_errors)).map(legacyGroup);
}

async function fetchPendingState(workspaceId: string): Promise<PendingState | null> {
  const { runs } = await listPipelineRuns(workspaceId);
  const paused = runs.find((r) => r.status === "needs_review");
  if (!paused) return null;
  const reviews = await listStageReviews(workspaceId, paused.id);
  return {
    runId: paused.id,
    pendingReviews: reviews.filter((r) => r.status === "pending"),
  };
}

function usePendingReviews(workspaceId: string, refreshKey: number) {
  const [state, setState] = useState<PendingState | null>(null);
  const load = useCallback(
    () => fetchPendingState(workspaceId).then(setState, () => setState(null)),
    [workspaceId],
  );
  useEffect(() => {
    void load();
  }, [load, refreshKey]);
  const clear = useCallback(() => setState(null), []);
  return { state, clear };
}

export function PendingReviewQueue({
  workspaceId,
  docs,
  onFixDocument,
  onFixSequence,
  refreshKey,
}: FixHandlers & {
  workspaceId: string;
  docs: DocumentResponse[];
  refreshKey: number;
}) {
  const { state, clear } = usePendingReviews(workspaceId, refreshKey);
  const groups = useMemo(
    () => (state ? buildQueueGroups(state.pendingReviews, docs) : []),
    [state, docs],
  );
  if (!state) return null;
  if (state.pendingReviews.length === 0) {
    return <ResolvedBanner workspaceId={workspaceId} runId={state.runId} onResumed={clear} />;
  }
  return (
    <PausedQueueCard
      runId={state.runId}
      groups={groups}
      onFixDocument={onFixDocument}
      onFixSequence={onFixSequence}
    />
  );
}

function PausedQueueCard({
  runId,
  groups,
  onFixDocument,
  onFixSequence,
}: FixHandlers & { runId: string; groups: QueueGroup[] }) {
  return (
    <Card className="mb-6 border-alert/50">
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <AlertTriangle aria-hidden className="h-5 w-5 text-alert" />
          <h2 className="font-medium text-foreground">
            Sua análise está pausada esperando você
          </h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Encontramos pontos nos seus documentos que precisam de uma olhada
          antes de gerar o relatório. Resolva abaixo e depois conclua a
          conferência para a análise continuar.
        </p>
        <ul className="space-y-3">
          {groups.map((group) => (
            <li key={group.key}>
              <QueueGroupCard
                group={group}
                onFixDocument={onFixDocument}
                onFixSequence={onFixSequence}
              />
            </li>
          ))}
        </ul>
        <Button
          size="sm"
          nativeButton={false}
          render={<Link href={`/pipeline/runs/${runId}/reviews`} />}
        >
          Concluir conferência
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}

function ResolvedBanner({
  workspaceId,
  runId,
  onResumed,
}: {
  workspaceId: string;
  runId: string;
  onResumed: () => void;
}) {
  const [resuming, setResuming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleResume() {
    setResuming(true);
    setError(null);
    try {
      await resumePipelineRun(workspaceId, runId);
      onResumed();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Não foi possível retomar a análise");
    } finally {
      setResuming(false);
    }
  }

  return (
    <Card className="mb-6 border-gain/50" aria-live="polite">
      <CardContent className="space-y-3">
        <div className="flex items-center gap-3">
          <CheckCircle2 aria-hidden className="h-5 w-5 text-gain" />
          <h2 className="font-medium text-foreground">Tudo resolvido — retomar agora</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Não há mais pendências. A análise continua de onde parou; costuma
          levar alguns minutos.
        </p>
        {error && (
          <p role="alert" className="text-sm text-loss">
            {error}
          </p>
        )}
        <Button size="sm" onClick={handleResume} disabled={resuming} aria-busy={resuming}>
          {resuming ? (
            <span className="inline-flex items-center gap-2">
              <Spinner size="sm" className="text-primary-foreground" />
              Retomando…
            </span>
          ) : (
            "Retomar análise"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

function QueueGroupCard({
  group,
  onFixDocument,
  onFixSequence,
}: FixHandlers & { group: QueueGroup }) {
  const Icon = group.severity === "error" ? AlertCircle : AlertTriangle;
  const iconClass = group.severity === "error" ? "text-loss" : "text-alert";
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2">
        <Icon aria-hidden className={`h-4 w-4 shrink-0 ${iconClass}`} />
        <h3 className="min-w-0 flex-1 text-sm font-medium text-foreground">{group.title}</h3>
        <Badge variant={group.severity === "error" ? "destructive" : "secondary"}>
          {group.countIsExact ? group.count : `${group.count}+`}
        </Badge>
      </div>
      {group.description && (
        <p className="mt-1.5 text-xs text-muted-foreground">{group.description}</p>
      )}
      <QueueSampleList group={group} onFixDocument={onFixDocument} />
      {group.documentIds.length > 1 && (
        <Button
          size="sm"
          variant="outline"
          className="mt-2"
          onClick={() => onFixSequence(group.documentIds)}
        >
          Corrigir um por um ({group.documentIds.length})
        </Button>
      )}
    </div>
  );
}

function QueueSampleList({
  group,
  onFixDocument,
}: {
  group: QueueGroup;
  onFixDocument: (documentId: string) => void;
}) {
  if (group.samples.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1">
      {group.samples.map((sample, idx) => (
        <li key={idx} className="flex items-baseline gap-2 text-xs">
          <span className="min-w-0 flex-1 break-words font-mono text-foreground">
            {sample.label}
          </span>
          {sample.documentId !== null && (
            <button
              type="button"
              onClick={() => onFixDocument(sample.documentId!)}
              className="shrink-0 text-primary hover:underline focus-visible:underline"
            >
              Corrigir
            </button>
          )}
        </li>
      ))}
      {group.count > group.samples.length && (
        <li className="text-xs text-muted-foreground">
          e mais {group.count - group.samples.length}
        </li>
      )}
    </ul>
  );
}
