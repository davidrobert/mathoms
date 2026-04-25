"use client";

import { useRef, useState } from "react";
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import type {
  PipelineStageLog,
  PipelineStageActivity,
} from "@/lib/api";
import { formatDuration, stageStatusLabel, stageName } from "@/lib/format";
import { stageLlmFootnote } from "@/lib/pipelineTransparency";
import { Button } from "@/components/ui/button";
import { LiveStepProgress } from "./LiveStepProgress";
import { useNowInterval } from "./useNowInterval";
import { useStageStall } from "./useStageStall";

const VARIANT_COLORS: Record<string, string> = {
  neutral: "text-muted-foreground",
  info: "text-info-financial",
  success: "text-gain",
  error: "text-loss",
  warning: "text-warning",
  muted: "text-muted-foreground",
};

function StageStatusIcon({ stage }: { stage: PipelineStageLog }) {
  const st = stageStatusLabel(stage.status);
  if (stage.status === "running") {
    return (
      <Loader2
        className="h-4 w-4 shrink-0 animate-spin text-info-financial"
        aria-label="Executando"
      />
    );
  }
  return (
    <span
      className={`text-base ${VARIANT_COLORS[st.variant] ?? "text-muted-foreground"}`}
      aria-label={st.label}
    >
      {st.icon}
    </span>
  );
}

function StageRowLabel({ stage }: { stage: PipelineStageLog }) {
  const llmNote = stageLlmFootnote(stage.stage);
  return (
    <span className={`flex-1 ${stage.status === "running" ? "font-medium" : ""}`}>
      <span className="block">
        {stageName(stage.stage)}
        {stage.status === "needs_review" && (
          <span className="ml-2 text-xs text-warning">(revisão)</span>
        )}
        {llmNote && (
          <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
            {llmNote}
          </span>
        )}
      </span>
    </span>
  );
}

export function StageRow({
  stage,
  liveActivity,
  lastActivityByStageRef,
}: {
  stage: PipelineStageLog;
  liveActivity?: PipelineStageActivity;
  lastActivityByStageRef?: React.RefObject<Record<string, number>>;
}) {
  const [expanded, setExpanded] = useState(false);
  const running = stage.status === "running";
  const now = useNowInterval(running, 1000);
  const displayMs = running
    ? Math.max(0, now - new Date(stage.started_at).getTime())
    : stage.duration_ms;
  const emptyRef = useRef<Record<string, number>>({});
  const stall = useStageStall(
    running && liveActivity ? liveActivity : null,
    lastActivityByStageRef ?? emptyRef,
  );

  const rowBg =
    stage.status === "running"
      ? "bg-primary/5"
      : stage.status === "needs_review"
        ? "bg-warning/5"
        : "";

  return (
    <div>
      <div className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${rowBg}`}>
        <StageStatusIcon stage={stage} />
        <StageRowLabel stage={stage} />
        <span className="text-xs text-muted-foreground font-mono">
          {formatDuration(displayMs)}
        </span>
        {stage.errors && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-auto px-1.5 py-0.5 text-xs text-loss"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? "ocultar" : "ver erro"}
          </Button>
        )}
      </div>
      {expanded && stage.errors && (
        <pre className="mx-3 mb-1 max-h-40 overflow-auto rounded bg-loss/5 p-3 text-xs text-loss font-mono">
          {stage.errors}
        </pre>
      )}
      {stage.status === "running" && liveActivity && (
        <LiveStepProgress
          activity={liveActivity}
          elapsedMs={displayMs ?? undefined}
          stalled={stall.stalled}
          stalledForMs={stall.stalledForMs}
        />
      )}
    </div>
  );
}
