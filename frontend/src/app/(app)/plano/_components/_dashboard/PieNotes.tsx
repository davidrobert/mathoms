import { MonetaryValue } from "@/components/report/MonetaryValue";

import type { PieNote } from "./dashboardPie";

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

/** Notas acima da pizza, não abaixo: a base do que as fatias somam é lida antes da
 *  conclusão que o gráfico sugere. */
export function PieNotes({ notes }: { notes: readonly PieNote[] }) {
  if (notes.length === 0) return null;
  return (
    <div className="mb-2 space-y-1 text-xs text-muted-foreground" data-testid="pie-notes">
      {notes.map((note, i) => (
        <p key={`${note.kind}-${i}`} data-note-kind={note.kind}>
          <BaseDespesas {...note} />
        </p>
      ))}
    </div>
  );
}
