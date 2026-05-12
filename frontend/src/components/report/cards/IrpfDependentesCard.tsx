import { ReportCard } from "../ReportCard";
import type { CardVariant } from "@/generated/report-layout";
import type { DependentesKpi } from "@/types/irpf";

interface IrpfDependentesCardProps {
  dependentes: DependentesKpi;
  anoBase: number;
  variant?: CardVariant;
}

/** ADR-194 §D8 — labels pt-BR para `RelacaoDependente` (ordem fixa de exibição). */
const RELACAO_LABEL: Record<string, string> = {
  conjuge_companheiro: "cônjuge",
  filho_filha: "filho/filha",
  enteado_enteada: "enteado/enteada",
  irmao_irma: "irmão/irmã",
  neto_neta: "neto/neta",
  pai_mae: "pai/mãe",
  avo: "avô/avó",
  bisavo: "bisavô/bisavó",
  bisneto_bisneta: "bisneto/bisneta",
  sogro_sogra: "sogro/sogra",
  menor_pobre: "menor pobre",
  tutelado: "tutelado",
  incapaz: "incapaz",
  outro: "outro",
};

const RELACAO_ORDEM: readonly string[] = [
  "conjuge_companheiro",
  "filho_filha",
  "enteado_enteada",
  "irmao_irma",
  "neto_neta",
  "pai_mae",
  "avo",
  "sogro_sogra",
  "menor_pobre",
  "tutelado",
  "incapaz",
  "bisavo",
  "bisneto_bisneta",
  "outro",
];

const CARDINAIS_EXTENSO: Record<number, string> = {
  1: "Um",
  2: "Dois",
  3: "Três",
};

function formatCount(n: number): string {
  return CARDINAIS_EXTENSO[n] ?? String(n);
}

function formatListaRelacoes(porRelacao: Record<string, number>): string {
  const partes: string[] = [];
  for (const key of RELACAO_ORDEM) {
    const n = porRelacao[key];
    if (typeof n === "number" && n > 0) {
      partes.push(`${RELACAO_LABEL[key] ?? key} · ${n}`);
    }
  }
  return partes.join(", ");
}

/** ADR-194 §6.1 — Dependentes Declarados (factual, sem prescrição).
 *
 * Esconde quando `count == 0` — guard em `IrpfOtimizacaoSection`. Copy
 * literal congelada por G0 (financial-planner) em 2026-05-12. Sem
 * disclaimer (não há recomendação a desclarar). */
export function IrpfDependentesCard({
  dependentes,
  anoBase,
  variant = "neutral",
}: IrpfDependentesCardProps) {
  const { count, por_relacao } = dependentes;
  const singularPlural =
    count === 1
      ? { dep: "dependente", decl: "declarado" }
      : { dep: "dependentes", decl: "declarados" };
  const lista = formatListaRelacoes(por_relacao);

  return (
    <ReportCard variant={variant} size="half" title="Dependentes Declarados">
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Composição declarada à RFB · {anoBase}
        </p>
        <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
          {count}
        </p>
        <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
          {formatCount(count)} {singularPlural.dep} {singularPlural.decl} em{" "}
          {anoBase}
          {lista ? `: ${lista}.` : "."}
        </p>
      </div>
    </ReportCard>
  );
}
