// ADR-296 (A26.l9) — citação determinística D2-puro: a prosa não traz R$; cada
// âncora vira um chip no rodapé do card (rótulo legível + valor renderizado pelo
// finalize). O contrato carrega o root canônico; a UI embeleza root → label.

import type { Ancora } from "@/lib/api";

const ROTULO_LABEL: Record<string, string> = {
  reserva_emergencia: "Reserva de emergência",
  endividamento: "Endividamento",
  passive_income: "Renda passiva",
  if_monte_carlo: "Independência financeira",
  patrimonio: "Patrimônio",
  fluxo_caixa: "Fluxo de caixa",
  investimentos: "Investimentos",
  // "Previdência" nu é o único item deste mapa que o COPY_GUIDELINES §2
  // proíbe (ambíguo entre PGBL e VGBL). O rótulo é PROCEDÊNCIA do dado,
  // não da seção — e "Previdência PGBL" é a string que o leitor encontra
  // ao seguir a pista: é o title do PrevidenciaPgblCard (A40.l7).
  previdencia_pgbl: "Previdência PGBL",
  irpf_kpis: "Imposto de renda",
  cenarios_conjuge: "Cenário do casal",
  consumo_consciente: "Consumo",
  goals: "Metas",
};

function rotuloLabel(rotulo: string | null): string {
  if (!rotulo) return "Evidência";
  return ROTULO_LABEL[rotulo] ?? rotulo;
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
          <span>{rotuloLabel(a.rotulo)}</span>
          <span className="font-mono tabular-nums text-[var(--surface-foreground)]">
            {a.valor_renderizado}
          </span>
        </span>
      ))}
    </div>
  );
}
