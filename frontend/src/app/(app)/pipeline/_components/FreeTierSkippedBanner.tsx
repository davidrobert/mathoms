"use client";

import Link from "next/link";
import { AlertTriangle, X } from "lucide-react";
import { getDismissedFreeTierRunId, setDismissedFreeTierRunId } from "./dismissedFreeTierBanner";

interface FreeTierSkippedBannerProps {
  runId: string;
  skippedStageCount: number;
  onDismiss: () => void;
}

export function FreeTierSkippedBanner({
  runId,
  skippedStageCount,
  onDismiss,
}: FreeTierSkippedBannerProps) {
  if (skippedStageCount === 0) return null;
  if (getDismissedFreeTierRunId() === runId) return null;

  function handleDismiss() {
    setDismissedFreeTierRunId(runId);
    onDismiss();
  }

  const label =
    skippedStageCount === 1
      ? "1 stage LLM foi pulado"
      : `${skippedStageCount} stages LLM foram pulados`;

  return (
    <div
      role="alert"
      className="mb-6 flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm"
    >
      <AlertTriangle
        className="mt-0.5 h-4 w-4 shrink-0 text-warning"
        aria-hidden="true"
      />
      <p className="flex-1 text-foreground">
        <span className="font-medium">{label} (plano gratuito).</span>{" "}
        Alguns documentos podem estar incompletos.{" "}
        <Link
          href="/config"
          className="font-medium text-warning underline underline-offset-2 hover:text-warning/80"
        >
          Faça upgrade para processar documentos completos.
        </Link>
      </p>
      <button
        onClick={handleDismiss}
        aria-label="Fechar aviso de plano gratuito"
        className="text-muted-foreground hover:text-foreground rounded p-0.5 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
