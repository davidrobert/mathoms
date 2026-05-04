"use client";

import Link from "next/link";
import { ArrowRight, FileText, PlayCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

import type { PatrimonioSnapshot } from "./usePlanoOverview";

interface ReportLinkActionProps {
  /** Onda 7 #4 (ADR-156) — snapshot do último Report (sourceReportId). */
  snapshot: PatrimonioSnapshot | null;
}

/** Onda 10 #2 — CTA primário para o relatório do mês.
 *
 * Casal abre /plano domingo, vê KPIs, mas não sabia que existe um
 * documento de 60 páginas que aprofunda os mesmos números. Esse CTA
 * resolve a desconexão `/plano` ↔ `/reports`.
 *
 * Estados:
 * - **Snapshot presente** → link "Abrir relatório de {período}".
 * - **Sem snapshot** → CTA outline "Gerar relatório" → /documents
 *   (onde o usuário sobe extratos para o pipeline gerar o relatório).
 */
export function ReportLinkAction({ snapshot }: ReportLinkActionProps) {
  if (!snapshot) {
    return (
      <Button size="sm" variant="outline" nativeButton={false} render={<Link href="/documents" />}>
        <PlayCircle className="mr-1.5 h-3.5 w-3.5" />
        Gerar relatório
      </Button>
    );
  }
  const label = formatMonthLabel(snapshot.asOf);
  return (
    <Button
      size="sm"
      nativeButton={false}
      render={<Link href={`/reports/${snapshot.sourceReportId}`} />}
    >
      <FileText className="mr-1.5 h-3.5 w-3.5" />
      Abrir relatório de {label}
      <ArrowRight className="ml-1 h-3.5 w-3.5" />
    </Button>
  );
}

function formatMonthLabel(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
  }).format(d);
}
