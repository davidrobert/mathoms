import { MonetaryValue } from "@/components/report/MonetaryValue";
import { NotaResidenciaNaoApurada } from "@/lib/residenciaNaoApurada";

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

function NoteText({ note }: { note: PieNote }) {
  if (note.kind === "residencia_nao_apurada") return <NotaResidenciaNaoApurada motivo={note.motivo} />;
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
