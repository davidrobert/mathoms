"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Eye,
  EyeOff,
  Printer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getReportDownloadHtmlUrl } from "@/lib/api";
import { useReportMode } from "./ReportModeProvider";
import type { ReportMode } from "@/generated/report-layout";

interface ReportHeaderProps {
  reportId: string;
  title: string;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

const MODE_LABELS: Record<ReportMode, string> = {
  estrategico: "Estratégico",
  tatico: "Tático",
  usa: "EUA",
};

/** F9 · F1.1 — Header do relatório nativo.
 *
 * Barra fina com: voltar + título + seletor de modo + ações (toc, print,
 * download). Preserva a UX do header antigo (iframe) porém sem depender
 * do contexto JS do iframe para ações.
 *
 * Print server-side via Playwright virá em F4.2 — até lá, window.print()
 * nativo já funciona razoavelmente bem dado que tudo é SVG/HTML puro
 * (sem canvas).
 */
export function ReportHeader({
  reportId,
  title,
  sidebarOpen,
  onToggleSidebar,
}: ReportHeaderProps) {
  const { mode, setMode } = useReportMode();

  const handlePrint = () => {
    if (typeof window !== "undefined") window.print();
  };

  return (
    <div className="no-print flex items-center justify-between border-b border-[var(--surface-border)] bg-[var(--surface-card)] px-4 py-2">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          nativeButton={false}
          render={<Link href="/reports" />}
        >
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          Voltar
        </Button>
        <Separator orientation="vertical" className="h-5" />
        <h1 className="font-display text-sm font-semibold lg:text-base">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-1.5">
        {/* Mode selector */}
        <div
          role="tablist"
          aria-label="Modo de visualização"
          className="flex items-center gap-0.5 rounded-md border border-[var(--surface-border)] p-0.5 text-xs"
        >
          {(Object.keys(MODE_LABELS) as ReportMode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={
                mode === m
                  ? "rounded-sm bg-[var(--brand-primary)] px-2 py-1 font-medium text-[var(--brand-primary-foreground)]"
                  : "rounded-sm px-2 py-1 text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)]"
              }
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>

        <Separator orientation="vertical" className="mx-1 h-5" />

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={onToggleSidebar}
                aria-label={sidebarOpen ? "Ocultar índice" : "Mostrar índice"}
              />
            }
          >
            {sidebarOpen ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </TooltipTrigger>
          <TooltipContent>
            {sidebarOpen ? "Ocultar índice" : "Mostrar índice"}
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handlePrint}
                aria-label="Imprimir ou salvar PDF"
              />
            }
          >
            <Printer className="h-4 w-4" />
          </TooltipTrigger>
          <TooltipContent>Imprimir / PDF</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                nativeButton={false}
                render={
                  <Link
                    href={getReportDownloadHtmlUrl(reportId)}
                    target="_blank"
                    rel="noopener"
                    aria-label="Baixar HTML standalone"
                  />
                }
              />
            }
          >
            <Download className="h-4 w-4" />
          </TooltipTrigger>
          <TooltipContent>Baixar HTML standalone</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
