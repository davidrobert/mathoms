"use client";

import { useMemo } from "react";
import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { Spinner } from "@/components/Spinner";
import pkg from "../../../package.json";
import { LAYOUT, type SectionSpec } from "@/generated/report-layout";
import { type UseReportDataState } from "@/hooks/useReportData";
import type { ReportAnalysisData } from "@/lib/api";
import { formatPeriodCoverPtBR } from "@/lib/format";
import { ExecutiveSummarySection } from "./ExecutiveSummarySection";
import { ReportPremissasBlock } from "./ReportPremissasBlock";
import { ReportSourceStrip } from "./ReportSourceStrip";
import { ReportToc, type TocGroup } from "./ReportToc";
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
import { PlanoDeAcaoSection } from "./sections/PlanoDeAcao";
import { ApendiceASection } from "./sections/ApendiceASection";
import {
  ApendiceBSection,
  ApendiceCSection,
  ApendiceDSection,
  ApendiceESection,
} from "./sections/ApendicesSections";
import { PerfilFamiliaCard } from "./cards";
import {
  U1MudancaEuaSection,
  U2GreenCardSection,
  U3NclexSection,
  U4SimulacaoMarianaSection,
} from "./sections/UsaSections";
import {
  ReportActions,
  ReportCover,
  ReportTopNav,
  FloatingNav,
  AppearanceMenu,
  SkipNav,
  ExportToolbar,
  type CoverMeta,
  type NavGroup,
} from "./shell";
import { useReportFontScale } from "./useReportFontScale";
import { useReportTocOpen } from "./useReportTocOpen";

const COVER_MONTH_SHORT_PT = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
];

/** v2.F.3b — "Gerado em" no cover: `10 abr 2026, 16h25`.
 *
 * Falha graciosamente: retorna o ISO original se não parsear.
 */
function formatGeneratedAtPtBR(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const day = String(d.getDate()).padStart(2, "0");
  const month = COVER_MONTH_SHORT_PT[d.getMonth()];
  const year = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${day} ${month} ${year}, ${hh}h${mm}`;
}

/** Todas as seções de todos os modos estão migradas (F2.A–H + Fase D).
 * ADR-151 (Direção E): Modo Tático removido — T1-T6 não são mais renderizados. */
const MIGRATED_SECTIONS = new Set([
  // Estratégico
  "S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10",
  // USA
  "U1", "U2", "U3", "U4",
  // A7.2a · ADR-136 — Plano de Ação (Decision aggregate, agora no Estratégico)
  "plano_de_acao",
  // Apêndices
  "APP_A", "APP_B", "APP_C", "APP_D", "APP_E",
]);

interface ReportShellProps {
  reportId: string;
  /** F8 · ADR-123 — necessário para endpoints de colaboração (T3/T6). */
  workspaceId: string;
  reportTitle: string;
  dataState: UseReportDataState;
  /** Metadados do relatório (API) — F11.4 origem dos dados. */
  reportPeriod: string | null;
  reportCreatedAt: string;
  /** F11.4a — opcional; link para a execução no Pipeline. */
  pipelineRunId?: string | null;
  /** F11.4a — `sourceDocumentCount`: docs prontos no workspace (mutável); `consumedDocumentCount`: docs extraídos pela run (imutável). */
  sourceDocumentCount?: number | null;
  consumedDocumentCount?: number | null;
  /** v2.F.3b — sobrenome da família (de ReportResponse.workspace_family_surname).
   * Quando ausente, o cover usa badge fallback e omite o card "Família". */
  familySurname?: string | null;
}

function selectSections(mode: "estrategico" | "usa"): SectionSpec[] {
  if (mode === "estrategico") return LAYOUT.estrategico.sections;
  return LAYOUT.usa.sections;
}

/** Mapa section_id → title para lookup rápido (usado pelo buildNavGroups). */
function buildTitleMap(): Record<string, string> {
  const map: Record<string, string> = {};
  for (const s of LAYOUT.estrategico.sections) map[s.id] = s.title;
  for (const a of LAYOUT.estrategico.appendices ?? []) map[a.id] = a.title;
  for (const s of LAYOUT.usa.sections) map[s.id] = s.title;
  return map;
}

/** Encurta título da seção para uso no top-nav: "X — Y" → "X". */
function shortLabel(title: string): string {
  return title.split(" — ")[0].trim();
}

/** Converte LAYOUT.navigation (Fase 5) em grupos para ReportTopNav.
 *
 * Cai em fallback computacional (mesma lógica anterior) se o YAML não
 * tiver `navigation:` — backcompat caso alguém consuma um layout antigo.
 */
function buildNavGroups(): {
  estrategico: NavGroup[];
  usa: NavGroup[];
} {
  const titles = buildTitleMap();
  const nav = LAYOUT.navigation;
  if (nav?.estrategico) {
    const mapGroup = (groups: NonNullable<typeof nav.estrategico>): NavGroup[] =>
      groups.map((g) => ({
        label: g.label,
        links: g.links.map((l) => ({
          id: l.section_id,
          label: shortLabel(titles[l.section_id] ?? l.section_id),
          num: l.num,
          isAppendix: l.is_appendix,
        })),
      }));
    return {
      estrategico: mapGroup(nav.estrategico),
      usa: nav.usa ? mapGroup(nav.usa) : [],
    };
  }

  // Fallback (pré-Fase 5) — derivado das seções enabled
  const strategic = LAYOUT.estrategico.sections.filter((s) => s.enabled);
  return {
    estrategico: [
      {
        links: strategic.map((s) => ({ id: s.id, label: shortLabel(s.title), num: s.id })),
      },
    ],
    usa: [
      {
        links: LAYOUT.usa.sections
          .filter((s) => s.enabled)
          .map((s) => ({ id: s.id, label: shortLabel(s.title), num: s.id })),
      },
    ],
  };
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
  workspaceId,
  reportTitle,
  dataState,
  reportPeriod,
  reportCreatedAt,
  pipelineRunId,
  sourceDocumentCount,
  consumedDocumentCount,
  familySurname,
}: ReportShellProps) {
  const { mode } = useReportMode();
  const { open: sidebarOpen, toggle: toggleSidebar } = useReportTocOpen();

  const analysisPeriodFromSnapshot =
    dataState.status === "success"
      ? (typeof dataState.data.periodo_dados === "string"
          ? dataState.data.periodo_dados
          : undefined) ??
        (typeof dataState.data.data_analise === "string"
          ? dataState.data.data_analise
          : undefined)
      : undefined;

  const enabledSections = useMemo<SectionSpec[]>(
    () => selectSections(mode).filter((s) => s.enabled),
    [mode],
  );

  const navGroups = useMemo(buildNavGroups, []);

  /** Grupos do TOC lateral / drawer mobile — mesma estrutura do `navGroups`,
   * mas com títulos completos das seções (a faixa do topo encurta via
   * `shortLabel`). Apêndices entram como grupo "Apêndices" via YAML. */
  const tocGroups = useMemo<TocGroup[]>(() => {
    const titles = buildTitleMap();
    const nav = LAYOUT.navigation;
    const modeNav = nav?.[mode];
    if (modeNav) {
      return modeNav.map((g) => ({
        label: g.label,
        entries: g.links.map((l) => ({
          id: l.section_id,
          label: titles[l.section_id] ?? l.section_id,
          num: l.num,
          isAppendix: l.is_appendix,
        })),
      }));
    }
    return [
      {
        entries: enabledSections.map((s) => ({ id: s.id, label: s.title })),
      },
    ];
  }, [mode, enabledSections]);

  const { scale: fontScale } = useReportFontScale();

  const coverMeta = useMemo<CoverMeta[]>(() => {
    if (dataState.status !== "success") return [];
    const generated = formatGeneratedAtPtBR(reportCreatedAt);
    const periodValue = formatPeriodCoverPtBR(
      analysisPeriodFromSnapshot ?? reportPeriod ?? null,
    );
    const versionValue = pkg.version ? `Mathoms v${pkg.version}` : "Mathoms";
    const surname = familySurname?.trim();
    const cards: CoverMeta[] = [];
    if (surname) {
      cards.push({ label: "Família", value: surname });
    }
    cards.push(
      { label: "Período de referência", value: periodValue },
      { label: "Gerado em", value: generated },
      { label: "Versão", value: versionValue },
    );
    return cards;
  }, [
    dataState.status,
    analysisPeriodFromSnapshot,
    reportPeriod,
    reportCreatedAt,
    familySurname,
  ]);

  return (
    <div
      className="flex h-[calc(100vh-3.5rem)] flex-col lg:h-screen"
      data-report-scope
      data-font-scale={fontScale}
    >
      <SkipNav targetId="report-main" />

      <ReportTopNav
        groupsByMode={navGroups}
        brand={
          <nav aria-label="Trilha de navegação" className="flex items-center gap-1.5 text-xs">
            <Link
              href="/reports"
              className="text-white/60 hover:text-white"
              style={{ fontFamily: "var(--font-body)" }}
            >
              Relatórios
            </Link>
            <span aria-hidden className="text-white/30">/</span>
            <span
              className="font-medium text-white"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {reportTitle}
            </span>
          </nav>
        }
        actions={
          <>
            <ReportActions
              reportId={reportId}
              workspaceId={workspaceId}
              sidebarOpen={sidebarOpen}
              onToggleSidebar={toggleSidebar}
            />
            <span className="mx-1 hidden h-5 w-px bg-white/15 md:inline-block" aria-hidden />
            <AppearanceMenu />
          </>
        }
      />

      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && (
          <div className="hidden md:block">
            <ReportToc groups={tocGroups} />
          </div>
        )}

        <main
          id="report-main"
          className="relative flex-1 overflow-y-auto bg-[var(--surface-background)]"
        >
          {dataState.status === "loading" && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[var(--surface-background)]/80">
              <Spinner size="lg" />
            </div>
          )}

          {dataState.status === "error" && (
            <div className="max-w-[1120px] px-10 pt-8">
              <div className="flex items-start gap-3 rounded-lg bg-[color-mix(in_srgb,var(--semantic-loss)_10%,transparent)] p-6 text-[var(--semantic-loss)]">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="font-display font-medium">
                    Não foi possível carregar os dados deste relatório.
                  </p>
                  <p className="mt-1 text-sm opacity-80">
                    {dataState.error.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          {dataState.status === "success" && (
            <>
              {mode === "estrategico" && (
                <ReportCover
                  title="Planejamento Financeiro"
                  subtitle="Pessoal e Patrimonial"
                  familySurname={familySurname}
                  meta={coverMeta}
                />
              )}
            <article
              className="max-w-[1120px] px-10 py-8 font-body text-[var(--surface-foreground)]"
              data-report-mode={mode}
              data-report-ready="true"
            >
              <ReportPremissasBlock data={dataState.data} />

              {/* Sumário Executivo (Hero KPI) — modo estratégico, antes do Perfil
                * Paridade com EXEMPLO_DE_RELATORIO.html:1376 (id="kpis"). */}
              {mode === "estrategico" && (
                <ExecutiveSummarySection data={dataState.data} />
              )}

              {/* Perfil da Família — modo estratégico, acima das seções */}
              {mode === "estrategico" && (
                <PerfilFamiliaCard
                  narrativas={dataState.data.narrativas as Record<string, unknown> | undefined}
                />
              )}

              {enabledSections.map((section) =>
                MIGRATED_SECTIONS.has(section.id) ? (
                  <MigratedSection
                    key={section.id}
                    sectionId={section.id}
                    data={dataState.data}
                    workspaceId={workspaceId}
                  />
                ) : (
                  <ReportSection
                    key={section.id}
                    id={section.id}
                    title={section.title}
                  >
                    <ReportSectionStub
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

              {/* Apêndices — modo estratégico */}
              {mode === "estrategico" &&
                (LAYOUT.estrategico.appendices ?? [])
                  .filter((a) => a.enabled)
                  .map((a) =>
                    MIGRATED_SECTIONS.has(a.id) ? (
                      <MigratedSection
                        key={a.id}
                        sectionId={a.id}
                        data={dataState.data}
                        workspaceId={workspaceId}
                        reportId={reportId}
                      />
                    ) : null,
                  )}
            </article>
            <ReportSourceStrip
              reportPeriod={reportPeriod}
              analysisPeriod={analysisPeriodFromSnapshot}
              generatedAtIso={reportCreatedAt}
              pipelineRunId={pipelineRunId}
              sourceDocumentCount={sourceDocumentCount}
              consumedDocumentCount={consumedDocumentCount}
            />
            <ExportToolbar />
            </>
          )}
        </main>
      </div>
      <FloatingNav tocGroups={tocGroups} />
    </div>
  );
}

/** Dispatcher para seções migradas. Cada lote F2.A–F2.H adiciona um case. */
function MigratedSection({
  sectionId,
  data,
  workspaceId,
}: {
  sectionId: string;
  data: ReportAnalysisData;
  workspaceId: string;
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
    // USA
    case "U1":
      return <U1MudancaEuaSection data={data} />;
    case "U2":
      return <U2GreenCardSection data={data} />;
    case "U3":
      return <U3NclexSection data={data} />;
    case "U4":
      return <U4SimulacaoMarianaSection data={data} />;
    // A7.2a · ADR-136 — Plano de Ação (Decisões editoriais)
    case "plano_de_acao":
      return <PlanoDeAcaoSection workspaceId={workspaceId} />;
    // Apêndices
    case "APP_A":
      return <ApendiceASection data={data} />;
    case "APP_B":
      return <ApendiceBSection data={data} />;
    case "APP_C":
      return <ApendiceCSection data={data} />;
    case "APP_D":
      return <ApendiceDSection data={data} />;
    case "APP_E":
      return <ApendiceESection data={data} />;
    default:
      return null;
  }
}
