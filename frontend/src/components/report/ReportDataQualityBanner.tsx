"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, ShieldCheck } from "lucide-react";

import type { ReportAnalysisData } from "@/lib/api";
import {
  mayAssertCleanQuality,
  type ReportRunOutcome,
} from "@/lib/api/reports";
import { MonetaryValue } from "./MonetaryValue";
import { Alert } from "./ui/Alert";
import { useNeedsReviewCount } from "./hooks/useNeedsReviewCount";
import {
  computeDataQualitySignals,
  type NaoIdentificadoShare,
  type PremissasDegrade,
  type ReportDataQualitySignals,
} from "./utils/dataQualitySignals";

/** A28.l9 — banner agregado de qualidade de dados (KR4 · honestidade).
 *
 * Renderizado entre o Sumário Executivo e a primeira seção. Consolida os
 * sinais de degradação que ficavam escondidos em cards individuais, cada
 * linha com CTA de resolução ("erros resolvem" — COPY_GUIDELINES). Sem
 * sinais, colapsa para barra fina — zero ruído em relatório saudável.
 *
 * Este banner NÃO maquia dado contraditório: se duas seções discordam, o
 * fix é a montante (Onda 0 do Sprint A28).
 */
export function ReportDataQualityBanner({
  data,
  workspaceId,
  runOutcome,
}: {
  data: ReportAnalysisData;
  workspaceId: string;
  runOutcome: ReportRunOutcome;
}) {
  const needsReviewDocs = useNeedsReviewCount(workspaceId);
  const signals = computeDataQualitySignals(data, needsReviewDocs);

  // A40.l18 · ADR-357 — a ordem dos guards importa. `runOutcome` NÃO entra em
  // `computeDataQualitySignals`: se entrasse no `count`, o `SignalsAlert`
  // renderizaria "1 pendência afeta a precisão" com uma <ul> VAZIA, porque as
  // linhas são condicionais em sinais específicos. Aqui o desfecho gateia
  // apenas a AFIRMAÇÃO positiva; o alerta com sinais reais continua honesto
  // (incompleto ≠ falso).
  //
  // A ressalva positiva ("o que faltou") é da A40.l22 — este PR só cala a
  // afirmação falsa, e o slot fica livre para a linha que ela vai escrever.
  if (signals.count > 0) return <SignalsAlert signals={signals} />;
  if (!mayAssertCleanQuality(runOutcome)) return null;
  return <CleanBar />;
}

function CleanBar() {
  return (
    <div
      role="status"
      aria-label="Qualidade dos dados: sem pendências"
      data-testid="data-quality-clean"
      className="mb-6 flex items-center gap-2 rounded-md border border-[var(--surface-border)] px-3 py-1.5 text-xs text-[var(--surface-muted-foreground)]"
    >
      <ShieldCheck
        className="h-3.5 w-3.5 shrink-0 text-[var(--semantic-gain)]"
        aria-hidden="true"
      />
      <span>
        Qualidade dos dados: sem pendências que afetem a leitura deste
        relatório.
      </span>
    </div>
  );
}

function SignalsAlert({ signals }: { signals: ReportDataQualitySignals }) {
  const n = signals.count;
  return (
    <div className="mb-6" data-testid="data-quality-banner">
      <Alert
        severity="warning"
        icon={<AlertTriangle className="h-4 w-4" aria-hidden="true" />}
      >
        <p className="font-medium">
          Qualidade dos dados — {n}{" "}
          {n === 1 ? "pendência afeta" : "pendências afetam"} a precisão deste
          relatório.
        </p>
        <ul
          aria-label="Pendências de qualidade de dados"
          className="mt-2 space-y-1.5 text-sm"
        >
          {signals.naoIdentificado && (
            <NaoIdentificadoRow share={signals.naoIdentificado} />
          )}
          {signals.needsReviewDocs > 0 && (
            <NeedsReviewRow count={signals.needsReviewDocs} />
          )}
          {signals.premissas && <PremissasRow degrade={signals.premissas} />}
          {signals.imoveisPendentes > 0 && (
            <ImoveisPendentesRow count={signals.imoveisPendentes} />
          )}
        </ul>
      </Alert>
    </div>
  );
}

function NaoIdentificadoRow({ share }: { share: NaoIdentificadoShare }) {
  return (
    <SignalRow
      cta={{
        href: "/transactions?category=nao_identificado&sort=valor_desc",
        label: "Reclassificar transações",
      }}
    >
      <MonetaryValue value={share.valor} compact /> em despesas sem categoria (
      {share.pct.toFixed(1).replace(".", ",")}% do total) — reclassificar
      devolve precisão ao fluxo de caixa.
    </SignalRow>
  );
}

function NeedsReviewRow({ count }: { count: number }) {
  return (
    <SignalRow
      cta={{
        href: "/documents?filter=needs_review",
        label: "Revisar documentos",
      }}
    >
      {count}{" "}
      {count === 1
        ? "documento aguarda revisão"
        : "documentos aguardam revisão"}{" "}
      de classificação — dados deles podem estar fora desta análise.
    </SignalRow>
  );
}

function PremissasRow({ degrade }: { degrade: PremissasDegrade }) {
  return (
    <SignalRow cta={{ href: "#APP_B", label: "Ver premissas adotadas" }}>
      Premissas de mercado em fallback
      {degrade.classesTotal > 0 && (
        <>
          {" "}
          ({degrade.classesIndisponiveis}/{degrade.classesTotal} classes sem
          premissa vigente)
        </>
      )}{" "}
      — projeções usam valores padrão, não calibrados à sua carteira.
    </SignalRow>
  );
}

function ImoveisPendentesRow({ count }: { count: number }) {
  return (
    <SignalRow
      cta={{
        href: "/config?tab=members",
        label: "Classificar em Configurações",
      }}
    >
      {count}{" "}
      {count === 1
        ? "imóvel sem classificação está"
        : "imóveis sem classificação estão"}{" "}
      fora do módulo de rentabilidade imobiliária.
    </SignalRow>
  );
}

function SignalRow({
  children,
  cta,
}: {
  children: ReactNode;
  cta: { href: string; label: string };
}) {
  const isAnchor = cta.href.startsWith("#");
  const ctaStyle = {
    color: "var(--brand-primary)",
    textDecoration: "underline",
  } as const;
  return (
    <li className="flex flex-wrap items-baseline gap-x-2">
      <span>{children}</span>
      {isAnchor ? (
        <a
          href={cta.href}
          style={ctaStyle}
          className="whitespace-nowrap font-medium"
        >
          {cta.label}
        </a>
      ) : (
        <Link
          href={cta.href}
          style={ctaStyle}
          className="whitespace-nowrap font-medium"
        >
          {cta.label}
        </Link>
      )}
    </li>
  );
}
