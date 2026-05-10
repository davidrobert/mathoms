"use client";

import { Fragment } from "react";
import Link from "next/link";
import { Eye, EyeOff, FileText, Printer } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useReportMode } from "@/components/report/ReportModeProvider";
import type { ReportMode } from "@/generated/report-layout";
import { getReportDownloadPdfUrl } from "@/lib/api";

interface ReportActionsProps {
  readonly reportId: string;
  readonly workspaceId: string;
  readonly sidebarOpen: boolean;
  readonly onToggleSidebar: () => void;
}

const MODE_LABELS: Record<ReportMode, string> = {
  estrategico: "Estratégico",
};

const MODE_TOOLTIPS: Record<ReportMode, string> = {
  estrategico: "Visão patrimonial e estratégica de longo prazo",
};

// ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA removido.
// Enquanto único modo, tablist se auto-oculta — reativar adicionando entry em VISIBLE_MODES.
const VISIBLE_MODES: readonly ReportMode[] = ["estrategico"];

/** Action zone do header unificado: Modo (multi-segment) + TOC + Print + PDF.
 *
 * Renderizada à direita do `ReportTopNav` (sticky, dark gradient). Estilo
 * alinhado ao gradiente: borders e texto em rgba(255,255,255,*). Toggle TOC
 * só aparece em md+ porque a sidebar é `hidden md:block`. Mode tablist
 * só aparece quando `VISIBLE_MODES.length > 1` (auto-hide para single mode).
 */
export function ReportActions({
  reportId,
  workspaceId,
  sidebarOpen,
  onToggleSidebar,
}: ReportActionsProps) {
  const { mode, setMode } = useReportMode();

  const handlePrint = () => {
    if (typeof window !== "undefined") window.print();
  };

  return (
    <div className="flex items-center gap-1.5">
      {VISIBLE_MODES.length > 1 && (
        <>
          <div
            role="tablist"
            aria-label="Modo de visualização"
            className="flex items-center gap-0.5 rounded-md border border-white/15 p-0.5 text-xs"
          >
            {VISIBLE_MODES.map((m) => (
              <Fragment key={m}>
                <Tooltip>
                  <TooltipTrigger
                    render={
                      <button
                        type="button"
                        role="tab"
                        aria-selected={mode === m}
                        onClick={() => setMode(m)}
                        className={
                          mode === m
                            ? "rounded-sm bg-white/15 px-2 py-1 font-medium text-white"
                            : "rounded-sm px-2 py-1 text-white/60 hover:bg-white/10 hover:text-white/90"
                        }
                      />
                    }
                  >
                    {MODE_LABELS[m]}
                  </TooltipTrigger>
                  <TooltipContent>{MODE_TOOLTIPS[m]}</TooltipContent>
                </Tooltip>
              </Fragment>
            ))}
          </div>

          <span
            className="mx-1 hidden h-5 w-px bg-white/15 md:inline-block"
            aria-hidden
          />
        </>
      )}

      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={onToggleSidebar}
              aria-label={sidebarOpen ? "Ocultar índice" : "Mostrar índice"}
              className="hidden rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white md:inline-flex"
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
            <button
              type="button"
              onClick={handlePrint}
              aria-label="Imprimir ou salvar PDF"
              className="rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
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
            <Link
              href={getReportDownloadPdfUrl(workspaceId, reportId)}
              target="_blank"
              rel="noopener"
              aria-label="Baixar PDF"
              className="rounded-md p-1.5 text-white/70 hover:bg-white/10 hover:text-white"
            />
          }
        >
          <FileText className="h-4 w-4" />
        </TooltipTrigger>
        <TooltipContent>Baixar PDF</TooltipContent>
      </Tooltip>
    </div>
  );
}
