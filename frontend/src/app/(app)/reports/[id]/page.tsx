"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { TooltipProvider } from "@/components/ui/tooltip";
import { getReport, type ReportResponse, ApiError } from "@/lib/api";
import { useReportData } from "@/hooks/useReportData";
import { ReportModeProvider } from "@/components/report/ReportModeProvider";
import { ReportShell } from "@/components/report/ReportShell";
import { MonthClosedBanner } from "@/components/report/MonthClosedBanner";
// F3.2: print CSS carregado apenas nesta rota
import "@/components/report/report-print.css";
import { Spinner } from "@/components/Spinner";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

/** F9 · ADR-076 · F1.1 — Rota nativa do relatório.
 *
 * Render React consumindo /reports/{id}/data. Cards ainda não migrados
 * aparecem como stubs.
 */
export default function ReportPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <ReportPageContent workspace={workspace} />;
}

function ReportPageContent({ workspace }: { workspace: UserWorkspace }) {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const dataState = useReportData(
    report?.has_analysis_data ? reportId : null,
    workspace.id,
  );

  useEffect(() => {
    const token = localStorage.getItem("fin_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    let cancelled = false;
    getReport(workspace.id, reportId)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((err) => {
        if (cancelled) return;
        if (
          err instanceof ApiError &&
          (err.status === 401 || err.status === 403)
        ) {
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
  }, [reportId, router, workspace.id]);

  // F11.3 — `?print=1` (PDF server-side): marca `<html>` para CSS opcional (sem useSearchParams → sem Suspense).
  useEffect(() => {
    const on =
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("print") === "1";
    if (on) {
      document.documentElement.setAttribute("data-print-route", "1");
    } else {
      document.documentElement.removeAttribute("data-print-route");
    }
    return () => {
      document.documentElement.removeAttribute("data-print-route");
    };
  }, [reportId]);

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
      <div className="mx-auto max-w-2xl px-6 py-10" data-report-pdf-error="1">
        <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-6">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
          <div>
            <p className="font-medium">
              Não foi possível carregar este relatório.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {metadataError}
            </p>
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

  // Estado 3: relatório pré-F9 (sem analysis data) — não pode mais ser exibido
  if (report && !report.has_analysis_data) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-10" data-report-pdf-legacy="1">
        <div className="space-y-4 rounded-lg border border-border bg-card p-6">
          <div>
            <p className="font-medium">Relatório indisponível</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Este relatório foi gerado antes do render nativo e não tem o
              snapshot JSON necessário para visualização. Gere um novo relatório
              a partir dos dados atuais.
            </p>
          </div>
          <Button
            variant="outline"
            nativeButton={false}
            render={<Link href="/reports" />}
          >
            Voltar para a lista
          </Button>
        </div>
      </div>
    );
  }

  // Estado 4: relatório F9+ — shell nativo
  return (
    <TooltipProvider>
      <ReportModeProvider initialMode="estrategico">
        <MonthClosedBanner workspaceId={workspace.id} period={report!.period} />
        <ReportShell
          reportId={reportId}
          workspaceId={workspace.id}
          reportTitle={report!.title}
          dataState={dataState}
          reportPeriod={report!.period}
          reportCreatedAt={report!.created_at}
          pipelineRunId={report!.pipeline_run_id}
          runOutcome={report!.run_outcome}
          sourceDocumentCount={report!.source_document_count}
          consumedDocumentCount={report!.consumed_document_count}
          familySurname={
            report!.workspace_family_surname ?? workspace.family_surname
          }
        />
      </ReportModeProvider>
    </TooltipProvider>
  );
}
