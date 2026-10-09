import Link from "next/link";
import type { ReactNode } from "react";

import { MonetaryValue } from "@/components/report/MonetaryValue";
import type { MotivoBaldeImovel } from "@/types/report-analysis";

import type { PieNote } from "./dashboardPie";

const MARCAR_RESIDENCIA = (
  <Link href="/config?tab=members" className="text-[var(--brand-primary)] underline">
    Marcar residência
  </Link>
);

const FALTA_INDICAR: ReactNode = (
  <>
    Residência não apurada: falta indicar a residência; até lá, todos os imóveis contam em
    Outros imóveis · {MARCAR_RESIDENCIA}
  </>
);

/** ADR-439 D2: a nota diz a direção do erro e a ação. Exaustivo de propósito — motivo
 *  novo no tipo quebra o build aqui. `vinculo_perdido`/`nao_classificados` são do balde
 *  de geradores; na linha da residência caem no ramo "falta indicar", como no relatório. */
const NOTA_RESIDENCIA: Record<MotivoBaldeImovel, ReactNode> = {
  nao_classificada: FALTA_INDICAR,
  nao_declarada: FALTA_INDICAR,
  vinculo_perdido: FALTA_INDICAR,
  nao_classificados: FALTA_INDICAR,
  nao_localizada:
    "Residência não apurada: o imóvel marcado não foi localizado; o valor dele pode estar em Outros imóveis.",
  sem_valor:
    "Residência não apurada: o imóvel marcado está sem valor apurado em 31/12; fica fora do patrimônio.",
};

function mesesDocumentados(n: number): string {
  return n === 1 ? "Último mês documentado" : `Últimos ${n} meses documentados`;
}

function BaseDespesas({ janelaMeses, aporteExcluido }: { janelaMeses: number; aporteExcluido: number }) {
  if (aporteExcluido <= 0) return <>{mesesDocumentados(janelaMeses)}.</>;
  return (
    <>
      {mesesDocumentados(janelaMeses)}, sem os aportes em investimentos (
      <MonetaryValue value={aporteExcluido} fractionDigits={0} />
      ), que contam como poupança.
    </>
  );
}

function NoteText({ note }: { note: PieNote }) {
  if (note.kind === "residencia_nao_apurada") return <>{NOTA_RESIDENCIA[note.motivo]}</>;
  if (note.kind === "base_despesas") return <BaseDespesas {...note} />;
  return (
    <>
      Fora do gráfico: {note.categoria} <MonetaryValue value={note.valor} />, em conferência.
    </>
  );
}

/** Notas acima da pizza, não abaixo: a residência costuma ser o maior ativo e não tem
 *  área no donut — lida depois do gráfico, a conclusão já foi tirada. */
export function PieNotes({ notes }: { notes: readonly PieNote[] }) {
  if (notes.length === 0) return null;
  return (
    <div className="mb-2 space-y-1 text-xs text-muted-foreground" data-testid="pie-notes">
      {notes.map((note, i) => (
        <p key={`${note.kind}-${i}`} data-note-kind={note.kind}>
          <NoteText note={note} />
        </p>
      ))}
    </div>
  );
}
