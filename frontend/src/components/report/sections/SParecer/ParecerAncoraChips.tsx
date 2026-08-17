// ADR-296 (A26.l9 / A40.l49) — citação determinística D2-puro: a prosa não traz
// R$; cada âncora vira um chip. `label` vem do finalize (mapa citation_labels);
// pareceres persistidos sem label caem no fallback root → ROTULO_LABEL.

import type { Ancora } from "@/lib/api";

const ROTULO_LABEL: Record<string, string> = {
  reserva_emergencia: "Reserva de emergência",
  endividamento: "Endividamento",
  passive_income: "Renda passiva",
  if_monte_carlo: "Independência financeira",
  patrimonio: "Patrimônio",
  fluxo_caixa: "Fluxo de caixa",
  investimentos: "Investimentos",
  previdencia_pgbl: "Análise PGBL",
  irpf_kpis: "Imposto de renda",
  cenarios_conjuge: "Cenário do casal",
  consumo_consciente: "Consumo",
  goals: "Metas",
};

function rotuloLabel(rotulo: string | null): string {
  if (!rotulo) return "Evidência";
  return ROTULO_LABEL[rotulo] ?? rotulo;
}

function chipLabel(ancora: Ancora): string {
  if (ancora.label) return ancora.label;
  return rotuloLabel(ancora.rotulo);
}

interface ParecerAncoraChipsProps {
  ancoras: Ancora[] | undefined;
}

/** Chips de âncora (D2-puro). Renderiza só âncoras com valor resolvido; v1 (sem
 *  ancoras) ou âncora sem valor → nada. */
export function ParecerAncoraChips({ ancoras }: ParecerAncoraChipsProps) {
  const valid = (ancoras ?? []).filter((a) => a.valor_renderizado);
  if (valid.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5" data-testid="parecer-ancoras">
      {valid.map((a, i) => (
        <span
          key={`${a.path ?? a.rotulo ?? "ancora"}-${i}`}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--surface-border)] bg-[var(--surface-muted)] px-2 py-0.5 text-[11px] text-[var(--surface-muted-foreground)]"
        >
          <span>{chipLabel(a)}</span>
          <span className="font-mono tabular-nums text-[var(--surface-foreground)]">
            {a.valor_renderizado}
          </span>
        </span>
      ))}
    </div>
  );
}
