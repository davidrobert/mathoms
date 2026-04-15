"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { TooltipProvider } from "@/components/ui/tooltip";
import { getReport, type ReportResponse, ApiError } from "@/lib/api";
import { useReportData } from "@/hooks/useReportData";
import { ReportModeProvider } from "@/components/report/ReportModeProvider";
import { ReportShell } from "@/components/report/ReportShell";
import { Spinner } from "@/components/Spinner";
import { AlertCircle, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { getReportDownloadHtmlUrl } from "@/lib/api";

/** F9 · ADR-076 · F1.1 — Rota nativa do relatório.
 *
 * Substitui o iframe antigo (que renderizava o HTML do E6) por um render
 * React nativo consumindo /reports/{id}/data. Cards ainda não migrados
 * aparecem como stubs com link para download do HTML completo.
 *
 * Design tokens (Plus Jakarta + Inter + navy/verde) são aplicados em F1.2.
 */
export default function ReportPage() {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const dataState = useReportData(report?.has_analysis_data ? reportId : null);

  useEffect(() => {
    const token = localStorage.getItem("fin_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    let cancelled = false;
    getReport(reportId)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.replace("/login");
          return;
        }
        setMetadataError(
          err instanceof Error ? err.message : "Erro ao carregar metadados.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [reportId, router]);

  // Estado 1: carregando metadados
  if (!report && !metadataError) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  // Estado 2: erro no metadados
  if (metadataError) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-10">
        <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-6">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
          <div>
            <p className="font-medium">Não foi possível carregar este relatório.</p>
            <p className="mt-1 text-sm text-muted-foreground">{metadataError}</p>
            <Button
              variant="outline"
              size="sm"
              nativeButton={false}
              className="mt-4"
              render={<Link href="/reports" />}
            >
              Voltar para a lista
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Estado 3: relatório pré-F9 (sem analysis data) — oferece download standalone
  if (report && !report.has_analysis_data) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-10">
        <div className="space-y-4 rounded-lg border border-border bg-card p-6">
          <div>
            <p className="font-medium">Relatório gerado antes da migração F9</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Este relatório foi gerado antes do render nativo e não tem o
              snapshot JSON necessário para a visualização em React. Baixe
              a versão HTML standalone para ver o conteúdo completo.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              nativeButton={false}
              render={
                <Link
                  href={getReportDownloadHtmlUrl(reportId)}
                  target="_blank"
                  rel="noopener"
                />
              }
            >
              <FileDown className="mr-1.5 h-4 w-4" />
              Baixar HTML standalone
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href="/reports" />}
            >
              Voltar
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Estado 4: relatório F9+ — shell nativo
  return (
    <TooltipProvider>
      <ReportModeProvider initialMode="estrategico">
        <ReportShell
          reportId={reportId}
          reportTitle={report!.title}
          dataState={dataState}
        />
      </ReportModeProvider>
    </TooltipProvider>
  );
}
