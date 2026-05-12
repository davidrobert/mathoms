import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { PgblCardMode } from "@/lib/irpf/pgbl-card-strategy";

export interface PrevidenciaPgblData {
  status?: string;
  nota?: string;
  renda_tributavel_anual?: number;
  limite_pgbl_anual?: number;
  aporte_mensal?: number;
  aliquota_marginal?: number;
  economia_ir_anual?: number;
}

interface PrevidenciaPgblCardProps {
  previdencia: PrevidenciaPgblData | undefined;
  /** ADR-196 §D2 — modo resolvido por `getPgblCardStrategy`. Default
   * `"default"` preserva comportamento legacy. */
  mode?: PgblCardMode;
  /** ADR-196 §D2 — ano-base do IRPF authoritativo/defasado, usado nos
   * modos `informative-*` e `default-defasado` para interpolar copy. */
  anoBase?: number;
}

const DISCLAIMER = (
  <>
    <strong>Não é recomendação:</strong> valor estimado sobre receita PJ;
    benefício fiscal real depende de regime tributário declarado, alíquota
    efetiva, horizonte de resgate, taxa de administração e contribuição ao
    INSS.
  </>
);

const CROSS_LINK_CLASS =
  "underline decoration-dotted underline-offset-2 text-[var(--brand-info)] hover:opacity-80";

function CrossLink() {
  return (
    <a href="#S_IRPF_OTIMIZACAO" className={CROSS_LINK_CLASS}>
      Otimização Tributária
    </a>
  );
}

function NotApplicable() {
  return (
    <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-[var(--surface-muted-foreground)]">
      <span aria-label="Métrica não aplicável">—</span>
    </p>
  );
}

/** F9 · F2.E · S7 — Card "Previdência PGBL".
 *
 * ADR-196 (Proposto · A12) — 6 modos. `default*` mantém grid de 4 KPIs
 * + disclaimer "Não é recomendação"; `informative-*` degrada para
 * parágrafo factual com cross-link para Card B em S_IRPF_OTIMIZACAO,
 * suprimindo "aporte sugerido" e "economia IR" (prescrições que entram
 * em conflito com IRPF authoritativo).
 */
export function PrevidenciaPgblCard({
  previdencia,
  mode = "default",
  anoBase,
}: PrevidenciaPgblCardProps) {
  if (!previdencia || previdencia.status === "Não aplicável") {
    return (
      <ReportCard variant="feature" title="Previdência PGBL">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          PGBL não aplicável para este perfil tributário.
        </p>
      </ReportCard>
    );
  }

  if (mode === "informative-capacidade") {
    return <InformativeCapacidade previdencia={previdencia} anoBase={anoBase} />;
  }
  if (mode === "informative-simplificado") {
    return <InformativeSimplificado previdencia={previdencia} anoBase={anoBase} />;
  }
  if (mode === "informative-no-teto") {
    return <InformativeNoTeto previdencia={previdencia} anoBase={anoBase} />;
  }
  if (mode === "informative-sem-renda") {
    return <InformativeSemRenda previdencia={previdencia} anoBase={anoBase} />;
  }

  return (
    <DefaultPrevidenciaCard
      previdencia={previdencia}
      defasado={mode === "default-defasado"}
      anoBase={anoBase}
    />
  );
}

function KpiCell({ label, value, tone }: { label: string; value: number | undefined; tone?: string }) {
  return (
    <div>
      <dt className="text-[var(--surface-muted-foreground)]">{label}</dt>
      <dd className={`mt-1 font-semibold${tone ? " " + tone : ""}`}>
        <MonetaryValue value={value} />
      </dd>
    </div>
  );
}

function PrevidenciaKpiGrid({ previdencia }: { previdencia: PrevidenciaPgblData }) {
  return (
    <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
      <KpiCell label="Renda tributável/ano" value={previdencia.renda_tributavel_anual} />
      <KpiCell label="Limite PGBL/ano (12%)" value={previdencia.limite_pgbl_anual} />
      <KpiCell label="Aporte sugerido/mês" value={previdencia.aporte_mensal} />
      {previdencia.economia_ir_anual !== undefined && (
        <KpiCell
          label="Economia de IR/ano"
          value={previdencia.economia_ir_anual}
          tone="text-[var(--semantic-gain)]"
        />
      )}
    </dl>
  );
}

function DefaultPrevidenciaCard({
  previdencia,
  defasado,
  anoBase,
}: {
  previdencia: PrevidenciaPgblData;
  defasado: boolean;
  anoBase: number | undefined;
}) {
  return (
    <ReportCard variant="feature" title="Previdência PGBL">
      <div className="space-y-4">
        {defasado && anoBase !== undefined && (
          <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            Última declaração: {anoBase} · defasada · reveja após próxima
            entrega IRPF
          </p>
        )}
        <PrevidenciaKpiGrid previdencia={previdencia} />
        {previdencia.nota && (
          <p className="rounded-md bg-[var(--surface-muted)] p-3 text-xs text-[var(--surface-muted-foreground)]">
            {previdencia.nota}
          </p>
        )}
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          {DISCLAIMER}
        </p>
      </div>
    </ReportCard>
  );
}

function InformativeSubtitle() {
  return (
    <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
      Estimativa sobre receita PJ — informativo · veja capacidade declarada
      em <CrossLink />
    </p>
  );
}

function InformativeCapacidade({
  previdencia,
  anoBase,
}: {
  previdencia: PrevidenciaPgblData;
  anoBase: number | undefined;
}) {
  return (
    <ReportCard variant="neutral" size="half" title="Previdência PGBL">
      <div className="space-y-3">
        <InformativeSubtitle />
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          Capacidade dedutível autoritativa está em <CrossLink /> (baseada
          no IRPF {anoBase ?? "—"} declarado). Esta seção mostra apenas a
          estimativa sobre receita PJ anualizada deste período (
          <strong>
            <MonetaryValue value={previdencia.limite_pgbl_anual} />
          </strong>
          /ano), útil para projetar próximo ano-base.
        </p>
      </div>
    </ReportCard>
  );
}

function InformativeSimplificado({
  previdencia,
  anoBase,
}: {
  previdencia: PrevidenciaPgblData;
  anoBase: number | undefined;
}) {
  return (
    <ReportCard variant="neutral" size="half" title="Previdência PGBL">
      <div className="space-y-3">
        <InformativeSubtitle />
        <NotApplicable />
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          Sua declaração de {anoBase ?? "—"} é pelo modelo simplificado, que
          não permite dedução de PGBL. O potencial estimado sobre sua
          receita PJ anualizada (
          <strong>
            <MonetaryValue value={previdencia.renda_tributavel_anual} />
          </strong>
          ) seria de até{" "}
          <strong>
            <MonetaryValue value={previdencia.limite_pgbl_anual} />
          </strong>
          /ano <em>caso houvesse migração para o modelo completo</em> —
          decisão que depende de comparação anual com o desconto
          simplificado da Receita.
        </p>
      </div>
    </ReportCard>
  );
}

function InformativeNoTeto({
  previdencia,
  anoBase,
}: {
  previdencia: PrevidenciaPgblData;
  anoBase: number | undefined;
}) {
  return (
    <ReportCard variant="neutral" size="half" title="Previdência PGBL">
      <div className="space-y-3">
        <InformativeSubtitle />
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          Em {anoBase ?? "—"} você esgotou os dedutíveis (12% da renda
          tributável declarada — veja <CrossLink />). Capacidade adicional
          só no próximo ano-base. Estimativa sobre receita PJ anualizada
          deste período:{" "}
          <strong>
            <MonetaryValue value={previdencia.limite_pgbl_anual} />
          </strong>
          .
        </p>
      </div>
    </ReportCard>
  );
}

function InformativeSemRenda({
  previdencia,
  anoBase,
}: {
  previdencia: PrevidenciaPgblData;
  anoBase: number | undefined;
}) {
  return (
    <ReportCard variant="neutral" size="half" title="Previdência PGBL">
      <div className="space-y-3">
        <InformativeSubtitle />
        <NotApplicable />
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          Sua declaração de {anoBase ?? "—"} registrou apenas rendimentos
          isentos ou de tributação exclusiva — PGBL deduz da base
          tributável e não se aplica nesse cenário. A receita PJ
          identificada no fluxo deste período (
          <strong>
            <MonetaryValue value={previdencia.renda_tributavel_anual} />
          </strong>
          ) só geraria espaço dedutível se classificada como tributável no
          próximo IRPF (<CrossLink />).
        </p>
      </div>
    </ReportCard>
  );
}
