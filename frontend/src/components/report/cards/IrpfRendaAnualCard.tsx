import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import { type CompletudeAno, type IrpfKpis, parseDecimalString } from "@/types/irpf";

interface IrpfRendaAnualCardProps {
  kpis: IrpfKpis;
  variant?: CardVariant;
}

/** ADR-157 · ADR-266 · S_IRPF_RENDA — Renda anual familiar com completude tri-state. */
export function IrpfRendaAnualCard({ kpis, variant = "feature" }: IrpfRendaAnualCardProps) {
  const display = pickDisplayYear(kpis);
  return (
    <ReportCard
      variant={variant}
      size="half"
      title="Renda Anual Familiar"
      headerRight={
        display.completude !== "completo" ? <CompletudeBadge state={display.completude} /> : null
      }
    >
      <RendaBody kpis={kpis} display={display} />
    </ReportCard>
  );
}

type DisplayState = {
  ano: number;
  completude: CompletudeAno;
  motivo: string | null;
};

function pickDisplayYear(kpis: IrpfKpis): DisplayState {
  // Backend (ADR-266) opina via ano_base_default + completude. Workspaces
  // pre-A16 não emitem esses campos — fallback assume completo no ano_base.
  const ano = kpis.ano_base_default ?? kpis.ano_base;
  const completude: CompletudeAno = kpis.ano_base_completude ?? "completo";
  const motivo = kpis.completude_motivo ?? null;
  return { ano, completude, motivo };
}

function RendaBody({ kpis, display }: { kpis: IrpfKpis; display: DisplayState }) {
  const brutaForDisplay = brutaDoAno(kpis, display.ano);
  const liquida = parseDecimalString(kpis.renda_liquida_familiar_brl);
  const showCollapse =
    display.completude === "completo" &&
    brutaForDisplay !== null &&
    liquida !== null &&
    Math.abs(brutaForDisplay - liquida) < 0.005;
  if (showCollapse) return <RendaSingleLine ano={display.ano} valor={brutaForDisplay} />;
  if (display.completude === "completo") return <BrutaLiquidaRows kpis={kpis} ano={display.ano} />;
  return <IncompletoBanner kpis={kpis} display={display} />;
}

function brutaDoAno(kpis: IrpfKpis, ano: number): number | null {
  // ano_base_default pode apontar para ano histórico — busca em evolucao_renda_anos.
  if (ano === kpis.ano_base) return parseDecimalString(kpis.renda_anual_familiar_brl);
  const raw = kpis.evolucao_renda_anos[String(ano)];
  return raw ? parseDecimalString(raw) : null;
}

function BrutaLiquidaRows({ kpis, ano }: { kpis: IrpfKpis; ano: number }) {
  const bruta = brutaDoAno(kpis, ano);
  const liquida = parseDecimalString(kpis.renda_liquida_familiar_brl);
  return (
    <div className="space-y-4">
      <RendaRow label={`Bruta · ${ano}`} value={bruta} sizeClass="text-2xl" />
      <RendaRow
        label="Líquida (após IR, INSS e pensão)"
        value={liquida}
        sizeClass="text-xl text-[var(--semantic-gain)]"
      />
    </div>
  );
}

function RendaRow({
  label,
  value,
  sizeClass,
}: {
  label: string;
  value: number | null;
  sizeClass: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        {label}
      </p>
      <p className={`mt-1 font-mono ${sizeClass} font-semibold tabular-nums`}>
        <MonetaryValue value={value} />
      </p>
    </div>
  );
}

function RendaSingleLine({ ano, valor }: { ano: number; valor: number }) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
        Renda Familiar · {ano}
      </p>
      <p className="mt-1 font-mono text-3xl font-semibold tabular-nums">
        <MonetaryValue value={valor} />
      </p>
      <p className="text-xs text-[var(--surface-muted-foreground)]">
        Sem retenção de IR ou INSS no ano.
      </p>
    </div>
  );
}

function IncompletoBanner({
  kpis,
  display,
}: {
  kpis: IrpfKpis;
  display: DisplayState;
}) {
  // Fallback mostra o último ano completo (ano_base_default). Quando todos
  // anos disponíveis são incompletos/provisorios, ano_base_default ainda é o
  // melhor candidato (pick_default_year prefere completo > provisorio > incompleto).
  const bruta = brutaDoAno(kpis, display.ano);
  return (
    <div className="space-y-3">
      <RendaRow label={`Bruta · ${display.ano}`} value={bruta} sizeClass="text-2xl" />
      <p
        className="text-xs text-[var(--surface-muted-foreground)]"
        role="note"
        aria-live="polite"
      >
        {display.motivo ?? "Ano-base atual ainda em consolidação."}
      </p>
    </div>
  );
}

function CompletudeBadge({ state }: { state: CompletudeAno }) {
  const label =
    state === "provisorio" ? "Provisório · em entrega" : "Ano-base incompleto";
  return (
    <span
      className="inline-flex items-center rounded-full bg-[var(--report-alert-warning-bg)] px-2.5 py-0.5 text-xs font-medium text-[var(--report-alert-warning-text)]"
      role="status"
      aria-label={label}
    >
      {label}
    </span>
  );
}
