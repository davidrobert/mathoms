"use client";

import { useState } from "react";
import {
  Alert,
  Badge,
  IconBadge,
  SectionDivider,
  KpiCard,
  KpiGrid,
  KpiStrip,
  ScoreCard,
  PontoForteItem,
  PontosFortesList,
  CollapsibleSectionHeader,
  SplitCards,
  ComparisonBlock,
  PriorityBadge,
  DeadlineBadge,
  EffortBadge,
  Timeline,
  ChangelogList,
  Kanban,
  NotasCard,
  NotasInsightsGrid,
  NotasInsightCard,
  type KanbanItem,
} from "@/components/report/ui";

const KANBAN_ITEMS: KanbanItem[] = [
  { id: "1", titulo: "Rebalancear RF", coluna: "a_fazer", prioridade: "alta", prazoIso: "2026-05-01", categoria: "Investimentos" },
  { id: "2", titulo: "Revisar PGBL", coluna: "em_andamento", prioridade: "media", prazoIso: "2026-04-28" },
  { id: "3", titulo: "Atualizar orçamento", coluna: "concluido", prioridade: "baixa" },
  { id: "4", titulo: "Consultar imposto", coluna: "a_fazer", prioridade: "media", prazoIso: "2026-04-25" },
];

export function UiDevPlayground() {
  const [collapsed, setCollapsed] = useState(false);
  const [notas, setNotas] = useState("");
  const [kanban, setKanban] = useState(KANBAN_ITEMS);

  return (
    <div
      data-report-scope
      data-font-scale="compact"
      style={{ padding: 32, maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 40 }}
    >
      <header>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 800 }}>
          UI primitives — playground
        </h1>
        <p style={{ color: "var(--surface-muted-foreground)", marginTop: 4 }}>
          DEV only · Fase 3 do plano Report Premium.
        </p>
      </header>

      <section>
        <h2>Alerts</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Alert severity="info">Esse é um alerta informativo.</Alert>
          <Alert severity="success">Tudo certo por aqui.</Alert>
          <Alert severity="warning">Atenção à reserva de emergência.</Alert>
          <Alert severity="danger">Dívida de cartão ultrapassou o limite seguro.</Alert>
        </div>
      </section>

      <section>
        <h2>Badges</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(["green", "red", "yellow", "blue", "neutral"] as const).map((c) => (
            <Badge key={c} color={c}>{c}</Badge>
          ))}
          <PriorityBadge level="alta" />
          <PriorityBadge level="media" />
          <PriorityBadge level="baixa" />
          <EffortBadge effort="S" />
          <EffortBadge effort="R" />
          <EffortBadge effort="O" />
          <DeadlineBadge iso="2025-12-01" />
          <DeadlineBadge iso="2026-04-26" />
          <DeadlineBadge iso="2026-06-15" />
        </div>
      </section>

      <section>
        <h2>IconBadges</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <IconBadge color="blue" ariaLabel="Informação">i</IconBadge>
          <IconBadge color="green" ariaLabel="OK">✓</IconBadge>
          <IconBadge color="red" ariaLabel="Crítico">!</IconBadge>
          <IconBadge color="orange" ariaLabel="Atenção">⚠</IconBadge>
          <IconBadge color="dark" ariaLabel="Neutro">∙</IconBadge>
        </div>
      </section>

      <SectionDivider icon="§" ariaLabel="Divisor" />

      <section>
        <h2>KPI family</h2>
        <KpiGrid columns={4}>
          <KpiCard label="Patrimônio" value="R$ 1,2 mi" sub="+12% a/a" tone="default" />
          <KpiCard label="Meta IF" value="68%" tone="blue" accent="primary" progress={{ value: 0.68, tone: "blue" }} />
          <KpiCard label="Dívida" value="R$ 18k" tone="red" accent="danger" />
          <KpiCard label="Score" value="8.2" tone="green" accent="accent" hero />
        </KpiGrid>
        <KpiStrip
          items={[
            { label: "Hoje", value: "R$ 1,2 mi" },
            { label: "Meta", value: "R$ 5 mi", tone: "meta" },
            { label: "Gap mensal", value: "R$ 8.500", tone: "gap" },
            { label: "Progresso", value: "24%", progress: 0.24 },
            { label: "Ano alvo", value: "2041", tone: "year" },
          ]}
        />
      </section>

      <section>
        <h2>ScoreCard</h2>
        <ScoreCard
          value={7.8}
          max={10}
          classe="Bom"
          breakdown={[
            { dimensao: "Liquidez", valor: 8.5, max: 10, peso: 0.2, contribuicao: 1.7 },
            { dimensao: "Endividamento", valor: 6.2, max: 10, peso: 0.25, contribuicao: 1.55 },
            { dimensao: "Investimentos", valor: 9.0, max: 10, peso: 0.3, contribuicao: 2.7 },
            { dimensao: "Reserva", valor: 7.5, max: 10, peso: 0.25, contribuicao: 1.87 },
          ]}
          formula="Score = Σ(valor × peso)"
        />
      </section>

      <section>
        <h2>Pontos fortes</h2>
        <PontosFortesList>
          <PontoForteItem icon="✓" titulo="Reserva de emergência completa" descricao="12 meses de despesas cobertos em RF líquida." />
          <PontoForteItem icon="📈" titulo="Crescimento consistente" descricao="Patrimônio líquido cresceu 12% a/a." />
          <PontoForteItem icon="🎯" titulo="Diversificação saudável" descricao="Alocação equilibrada entre RF, RV e imóveis." />
        </PontosFortesList>
      </section>

      <section>
        <h2>Comparison</h2>
        <ComparisonBlock
          before={{ label: "Antes (Q4/2025)", value: "R$ 950k", note: "sem previdência" }}
          after={{ label: "Depois (Q1/2026)", value: "R$ 1,08 mi", note: "com aporte extra" }}
        />
      </section>

      <section>
        <h2>Collapsible section</h2>
        <CollapsibleSectionHeader
          title={<h3 style={{ margin: 0 }}>Seção colapsável</h3>}
          collapsed={collapsed}
          onToggle={() => setCollapsed((v) => !v)}
          hint={<span>(6 cards escondidos)</span>}
        >
          <p>Conteúdo revelado quando expandida.</p>
        </CollapsibleSectionHeader>
      </section>

      <section>
        <h2>SplitCards</h2>
        <SplitCards>
          <div style={{ padding: 20, background: "var(--surface-card)", borderRadius: 12, border: "1px solid var(--surface-border)" }}>Lado esquerdo</div>
          <div style={{ padding: 20, background: "var(--surface-card)", borderRadius: 12, border: "1px solid var(--surface-border)" }}>Lado direito</div>
        </SplitCards>
      </section>

      <section>
        <h2>Timeline</h2>
        <Timeline
          items={[
            { id: "t1", date: "24/04", action: "Revisar alocação RF", status: "pendente" },
            { id: "t2", date: "28/04", action: "Rebalanceamento trimestral", status: "aguardando" },
            { id: "t3", date: "02/05", action: "Fechar IRPF", status: "feito" },
          ]}
        />
      </section>

      <section>
        <h2>Changelog</h2>
        <ChangelogList
          ciclo="Ciclo 2026-Q2"
          entries={[
            { id: "c1", headline: "Nova meta de IF definida para 2041", meta: "+8 anos", severity: "highlight" },
            { id: "c2", headline: "PGBL revisado (limite 12%)", severity: "change" },
            { id: "c3", headline: "Reserva de emergência atingiu 12×", severity: "info" },
          ]}
        />
      </section>

      <section>
        <h2>Kanban (UI-only — backend wiring em Fase 8)</h2>
        <Kanban
          items={kanban}
          onMove={(id, to) =>
            setKanban((prev) =>
              prev.map((i) => (i.id === id ? { ...i, coluna: to } : i)),
            )
          }
        />
      </section>

      <section>
        <h2>Notas</h2>
        <NotasInsightsGrid>
          <NotasInsightCard tone="score" label="Score" value="7.8" sub="Bom" />
          <NotasInsightCard tone="cerbasi" label="Presente / Futuro" value="60/40" sub="equilibrado" />
          <NotasInsightCard tone="periodo" label="Próximo ciclo" value="Q3 2026" />
        </NotasInsightsGrid>
        <div style={{ marginTop: 16 }}>
          <NotasCard
            value={notas}
            onChange={setNotas}
            saveState="saved"
            onCopyMarkdown={() => navigator.clipboard?.writeText(notas)}
            onClear={() => setNotas("")}
          />
        </div>
      </section>
    </div>
  );
}
