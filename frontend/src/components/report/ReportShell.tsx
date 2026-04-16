"use client";

import { useMemo, useState } from "react";
import { AlertCircle } from "lucide-react";
import { Spinner } from "@/components/Spinner";
import { LAYOUT, type SectionSpec } from "@/generated/report-layout";
import { type UseReportDataState } from "@/hooks/useReportData";
import type { ReportAnalysisData } from "@/lib/api";
import { ReportHeader } from "./ReportHeader";
import { ReportToc, type TocEntry } from "./ReportToc";
import { ReportSection } from "./ReportSection";
import { ReportSectionStub } from "./ReportSectionStub";
import { useReportMode } from "./ReportModeProvider";
import { S1PatrimonioSection } from "./sections/S1PatrimonioSection";
import { S2FluxoCaixaSection } from "./sections/S2FluxoCaixaSection";
import { S3InvestimentosSection } from "./sections/S3InvestimentosSection";
import { S4RealEstateSection } from "./sections/S4RealEstateSection";
import { S7IndependenciaSection } from "./sections/S7IndependenciaSection";
import { S8PrevidenciaSection } from "./sections/S8PrevidenciaSection";
import { S9RiscosSection } from "./sections/S9RiscosSection";
import { S10SinteseSection } from "./sections/S10SinteseSection";

/** IDs de seções com render React completo (sem stubs).
 *  F2.A–G: todas as seções do modo estratégico migradas. */
const MIGRATED_SECTIONS = new Set([
  "S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10",
]);

interface ReportShellProps {
  reportId: string;
  reportTitle: string;
  dataState: UseReportDataState;
}

function selectSections(mode: "estrategico" | "tatico" | "usa"): SectionSpec[] {
  if (mode === "estrategico") return LAYOUT.estrategico.sections;
  if (mode === "tatico") return LAYOUT.tatico.sections;
  return LAYOUT.usa.sections;
}

/** F9 · F1.1 — Shell nativo do relatório.
 *
 * Lê o `report-layout.yaml` gerado como constante TS, itera as seções do
 * modo ativo, e renderiza stubs (F1.1) ou componentes reais (F2.A–F2.H
 * conforme migrados). O TOC é derivado das mesmas seções filtradas.
 *
 * Loading/error são tratados aqui — a rota page.tsx apenas orquestra
 * useReportData e entrega o estado.
 */
export function ReportShell({
  reportId,
  reportTitle,
  dataState,
}: ReportShellProps) {
  const { mode } = useReportMode();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const enabledSections = useMemo<SectionSpec[]>(
    () => selectSections(mode).filter((s) => s.enabled),
    [mode],
  );

  const tocEntries = useMemo<TocEntry[]>(
    () => enabledSections.map((s) => ({ id: s.id, label: s.title })),
    [enabledSections],
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col lg:h-screen">
      <ReportHeader
        reportId={reportId}
        title={reportTitle}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
      />

      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && <ReportToc sections={tocEntries} />}

        <main className="relative flex-1 overflow-y-auto bg-[var(--surface-background)]">
          {dataState.status === "loading" && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--surface-background)]/80">
              <Spinner size="lg" />
            </div>
          )}

          {dataState.status === "error" && (
            <div className="mx-auto max-w-[960px] px-6 pt-8">
              <div className="flex items-start gap-3 rounded-lg bg-[color-mix(in_srgb,var(--semantic-loss)_10%,transparent)] p-6 text-[var(--semantic-loss)]">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="font-display font-medium">
                    Não foi possível carregar os dados deste relatório.
                  </p>
                  <p className="mt-1 text-sm opacity-80">
                    {dataState.error.message}
                  </p>
                  <p className="mt-2 text-sm opacity-80">
                    Você pode baixar o HTML standalone pelo botão de download
                    no topo.
                  </p>
                </div>
              </div>
            </div>
          )}

          {dataState.status === "success" && (
            <article
              className="mx-auto max-w-[960px] px-6 py-8 font-body text-[var(--surface-foreground)]"
              data-report-mode={mode}
            >
              <header className="mb-10 border-b border-[var(--surface-border)] pb-6">
                <p className="mb-2 font-mono text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                  {dataState.data.periodo_dados ?? "Período não informado"}
                </p>
                <h1 className="font-display text-3xl font-bold leading-tight text-[var(--surface-foreground)]">
                  {reportTitle}
                </h1>
              </header>

              {enabledSections.map((section) =>
                MIGRATED_SECTIONS.has(section.id) ? (
                  <MigratedSection
                    key={section.id}
                    sectionId={section.id}
                    data={dataState.data}
                  />
                ) : (
                  <ReportSection
                    key={section.id}
                    id={section.id}
                    title={section.title}
                  >
                    <ReportSectionStub
                      reportId={reportId}
                      cardIds={(section.cards ?? [])
                        .filter((c) => c.enabled)
                        .map((c) => c.id)}
                      chartIds={(section.charts ?? [])
                        .filter((c) => c.enabled)
                        .map((c) => c.id)}
                    />
                  </ReportSection>
                ),
              )}
            </article>
          )}
        </main>
      </div>
    </div>
  );
}

/** Dispatcher para seções migradas. Cada lote F2.A–F2.H adiciona um case. */
function MigratedSection({
  sectionId,
  data,
}: {
  sectionId: string;
  data: ReportAnalysisData;
}) {
  switch (sectionId) {
    case "S1":
      return <S1PatrimonioSection data={data} />;
    case "S2":
      return <S2FluxoCaixaSection data={data} />;
    case "S3":
      return <S3InvestimentosSection data={data} />;
    case "S4":
      return <S4RealEstateSection data={data} />;
    case "S7":
      return <S7IndependenciaSection data={data} />;
    case "S8":
      return <S8PrevidenciaSection data={data} />;
    case "S9":
      return <S9RiscosSection data={data} />;
    case "S10":
      return <S10SinteseSection data={data} />;
    // F2.H: USA sections (U1–U4)
    default:
      return null;
  }
}
