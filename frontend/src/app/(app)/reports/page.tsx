"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReports, type ReportResponse } from "@/lib/api";
import { formatDateShort, formatBytes } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, Calendar, ArrowRight } from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import type { UserWorkspace } from "@/lib/api";

export default function ReportsPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return <ReportsPageContent workspace={workspace} />;
}

function ReportsPageContent({ workspace }: { workspace: UserWorkspace }) {

  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listReports(workspace.id)
      .then((data) => setReports(data.reports))
      .catch(() => setError("Erro ao carregar relatórios"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Relatórios"
        description="Histórico de relatórios financeiros gerados pelo pipeline"
        actions={
          <Button nativeButton={false} render={<Link href="/pipeline" />}>
            Gerar novo relatório
          </Button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">
            fechar
          </button>
        </div>
      )}

      {reports.length === 0 ? (
        <div className="space-y-4">
          <EmptyState
            variant="no-reports"
            title="Nenhum relatório disponível."
            description="Envie documentos e execute o pipeline para gerar seu primeiro relatório deste período."
            action={{ label: "Enviar documentos →", href: "/documents" }}
          />
          <p className="text-center text-sm text-muted-foreground">
            <Link href="/plano" className="font-medium text-primary underline-offset-2 hover:underline">
              Ver ou ajustar metas no Plano
            </Link>
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <Link key={report.id} href={`/reports/${report.id}`} className="group block">
              <Card className="transition hover:ring-primary/30 hover:shadow-md">
                <CardContent className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium group-hover:text-primary transition-colors">
                        {report.title}
                      </h3>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-muted-foreground">
                        {report.period && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            {report.period}
                          </span>
                        )}
                        {report.size_bytes && (
                          <span>{formatBytes(report.size_bytes)}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-3">
                    <span className="text-sm text-muted-foreground">
                      {formatDateShort(report.created_at)}
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 transition group-hover:opacity-100" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
