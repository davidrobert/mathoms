"use client";

// ADR-223 — Banner contextual "imoveis no IF" (FU-1 UX, sprint A13 deferred → entrega antecipada).
//
// Aparece em MembersTab quando workspace tem ≥1 imóvel classificado como
// locado/comercial E user ainda não fez signal afirmativo (set_at IS NULL).
// Copy alinhado a financial-planner: TRS ~3% real/ano como threshold;
// CTAs invertidos por treatment: workspaces NOVOS default false ("Manter
// fora" = primary); workspaces EXISTENTES com herança true recebem variant
// "educational" com "Manter incluindo" = primary.

import { useCallback, useEffect, useState } from "react";

import { listProperties, setImoveisNoIf, type PropertyListResponse } from "@/lib/api/properties";

export type ImoveisNoIfBannerVariant = "new" | "educational";

interface Props {
  workspaceId: string;
  qualifiedCount: number;
  currentValue: boolean;
  variant: ImoveisNoIfBannerVariant;
  onResolved: (newValue: boolean) => void;
  onDismiss?: () => void;
}

const COPY: Record<ImoveisNoIfBannerVariant, { title: string; body: (n: number) => string }> = {
  new: {
    title: "Contar seus imóveis alugados no cálculo de Independência Financeira?",
    body: (n) =>
      `Você marcou ${n} imóvel${n > 1 ? "is" : ""} como investimento. Por padrão, deixamos fora do seu Patrimônio Investido — só faz sentido incluir se o aluguel líquido rende mais que ~3% real ao ano (Taxa de Retorno Segura).`,
  },
  educational: {
    title: "Confirmar como seus imóveis alugados são contabilizados",
    body: (n) =>
      `Atualmente, seus ${n} imóveis investimento entram no cálculo do seu Patrimônio Investido. Quer manter assim, ou tirá-los? Por padrão hoje recomendamos deixar fora — só inclui se o aluguel líquido rende mais que ~3% real ao ano.`,
  },
};


export function ImoveisNoIfBanner({
  workspaceId,
  qualifiedCount,
  currentValue,
  variant,
  onResolved,
  onDismiss,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const copy = COPY[variant];

  const apply = async (value: boolean) => {
    setSubmitting(true);
    setError("");
    try {
      await setImoveisNoIf(workspaceId, value);
      onResolved(value);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar");
      setSubmitting(false);
    }
  };

  // CTA primary "manter fora" no variant 'new' (default conservador é fora) e
  // "manter incluindo" no variant 'educational' (preserva estado atual true).
  const primaryLabel = variant === "new" ? "Manter fora" : "Manter incluindo";
  const primaryValue = variant === "new" ? false : true;
  const secondaryLabel = variant === "new" ? "Incluir no cálculo" : "Tirar do cálculo";
  const secondaryValue = !primaryValue;

  return (
    <section
      role="region"
      aria-labelledby="imoveis-no-if-banner-title"
      className="rounded-md border-l-4 border-[var(--brand-accent)] bg-[var(--surface-card)] p-4"
    >
      <h3
        id="imoveis-no-if-banner-title"
        className="font-display text-base font-semibold text-[var(--surface-foreground)]"
      >
        <span aria-hidden="true" className="mr-1 text-[var(--brand-accent)]">ⓘ</span>
        {copy.title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
        {copy.body(qualifiedCount)}
      </p>
      {error && (
        <p className="mt-2 text-xs text-[var(--semantic-danger)]" role="alert">
          {error}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded bg-[var(--brand-primary)] px-3 py-1.5 text-sm font-medium text-[var(--brand-primary-foreground)] hover:opacity-90 disabled:opacity-50"
          onClick={() => apply(primaryValue)}
          disabled={submitting || currentValue === primaryValue}
          aria-label={primaryLabel}
        >
          {submitting ? "Salvando…" : primaryLabel}
        </button>
        <button
          type="button"
          className="rounded border border-[var(--surface-border)] px-3 py-1.5 text-sm hover:bg-[var(--surface-muted)] disabled:opacity-50"
          onClick={() => apply(secondaryValue)}
          disabled={submitting || currentValue === secondaryValue}
          aria-label={secondaryLabel}
        >
          {secondaryLabel}
        </button>
        {onDismiss && (
          <button
            type="button"
            className="text-sm text-[var(--surface-muted-foreground)] underline-offset-2 hover:underline disabled:opacity-50"
            onClick={onDismiss}
            disabled={submitting}
          >
            Decidir depois
          </button>
        )}
      </div>
    </section>
  );
}

const QUALIFYING = new Set(["locado", "comercial"]);
const DISMISS_KEY_PREFIX = "imoveis_no_if_banner_dismissed:";


function shouldShow(data: PropertyListResponse | null, dismissed: boolean): boolean {
  if (!data || dismissed) return false;
  if (data.imoveis_no_if_set_at !== null) return false;
  const qualified = data.properties.filter(
    (p) => p.classification !== null && QUALIFYING.has(p.classification),
  );
  return qualified.length > 0;
}


export function ImoveisNoIfBannerContainer({ workspaceId }: { workspaceId: string }) {
  const [data, setData] = useState<PropertyListResponse | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const reload = useCallback(async () => {
    try {
      const resp = await listProperties(workspaceId);
      setData(resp);
    } catch {
      // silent fail — banner é opcional, não crítico
    }
  }, [workspaceId]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setDismissed(localStorage.getItem(DISMISS_KEY_PREFIX + workspaceId) === "1");
    }
    void reload();
  }, [workspaceId, reload]);

  if (!shouldShow(data, dismissed)) return null;
  if (!data) return null;

  const qualifiedCount = data.properties.filter(
    (p) => p.classification !== null && QUALIFYING.has(p.classification),
  ).length;
  const variant: ImoveisNoIfBannerVariant = data.imoveis_no_if ? "educational" : "new";

  return (
    <ImoveisNoIfBanner
      workspaceId={workspaceId}
      qualifiedCount={qualifiedCount}
      currentValue={data.imoveis_no_if}
      variant={variant}
      onResolved={() => void reload()}
      onDismiss={() => {
        if (typeof window !== "undefined") {
          localStorage.setItem(DISMISS_KEY_PREFIX + workspaceId, "1");
        }
        setDismissed(true);
      }}
    />
  );
}
