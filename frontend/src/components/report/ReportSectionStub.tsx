import Link from "next/link";
import { Construction, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getReportDownloadHtmlUrl } from "@/lib/api";
import { ReportCard } from "./ReportCard";
import { useWorkspace } from "@/lib/WorkspaceProvider";

interface ReportSectionStubProps {
  reportId: string;
  cardIds: string[];
  chartIds: string[];
}

/** F9 · F1.1 — Stub mostrado enquanto um card ainda não migrou para React.
 *
 * Estratégia de migração por lotes (2.A–2.H): cada lote substitui alguns
 * stubs por componentes reais. Enquanto isso, o usuário vê uma mensagem
 * clara e um link para baixar o HTML standalone completo (F1.5).
 *
 * Não é um erro — é progresso visível.
 */
export function ReportSectionStub({
  reportId,
  cardIds,
  chartIds,
}: ReportSectionStubProps) {
  const { workspace } = useWorkspace();
  if (!workspace) return null;
  return (
    <ReportCard variant="neutral" size="full">
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <Construction className="mt-0.5 h-5 w-5 shrink-0 text-[var(--brand-neutral)]" />
          <div className="space-y-1">
            <p className="font-display font-medium text-[var(--surface-foreground)]">
              Conteúdo em migração para a nova experiência
            </p>
            <p className="text-sm text-[var(--surface-muted-foreground)]">
              Esta seção está sendo migrada do relatório standalone para a
              visualização nativa. Durante a transição, você pode baixar a
              versão completa em HTML.
            </p>
          </div>
        </div>

        {(cardIds.length > 0 || chartIds.length > 0) && (
          <div className="rounded-md bg-[var(--surface-muted)] px-4 py-3 text-xs font-mono text-[var(--surface-muted-foreground)]">
            {cardIds.length > 0 && (
              <div>cards: {cardIds.join(", ")}</div>
            )}
            {chartIds.length > 0 && (
              <div>charts: {chartIds.join(", ")}</div>
            )}
          </div>
        )}

        <div>
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={
              <Link
                href={getReportDownloadHtmlUrl(workspace.id, reportId)}
                target="_blank"
                rel="noopener"
              />
            }
          >
            <FileDown className="mr-1.5 h-4 w-4" />
            Baixar HTML completo
          </Button>
        </div>
      </div>
    </ReportCard>
  );
}
