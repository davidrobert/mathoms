import {
  donutSlices,
  visibleCompositionRows,
  type VisibleCompositionRow,
} from "@/components/report/utils/visibleCompositionRows";
import type { DashboardChart } from "@/lib/api";
import { humanizeCategoryLabel, isAporteInvestimentoKey } from "@/lib/categoryLabels";
import type { MotivoBaldeImovel, PatrimonioData } from "@/types/report-analysis";

/** `id` é o que o clique leva ao deep-link (chave crua da categoria); `name`, o rótulo. */
export interface PieSlice {
  id: string;
  name: string;
  value: number;
}

export type PieNote =
  | { kind: "residencia_nao_apurada"; motivo: MotivoBaldeImovel }
  | { kind: "fora_do_grafico"; categoria: string; valor: number }
  | { kind: "base_despesas"; janelaMeses: number; aporteExcluido: number };

export interface DashboardPie {
  slices: PieSlice[];
  notes: PieNote[];
  /** Só a pizza de despesas tem destino no clique (`/transactions?category=`). */
  clickable: boolean;
}

interface DespesasPayload {
  categorias?: Record<string, number>;
  janela_meses?: number;
}

const SEM_FATIAS: DashboardPie = { slices: [], notes: [], clickable: false };

/** O payload declara de que bloco do E5 vem (`fonte`); cada fonte tem o seu leitor de
 *  domínio, o mesmo do relatório — nenhum predicado reescrito aqui nem no backend. */
export function normalizePieData(chart: DashboardChart): DashboardPie {
  const fonte = (chart.data as { fonte?: unknown }).fonte;
  if (fonte === "composicao_patrimonial") {
    return composicaoPie(chart.data as PatrimonioData);
  }
  if (fonte === "despesas_por_categoria") {
    return despesasPie(chart.data as DespesasPayload);
  }
  return SEM_FATIAS;
}

function composicaoPie(patrimonio: PatrimonioData): DashboardPie {
  const rows = visibleCompositionRows(patrimonio);
  const slices = donutSlices(rows).map((s) => ({ id: s.label, name: s.label, value: s.value }));
  return { slices, notes: composicaoNotes(rows), clickable: false };
}

/** ADR-439 D5: a residência não apurada não tem área no donut e não pode virar zero —
 *  a nota é o único lugar onde ela aparece. Negativo idem: área não representa sinal. */
function composicaoNotes(rows: readonly VisibleCompositionRow[]): PieNote[] {
  const notes: PieNote[] = [];
  const residencia = rows.find((row) => row.state === "nao_apurado" && row.motivo);
  if (residencia?.motivo) notes.push({ kind: "residencia_nao_apurada", motivo: residencia.motivo });
  for (const row of rows) {
    if (row.state === "negativo") {
      notes.push({ kind: "fora_do_grafico", categoria: row.categoria, valor: row.valor });
    }
  }
  return notes;
}

/** ADR-333 §Emenda: aporte é poupança, não consumo — sai das fatias, e o valor retirado
 *  vai para a nota de base, que é o que faz a pizza bater com a série de saídas. */
function despesasPie(payload: DespesasPayload): DashboardPie {
  const entries = Object.entries(payload.categorias ?? {});
  const aporteExcluido = entries
    .filter(([key]) => isAporteInvestimentoKey(key))
    .reduce((acc, [, value]) => acc + value, 0);
  const slices = entries
    .filter(([key, value]) => !isAporteInvestimentoKey(key) && value > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([key, value]) => ({ id: key, name: humanizeCategoryLabel(key), value }));
  const janelaMeses = payload.janela_meses ?? 0;
  return { slices, notes: [{ kind: "base_despesas", janelaMeses, aporteExcluido }], clickable: true };
}
