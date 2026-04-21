"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type {
  PipelineStageLog,
  PipelineStageActivity,
} from "@/lib/api";
import { formatDuration, stageStatusLabel, stageName } from "@/lib/format";
import { stageLlmFootnote } from "@/lib/pipelineTransparency";
import { Button } from "@/components/ui/button";
import { useNowInterval } from "./useNowInterval";

const VARIANT_COLORS: Record<string, string> = {
  neutral: "text-muted-foreground",
  info: "text-info-financial",
  success: "text-gain",
  error: "text-loss",
  warning: "text-warning",
  muted: "text-muted-foreground",
};

function StageRowLabel({ stage }: { stage: PipelineStageLog }) {
  const llmNote = stageLlmFootnote(stage.stage);
  return (
    <span className={`flex-1 ${stage.status === "running" ? "font-medium" : ""}`}>
      <span className="block">
        {stageName(stage.stage)}
        {llmNote && (
          <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
            {llmNote}
          </span>
        )}
      </span>
      {stage.status === "running" && (
        <span className="ml-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
      )}
      {stage.status === "needs_review" && (
        <span className="ml-2 text-xs text-warning">(revisão)</span>
      )}
    </span>
  );
}

function LiveActivityDetail({ activity }: { activity: PipelineStageActivity }) {
  if (!activity.message && !activity.file) return null;
  return (
    <div className="mx-3 mb-1 rounded-md border border-border/50 bg-muted/40 px-3 py-2 text-xs">
      {activity.message && (
        <p className="text-muted-foreground leading-snug">{activity.message}</p>
      )}
      {activity.file && (
        <p
          className="mt-1 font-mono text-[11px] text-foreground/90 truncate"
          title={activity.file}
        >
          Arquivo: {activity.file}
        </p>
      )}
    </div>
  );
}

export function StageRow({
  stage,
  liveActivity,
}: {
  stage: PipelineStageLog;
  liveActivity?: PipelineStageActivity;
}) {
  const st = stageStatusLabel(stage.status);
  const [expanded, setExpanded] = useState(false);
  const running = stage.status === "running";
  const now = useNowInterval(running, 1000);
  const displayMs = running
    ? Math.max(0, now - new Date(stage.started_at).getTime())
    : stage.duration_ms;

  const rowBg =
    stage.status === "running"
      ? "bg-primary/5"
      : stage.status === "needs_review"
        ? "bg-warning/5"
        : "";

  return (
    <div>
      <div className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${rowBg}`}>
        <span
          className={`text-base ${VARIANT_COLORS[st.variant] ?? "text-muted-foreground"} ${
            stage.status === "running" ? "animate-pulse" : ""
          }`}
        >
          {st.icon}
        </span>
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
      {stage.status === "running" && liveActivity && <LiveActivityDetail activity={liveActivity} />}
    </div>
  );
}
