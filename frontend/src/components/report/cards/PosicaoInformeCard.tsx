"use client";

import type { Posicao3112Row } from "@/types/report-analysis";
import { MonetaryValue, type Currency } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";

interface PosicaoInformeCardProps {
  posicoes: readonly Posicao3112Row[] | undefined;
  cbeObrigatorio: boolean;
}

const MOEDAS_SUPORTADAS: readonly Currency[] = ["USD", "EUR", "GBP"];

/** A33.l2 P4 (ADR-238 D5 · co-design product-designer 2026-07-07) — card S1
 * "Posição por Instituição e Moeda (31/12)".
 *
 * Hide-when-empty: sem posição vinda de informe, retorna null (extrato puro
 * já é coberto pelos cards de caixa/exposição cambial).
 */
export function PosicaoInformeCard({ posicoes, cbeObrigatorio }: PosicaoInformeCardProps) {
  const rows = posicoes ?? [];
  const hasInforme = rows.some((r) => r.fonte === "informe_31_12");
  if (!hasInforme) return null;
  const informeVenceu = rows.some((r) => r.informe_venceu_extrato);
  return (
    <ReportCard size="full" variant="feature" title="Posição por Instituição e Moeda (31/12)">
      {cbeObrigatorio && <CbeAlert />}
      {informeVenceu && <InformeVenceuNudge />}
      <PosicaoTable rows={rows} />
      <PtaxFootnote rows={rows} />
    </ReportCard>
  );
}

/** Alert CBE no TOPO do card (gatilho é o agregado, não a linha). */
function CbeAlert() {
  return (
    <aside
      role="alert"
      className="mb-4 rounded-md border-l-4 p-3 text-sm"
      style={{
        borderLeftColor: "var(--brand-warning)",
        backgroundColor: "var(--surface-muted)",
        color: "var(--surface-foreground)",
      }}
    >
      <strong>Declaração CBE ao Banco Central pode ser obrigatória.</strong>{" "}
      Seus ativos no exterior somam mais de US$ 1 milhão em 31/12. A partir desse valor, o
      Banco Central exige a Declaração de Capitais Brasileiros no Exterior (CBE). Confirme o
      enquadramento com seu contador.
    </aside>
  );
}

/** Nudge estilo ValorMercadoNudge — só quando o informe venceu o extrato (D+1). */
function InformeVenceuNudge() {
  return (
    <aside
      role="note"
      className="mb-4 rounded-md border p-3 text-sm"
      style={{
        borderColor: "var(--semantic-info-financial)",
        backgroundColor: "var(--surface-muted)",
        color: "var(--surface-foreground)",
      }}
    >
      <strong>Posição de fechamento do ano, informada pela instituição.</strong> Pode diferir
      do saldo atual no extrato — reflete 31/12.
    </aside>
  );
}

function PosicaoTable({ rows }: { rows: readonly Posicao3112Row[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">
          Posição por instituição e moeda em 31/12 — saldos de informes de rendimentos e
          extratos, convertidos a real pela PTAX de compra
        </caption>
        <thead className="text-[var(--surface-muted-foreground)]">
          <tr className="border-b border-[var(--surface-border)] text-left">
            <th className="py-1 pr-2 font-display font-semibold">Instituição</th>
            <th className="py-1 pr-2 font-display font-semibold">Moeda</th>
            <th className="py-1 pr-2 text-right font-display font-semibold">Valor em 31/12</th>
            <th className="py-1 font-display font-semibold">Fonte</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <PosicaoRow key={`${row.instituicao}-${row.moeda}-${idx}`} row={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PosicaoRow({ row }: { row: Posicao3112Row }) {
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2 pr-2">{row.instituicao}</td>
      <td className="py-2 pr-2 font-mono tabular-nums">{row.moeda}</td>
      <td className="py-2 pr-2 text-right">
        <ValorCell row={row} />
      </td>
      <td className="py-2">
        <FonteChip fonte={row.fonte} />
      </td>
    </tr>
  );
}

/** Valor primário em BRL; moeda original como linha secundária mono SEMPRE
 * visível (PDF sem hover). Contas BRL: sem linha secundária. */
function ValorCell({ row }: { row: Posicao3112Row }) {
  return (
    <div className="flex flex-col items-end">
      {row.valor_brl !== null ? (
        <MonetaryValue value={row.valor_brl} />
      ) : (
        <span className="text-[var(--surface-muted-foreground)]" title="PTAX indisponível">
          —
        </span>
      )}
      {row.valor_original !== null && row.moeda !== "BRL" && (
        <span className="font-mono text-xs tabular-nums text-[var(--surface-foreground)]">
          <ValorOriginal moeda={row.moeda} valor={row.valor_original} />
        </span>
      )}
    </div>
  );
}

function ValorOriginal({ moeda, valor }: { moeda: string; valor: number }) {
  if ((MOEDAS_SUPORTADAS as readonly string[]).includes(moeda)) {
    return <MonetaryValue value={valor} currency={moeda as Currency} />;
  }
  return (
    <>
      {moeda} {valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
    </>
  );
}

/** Chip de fonte com dot + texto — nunca só cor (a11y). */
function FonteChip({ fonte }: { fonte: string }) {
  const isInforme = fonte === "informe_31_12";
  const label = isInforme ? "Informe 31/12" : "Extrato";
  const tone = isInforme ? "var(--brand-info)" : "var(--surface-muted-foreground)";
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span
        aria-hidden="true"
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: tone }}
      />
      <span aria-label={`Fonte do saldo: ${label}`}>{label}</span>
    </span>
  );
}

function PtaxFootnote({ rows }: { rows: readonly Posicao3112Row[] }) {
  const anos = rows
    .filter((r) => r.fonte === "informe_31_12" && r.ano_base !== null)
    .map((r) => r.ano_base as number);
  if (anos.length === 0) return null;
  const ano = Math.max(...anos);
  return (
    <p className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
      Saldos em moeda estrangeira convertidos a real pela PTAX de compra de 31/12/{ano} (Banco
      Central).
    </p>
  );
}
