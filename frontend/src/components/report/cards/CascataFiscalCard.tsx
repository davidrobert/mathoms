"use client";

import { AlertTriangle } from "lucide-react";

import type { CascataPayload, CascataTrigger, TributarioBundle } from "@/lib/api";
import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";
import {
  SEVERITY,
  TRIGGER_TITLE,
  renderTriggerBody,
} from "./CascataFiscalCard.triggers";

/** Sprint A16 L2 P5 (ADR-236 §D5) — Card "Tributário PJ — Cascata Fiscal".
 *
 * Substitui o uso anterior de `<NarrativeChartCard chartId="impostos_pj"/>`
 * em `S8PrevidenciaSection`. Renderiza a cascata calculada por
 * `pipeline/domain/services/tributario/cascata_calculator.py` (P3) +
 * adapter (P4), exposta no E5 output como `data.tributario`.
 *
 * Estados:
 *   - Cascata completa (Simples Anexo III/V, Lucro Presumido, MEI).
 *   - Empty state "perfil tributário pendente" (regime/anexo ausente).
 *   - Empty state "Lucro Real" (regime fora do escopo V1; cascata V2).
 *   - Bloco PGBL com flag para `declaracao_simplificada` + estado neutro
 *     para `renda_tributavel_pf_zerada`.
 *   - 0-5 decision triggers (T1-T5) como callouts severity-tipados.
 *
 * Co-design product-designer + financial-planner (2026-05-21):
 *   - Steps verticais (`<dl>`) > waterfall — densidade do card.
 *   - Carga total como linha final da cascata (não KPI hero).
 *   - Triggers com cor + ícone redundante (daltonismo).
 *   - Copy CRC: "Trade-off observado" / "Sinal de atenção" / "Oportunidade".
 *   - Frase de proteção sob header (blinda card inteiro contra
 *     interpretação como conselho).
 */

interface CascataFiscalCardProps {
  tributario: TributarioBundle | undefined;
}

const HEADER_TITLE = "Tributário PJ · Cascata Fiscal";

const PROTECTION_SENTENCE =
  "Esta cascata descreve sua situação atual, não recomenda mudança. " +
  "Decisões de regime, anexo ou estrutura societária são do seu contador.";

const PREMISSAS_SENTENCE =
  "Base: receita bruta 12 meses móveis · fator-R 12 meses móveis · valores anuais salvo indicação.";

const DISCLAIMER_SENTENCE =
  "Valores estimados a partir de movimentações reconhecidas e IRPF processado. " +
  "Confirme com seu contador antes de qualquer decisão tributária.";

export function CascataFiscalCard({ tributario }: CascataFiscalCardProps) {
  const cascata = tributario?.cascata;
  if (!tributario || !cascata || cascata.motivo_nao_suportado === "perfil_incompleto") {
    return <PerfilPendenteState />;
  }
  if (cascata.regime_nao_suportado && cascata.motivo_nao_suportado === "lucro_real") {
    return <LucroRealState />;
  }
  if (cascata.motivo_nao_suportado === "anexo_simples_pendente") {
    return <AnexoPendenteState />;
  }
  return <CascataFullCard tributario={tributario} cascata={cascata} />;
}

function CascataFullCard({
  tributario,
  cascata,
}: {
  tributario: TributarioBundle;
  cascata: CascataPayload;
}) {
  return (
    <ReportCard
      variant="feature"
      size="full"
      title={HEADER_TITLE}
      headerRight={<RegimeSubheader cascata={cascata} />}
    >
      <section
        role="region"
        aria-labelledby="cascata-fiscal-title"
        aria-describedby="cascata-fiscal-disclaimer"
        className="space-y-6"
      >
        <h4 id="cascata-fiscal-title" className="sr-only">
          {HEADER_TITLE} — {cascata.regime_label}
        </h4>
        <ProtectionAndPremises />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
          <CascataLayers cascata={cascata} />
          <PgblBlock cascata={cascata} />
        </div>
        <TriggersList triggers={cascata.triggers} />
        <FiduciaryDisclaimer temContador={Boolean(tributario.contador_nome)} />
      </section>
    </ReportCard>
  );
}

/** A40.l4 (ADR-319): o nome do contador é PII de terceiro — e com frequência
 * pessoa física. O disclaimer precisa dizer que há contador no perfil, não
 * quem ele é; o relatório é o artefato que a família mostra a terceiros. */
function FiduciaryDisclaimer({ temContador }: { temContador: boolean }) {
  return (
    <p
      id="cascata-fiscal-disclaimer"
      className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]"
    >
      {DISCLAIMER_SENTENCE}
      {temContador ? " Há contador cadastrado no perfil da PJ." : ""}
    </p>
  );
}

/* ─── Header subtitle (regime + fator-R badge) ─────────────────────── */

function RegimeSubheader({ cascata }: { cascata: CascataPayload }) {
  const showFatorR =
    cascata.regime === "simples" &&
    cascata.fator_r_pct !== null &&
    cascata.fator_r_faixa !== null;

  return (
    <div className="flex flex-wrap items-center justify-end gap-2 text-right">
      <span className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {cascata.regime_label}
      </span>
      {showFatorR && cascata.fator_r_pct !== null && cascata.fator_r_faixa !== null && (
        <FatorRBadge
          pct={cascata.fator_r_pct}
          faixa={cascata.fator_r_faixa}
        />
      )}
    </div>
  );
}

function FatorRBadge({
  pct,
  faixa,
}: {
  pct: number;
  faixa: "anexo_iii" | "anexo_v";
}) {
  const isAnexoIII = faixa === "anexo_iii";
  const className = isAnexoIII
    ? "bg-[color-mix(in_srgb,var(--semantic-gain)_15%,transparent)] text-[var(--semantic-gain)]"
    : "bg-[color-mix(in_srgb,var(--semantic-warning)_15%,transparent)] text-[var(--semantic-warning)]";
  const label = isAnexoIII ? "Anexo III" : "Anexo V";
  const pctTxt = (pct * 100).toFixed(1).replace(".", ",");
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase ${className}`}
      aria-label={`Fator-R móvel 12 meses ${pctTxt} por cento — ${label}`}
    >
      Fator-R {pctTxt}% · {label}
    </span>
  );
}

/* ─── Protection + premises micro-copy ─────────────────────────────── */

function ProtectionAndPremises() {
  return (
    <div className="space-y-1.5">
      <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
        <strong>Não é recomendação:</strong> {PROTECTION_SENTENCE}
      </p>
      <p className="text-[0.7rem] uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {PREMISSAS_SENTENCE}
      </p>
    </div>
  );
}

/* ─── Cascata layers (steps verticais) ─────────────────────────────── */

function CascataLayers({ cascata }: { cascata: CascataPayload }) {
  return (
    <div className="border-l-2 border-[var(--surface-border)] pl-4">
      <LayersList cascata={cascata} />
      <CargaTotalRow cargaPct={cascata.carga_total_pct} />
    </div>
  );
}

function LayersList({ cascata }: { cascata: CascataPayload }) {
  const tributosLabel = labelTributosFederais(cascata.regime);
  const tributosPct = pctOfReceita(cascata.tributos_federais, cascata.receita_bruta);
  return (
    <dl className="space-y-2 text-sm">
      <Layer label="Receita bruta PJ (12m)" value={cascata.receita_bruta} />
      <Layer
        label={`− ${tributosLabel}`}
        value={cascata.tributos_federais}
        subtle={tributosPct ? `${tributosPct} efetivo` : undefined}
      />
      {cascata.iss_total > 0 && (
        <Layer label="− ISS destacado" value={cascata.iss_total} />
      )}
      <Layer label="= Lucro contábil PJ" value={cascata.lucro_contabil_pj} strong />
      <Layer label="− Pró-labore bruto" value={cascata.pro_labore_bruto} />
      {cascata.inss_patronal > 0 && (
        <Layer label="− INSS patronal (20%)" value={cascata.inss_patronal} />
      )}
      <Layer
        label="− INSS empregado + IRRF"
        value={cascata.inss_empregado + cascata.irrf_pro_labore}
      />
      <Layer
        label="= Lucros distribuídos (isentos)"
        value={cascata.lucros_distribuidos}
        strong
      />
    </dl>
  );
}

function CargaTotalRow({ cargaPct }: { cargaPct: number }) {
  const pct = (cargaPct * 100).toFixed(1).replace(".", ",");
  return (
    <div
      className="mt-3 flex items-baseline justify-between gap-2 border-t-2 border-[var(--surface-border)] pt-3"
      aria-label={`Carga tributária total estimada em ${pct} por cento da receita`}
    >
      <span className="text-sm font-display font-semibold text-[var(--surface-foreground)]">
        Carga tributária total
      </span>
      <span className="font-mono text-base font-semibold tabular-nums text-[var(--brand-primary)]">
        {pct}%
      </span>
    </div>
  );
}

function Layer({
  label,
  value,
  subtle,
  strong,
}: {
  label: string;
  value: number;
  subtle?: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className={strong ? "font-semibold text-[var(--surface-foreground)]" : "text-[var(--surface-muted-foreground)]"}>
        {label}
      </dt>
      <dd className={strong ? "font-semibold" : ""}>
        <MonetaryValue value={value} fractionDigits={0} />
        {subtle && (
          <span className="ml-2 text-xs text-[var(--surface-muted-foreground)]">({subtle})</span>
        )}
      </dd>
    </div>
  );
}

function labelTributosFederais(regime: CascataPayload["regime"]): string {
  if (regime === "simples") return "DAS Simples Nacional";
  if (regime === "lucro_presumido") return "PIS + COFINS + IRPJ + CSLL";
  if (regime === "mei") return "DAS-MEI (R$ 79,90/mês)";
  return "Tributos federais";
}

function pctOfReceita(parte: number, receita: number): string | null {
  if (!receita || receita <= 0) return null;
  return `${((parte / receita) * 100).toFixed(1).replace(".", ",")}%`;
}

/* ─── PGBL block ───────────────────────────────────────────────────── */

function PgblBlock({ cascata }: { cascata: CascataPayload }) {
  return (
    <section
      aria-labelledby="cascata-pgbl-title"
      className="space-y-3 rounded-md bg-[var(--surface-muted)] p-4"
    >
      <h4
        id="cascata-pgbl-title"
        className="font-display text-sm font-semibold text-[var(--surface-foreground)]"
      >
        Base para dedução PGBL
      </h4>
      <dl className="space-y-2 text-sm">
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[var(--surface-muted-foreground)]">Renda tributável PF/ano</dt>
          <dd>
            <MonetaryValue value={cascata.pgbl_base_anual} fractionDigits={0} />
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[var(--surface-muted-foreground)]">Limite PGBL (12%)</dt>
          <dd>
            <MonetaryValue value={cascata.pgbl_limite_anual} fractionDigits={0} />
          </dd>
        </div>
      </dl>
      <p className="text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
        Base = pró-labore + outras rendas tributáveis IRPF. Lucros distribuídos
        não entram na base PGBL.
      </p>
      <PgblStatus
        aplicavel={cascata.pgbl_aplicavel}
        motivo={cascata.pgbl_motivo_inaplicavel}
      />
      <p
        className="text-[0.7rem] italic leading-relaxed text-[var(--surface-muted-foreground)]"
        data-testid="pgbl-disclaimer-crc"
      >
        Cálculo informativo de capacidade dedutível. Para decisão de aporte em
        PGBL, considere conversar com seu contador — Mathoms consolida, não
        substitui orientação tributária.
      </p>
    </section>
  );
}

function PgblStatus({
  aplicavel,
  motivo,
}: {
  aplicavel: boolean;
  motivo: CascataPayload["pgbl_motivo_inaplicavel"];
}) {
  if (aplicavel) return null;
  if (motivo === "declaracao_simplificada") return <SimplificadaFlag />;
  if (motivo === "renda_tributavel_pf_zerada") return <RendaPfZeradaNotice />;
  return null;
}

function SimplificadaFlag() {
  return (
    <div
      role="note"
      className="flex items-start gap-2 rounded-md border-l-4 border-[var(--semantic-warning)] bg-[color-mix(in_srgb,var(--semantic-warning)_10%,transparent)] p-3 text-xs leading-relaxed"
    >
      <AlertTriangle
        className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-warning)]"
        aria-hidden="true"
      />
      <p>
        PGBL não dedutível — você escolheu desconto simplificado no IRPF.
        Migrar para declaração completa é decisão anual e depende de
        comparação caso-a-caso.
      </p>
    </div>
  );
}

function RendaPfZeradaNotice() {
  return (
    <p className="rounded-md border-l-4 border-[var(--surface-border)] bg-[var(--surface-card)] p-3 text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
      Renda tributável PF não detectada — processar o IRPF mais recente
      libera o cálculo da base PGBL.
    </p>
  );
}

/* ─── Decision triggers (callouts) ─────────────────────────────────── */

function TriggersList({ triggers }: { triggers: CascataTrigger[] }) {
  if (triggers.length === 0) return null;
  return (
    <section
      aria-labelledby="cascata-triggers-title"
      className="space-y-3"
    >
      <h4
        id="cascata-triggers-title"
        className="font-display text-sm font-semibold text-[var(--surface-foreground)]"
      >
        Pontos de atenção
      </h4>
      <ul className="space-y-3" aria-label="Pontos de atenção tributária">
        {triggers.map((t) => (
          <li key={t.code}>
            <TriggerCallout trigger={t} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TriggerCallout({ trigger }: { trigger: CascataTrigger }) {
  const style = SEVERITY[trigger.severity];
  const title = TRIGGER_TITLE[trigger.code] ?? trigger.title;
  const body = renderTriggerBody(trigger);
  return (
    <div
      className={`flex items-start gap-2 rounded-md border-l-4 ${style.borderClass} bg-[var(--surface-card)] p-3`}
      aria-label={`${style.ariaSeverity}: ${title}`}
    >
      <style.Icon
        className={`mt-0.5 h-4 w-4 shrink-0 ${style.iconClass}`}
        aria-hidden="true"
      />
      <div className="flex-1 space-y-1">
        <p className="text-sm font-semibold text-[var(--surface-foreground)]">
          {title}
        </p>
        <p className="text-xs leading-relaxed text-[var(--surface-foreground)]">
          {body}
        </p>
      </div>
    </div>
  );
}

/* ─── Empty / unsupported states ───────────────────────────────────── */

function EmptyStateBadge({ label }: { label: string }) {
  return (
    <span className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
      {label}
    </span>
  );
}

function EmptyStateBody({
  ariaLabel,
  title,
  body,
  hint,
}: {
  ariaLabel: string;
  title: string;
  body: string;
  hint?: string;
}) {
  return (
    <section role="region" aria-label={ariaLabel} className="space-y-3">
      <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
        <strong>{title}</strong> {body}
      </p>
      {hint && (
        <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
          {hint}
        </p>
      )}
    </section>
  );
}

function PerfilPendenteState() {
  return (
    <ReportCard variant="neutral" size="full" title={HEADER_TITLE}>
      <EmptyStateBody
        ariaLabel="Perfil tributário PJ incompleto"
        title="Perfil tributário PJ incompleto."
        body="A cascata fiscal ficará disponível quando seu consultor preencher regime, anexo Simples, CNAE e modelo de declaração IRPF no perfil do workspace."
        hint="Solicite ao seu consultor a complementação do perfil para receber a análise completa."
      />
    </ReportCard>
  );
}

function LucroRealState() {
  return (
    <ReportCard
      variant="neutral"
      size="full"
      title={HEADER_TITLE}
      headerRight={<EmptyStateBadge label="Lucro Real" />}
    >
      <EmptyStateBody
        ariaLabel="Regime Lucro Real — cascata em desenvolvimento"
        title="Regime Lucro Real — cascata em desenvolvimento (V2)."
        body="Lucro Real exige escrituração contábil completa (LALUR, depreciações, ajustes IRPJ) fora do escopo desta versão da cascata."
        hint="Trabalhe com seu contador para os números detalhados."
      />
    </ReportCard>
  );
}

function AnexoPendenteState() {
  return (
    <ReportCard
      variant="neutral"
      size="full"
      title={HEADER_TITLE}
      headerRight={<EmptyStateBadge label="Simples Nacional" />}
    >
      <EmptyStateBody
        ariaLabel="Anexo Simples pendente"
        title="Anexo Simples pendente."
        body="O regime está marcado como Simples Nacional, mas o anexo (III ou V) ainda não foi informado. O anexo depende do CNAE e do fator-R; peça ao seu consultor a complementação."
      />
    </ReportCard>
  );
}
