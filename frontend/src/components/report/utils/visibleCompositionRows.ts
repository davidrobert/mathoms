import type { PatrimonioCategoria, PatrimonioData } from "@/types/report-analysis";

/** A40.l71 (RV6-23) — predicado ÚNICO da composição patrimonial.
 *
 * O donut e a tabela liam `composicao` com dois `filter` próprios e
 * divergentes: o gráfico sumia com zero E negativo (`valor > 0`), a tabela
 * imprimia tudo menos "Residência" zero. Sobre payload com balde negativo as
 * duas respondiam diferente na mesma tela. Aqui o caso é decidido uma vez, com
 * nome, e cada componente projeta o que sabe renderizar.
 */

/** Vocabulário compartilhado com `cobertura_investimentos[]` (A40.l69). */
export type CompositionRowState =
  | "apurado"
  | "negativo"
  | "zero_apurado"
  | "nao_apurado";

export interface VisibleCompositionRow extends PatrimonioCategoria {
  readonly state: CompositionRowState;
}

export interface DonutSlice {
  readonly label: string;
  readonly value: number;
}

/** Label da residência — ADR-215 P5 esconde a linha quando ela vale R$ 0,00
 *  ("zero ≠ dado ausente" até o usuário marcar a residência via MembersTab).
 *
 *  É o LABEL, não o `template_key`: a ADR-145 declara `template_key` estável e
 *  proíbe rename, mas o payload transmite só o rótulo exibido
 *  (`patrimonio_calculator.py:455`), e dois dos seis rótulos interpolam nome de
 *  membro. Enquanto a chave não trafegar, quem impede o rename silencioso é o
 *  gate de paridade `dev/check_composicao_predicate.py`, não o tipo. */
export const CATEGORIA_RESIDENCIA_LABEL = "Residência";

/** Zero da residência não vira linha nenhuma (ADR-215 P5) — os demais zeros
 *  viram estado, porque some-los foi o que produziu o desacordo do RV6-23. */
function isHiddenResidenciaZero(row: PatrimonioCategoria): boolean {
  return row.categoria === CATEGORIA_RESIDENCIA_LABEL && row.valor === 0;
}

/** `hasCoverage` chega da `cobertura_investimentos[]` (A40.l69). Enquanto ela
 *  não existe no payload, todo zero é `nao_apurado`: afirmar `zero_apurado` sem
 *  fonte é exatamente a afirmação falsa do RV6-04. */
function classify(row: PatrimonioCategoria, hasCoverage: boolean): CompositionRowState {
  if (row.valor < 0) return "negativo";
  if (row.valor > 0) return "apurado";
  return hasCoverage ? "zero_apurado" : "nao_apurado";
}

function coversCategoria(
  cobertura: ReadonlySet<string> | undefined,
  categoria: string,
): boolean {
  return cobertura !== undefined && cobertura.has(categoria);
}

/** Linhas da composição classificadas — fonte única para tabela e donut. */
export function visibleCompositionRows(
  patrimonio: PatrimonioData | undefined,
  cobertura?: ReadonlySet<string>,
): VisibleCompositionRow[] {
  const rows = patrimonio?.composicao ?? patrimonio?.tabela_categorias ?? [];
  return rows
    .filter((row) => !isHiddenResidenciaZero(row))
    .map((row) => ({ ...row, state: classify(row, coversCategoria(cobertura, row.categoria)) }));
}

/** Fatias do donut. A assimetria vs. a tabela é INTENCIONAL: área zero ou
 *  negativa não é representável num donut, enquanto a linha da tabela é onde o
 *  número presta contas. O que a l71 elimina não é a assimetria — é ela existir
 *  por acidente, escrita duas vezes e divergente. */
export function donutSlices(rows: readonly VisibleCompositionRow[]): DonutSlice[] {
  return rows
    .filter((row) => row.state === "apurado")
    .map((row) => ({ label: row.categoria, value: row.valor }));
}
