"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { getReportHtmlUrl, clearToken } from "@/lib/api";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  ArrowLeft,
  AlertCircle,
  Printer,
  Download,
  FileSpreadsheet,
  ChevronRight,
  Eye,
  EyeOff,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TOC_SECTIONS = [
  { id: "resumo-executivo", label: "Resumo Executivo" },
  { id: "score-financeiro", label: "Score Financeiro" },
  { id: "patrimonio", label: "Patrimônio" },
  { id: "receitas", label: "Receitas" },
  { id: "despesas", label: "Despesas" },
  { id: "fluxo-de-caixa", label: "Fluxo de Caixa" },
  { id: "investimentos", label: "Investimentos" },
  { id: "categorias", label: "Categorias" },
  { id: "observacoes", label: "Observações" },
] as const;

export default function ReportViewPage() {
  const router = useRouter();
  const params = useParams();
  const reportId = params.id as string;
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeSection, setActiveSection] = useState<string>("");

  useEffect(() => {
    const token = localStorage.getItem("fin_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    const url = getReportHtmlUrl(reportId);
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((html) => {
        if (iframeRef.current) {
          const doc = iframeRef.current.contentDocument;
          if (doc) {
            doc.open();
            doc.write(html);
            doc.close();
          }
        }
        setLoading(false);
      })
      .catch((err) => {
        if (err.message.includes("401") || err.message.includes("403")) {
          clearToken();
          router.replace("/login");
        } else {
          setError("Erro ao carregar relatório");
          setLoading(false);
        }
      });
  }, [reportId, router]);

  const scrollIframeToSection = useCallback(
    (sectionId: string) => {
      const doc = iframeRef.current?.contentDocument;
      if (!doc) return;

      const headings = doc.querySelectorAll("h1, h2, h3");
      for (const heading of headings) {
        const text = heading.textContent?.toLowerCase().replace(/\s+/g, "-") ?? "";
        if (text.includes(sectionId) || heading.id === sectionId) {
          heading.scrollIntoView({ behavior: "smooth", block: "start" });
          setActiveSection(sectionId);
          return;
        }
      }

      const el = doc.getElementById(sectionId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        setActiveSection(sectionId);
      }
    },
    []
  );

  const handlePrint = useCallback(() => {
    const iframe = iframeRef.current;
    if (!iframe?.contentWindow) return;
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
  }, []);

  const handleDownloadHtml = useCallback(() => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    const html = doc.documentElement.outerHTML;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio-${reportId}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [reportId]);

  const handleExportTables = useCallback(async () => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;

    const { exportToXLSX } = await import("@/lib/export");

    const tables = doc.querySelectorAll("table");
    if (tables.length === 0) return;

    const XLSX = await import("xlsx");
    const wb = XLSX.utils.book_new();

    tables.forEach((table, idx) => {
      const caption =
        table.querySelector("caption")?.textContent?.trim() ||
        table.previousElementSibling?.textContent?.trim() ||
        `Tabela_${idx + 1}`;

      const sheetName = caption.slice(0, 31).replace(/[[\]*?/\\]/g, "_");
      const ws = XLSX.utils.table_to_sheet(table);
      XLSX.utils.book_append_sheet(wb, ws, sheetName);
    });

    const buf = XLSX.write(wb, { bookType: "xlsx", type: "array" });
    const blob = new Blob([buf], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio-${reportId}-tabelas.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [reportId]);

  return (
    <TooltipProvider>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col lg:h-screen">
        {/* Header bar */}
        <div className="no-print flex items-center justify-between border-b border-border bg-card px-4 py-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/reports" />}>
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Voltar
            </Button>
            <Separator orientation="vertical" className="h-5" />
            <h1 className="text-sm font-semibold lg:text-base">
              Visualizar Relatório
            </h1>
          </div>

          <div className="flex items-center gap-1.5">
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSidebarOpen((v) => !v)}
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

            <Separator orientation="vertical" className="mx-1 h-5" />

            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={handlePrint}
                    disabled={loading}
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
                    onClick={handleDownloadHtml}
                    disabled={loading}
                  />
                }
              >
                <Download className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent>Baixar HTML</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={handleExportTables}
                    disabled={loading}
                  />
                }
              >
                <FileSpreadsheet className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent>Exportar tabelas (XLSX)</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar TOC */}
          {sidebarOpen && (
            <aside className="sidebar-toc no-print hidden w-56 shrink-0 overflow-y-auto border-r border-border bg-card/50 p-3 lg:block">
              <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Índice
              </p>
              <nav className="flex flex-col gap-0.5">
                {TOC_SECTIONS.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => scrollIframeToSection(section.id)}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                      activeSection === section.id
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-muted-foreground"
                    )}
                  >
                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 shrink-0 transition-transform",
                        activeSection === section.id && "text-primary"
                      )}
                    />
                    {section.label}
                  </button>
                ))}
              </nav>
            </aside>
          )}

          {/* Main content: iframe */}
          <div className="relative flex-1">
            {loading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
                <Spinner size="lg" />
              </div>
            )}

            {error && (
              <div className="flex h-full items-center justify-center">
                <div className="flex items-center gap-3 rounded-lg bg-loss/10 p-6 text-loss">
                  <AlertCircle className="h-5 w-5 shrink-0" />
                  <div>
                    <p className="font-medium">{error}</p>
                    <p className="mt-1 text-sm opacity-80">
                      Verifique se o relatório existe e tente novamente.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <iframe
              ref={iframeRef}
              className={cn(
                "h-full w-full border-0",
                loading && "invisible"
              )}
              title="Relatório Financeiro"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
