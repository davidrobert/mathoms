"use client";

import { Lock } from "lucide-react";
import { useEffect, useState } from "react";

import {
  getActivePublication,
  normalizePeriodYyyymm,
  type ReportPublicationResponse,
} from "@/lib/api/report-publications";

export interface MonthClosedBannerProps {
  workspaceId: string;
  period: string | null;
}

function formatPublishedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

/** ADR-186 — banner cinza V1: avisa que o mês está fechado e mudanças retroativas estão bloqueadas. */
export function MonthClosedBanner({ workspaceId, period }: MonthClosedBannerProps) {
  const periodYyyymm = normalizePeriodYyyymm(period);
  const [publication, setPublication] = useState<ReportPublicationResponse | null>(null);

  useEffect(() => {
    if (!periodYyyymm) return;
    let cancelled = false;
    getActivePublication(workspaceId, periodYyyymm)
      .then((p) => {
        if (!cancelled) setPublication(p);
      })
      .catch(() => {
        // Silencioso: erro não impede o relatório de renderizar.
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, periodYyyymm]);

  if (!publication) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="month-closed-banner"
      style={{
        marginTop: 12,
        marginBottom: 12,
        padding: "10px 14px",
        borderRadius: 8,
        background: "var(--surface-muted)",
        color: "var(--surface-muted-foreground)",
        display: "flex",
        alignItems: "center",
        gap: 8,
        fontSize: "0.875rem",
      }}
    >
      <Lock className="h-4 w-4" aria-hidden="true" />
      <span>
        Relatório publicado em {formatPublishedAt(publication.published_at)}.
        Mudanças retroativas bloqueadas para este mês.
      </span>
    </div>
  );
}
