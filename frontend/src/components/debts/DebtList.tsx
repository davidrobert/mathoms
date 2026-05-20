"use client";

/**
 * Tabela compacta de Debts (ADR-227 §D1 · Sprint A15 Onda 5).
 *
 * Reutilizada na tela de batch review (`/imoveis/financiamentos-review`)
 * e por painéis futuros (drill-down do RealEstateBreakdownPanel). Foco:
 * leitura — mutações são responsabilidade do caller (via callbacks).
 */

import { Badge } from "@/components/ui/badge";
import { MonetaryValue } from "@/components/report/MonetaryValue";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DebtResponse, DebtTipo } from "@/lib/api/debts";

const TIPO_LABEL: Record<DebtTipo, string> = {
  financiamento_imobiliario: "Financiamento imobiliário",
  consignado: "Consignado",
  cdc: "CDC",
  cartao_rotativo: "Cartão rotativo",
  rotativo: "Crédito rotativo",
  outro: "Outro",
};

export interface PropertyLookup {
  [propertyId: string]: string;
}

export interface DebtListProps {
  debts: DebtResponse[];
  /** Mapping property_id → label, para renderizar nome em vez de UUID. */
  propertyLabels?: PropertyLookup;
  /** Slot extra na última coluna por linha (botões de ação contextuais). */
  renderActions?: (debt: DebtResponse) => React.ReactNode;
  emptyMessage?: string;
}

function _toNumberSafe(value: string | null): number | null {
  if (!value) return null;
  const n = Number.parseFloat(value);
  return Number.isFinite(n) ? n : null;
}

export function DebtList({
  debts,
  propertyLabels = {},
  renderActions,
  emptyMessage = "Nenhuma dívida cadastrada.",
}: DebtListProps) {
  if (debts.length === 0) {
    return (
      <p
        className="rounded-md border p-6 text-center text-sm"
        style={{ color: "var(--surface-muted-foreground)", borderColor: "var(--surface-border)" }}
      >
        {emptyMessage}
      </p>
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead>Tipo</TableHead>
          <TableHead>Imóvel</TableHead>
          <TableHead className="text-right">Saldo devedor</TableHead>
          <TableHead>Status</TableHead>
          {renderActions && <TableHead className="text-right">Ações</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {debts.map((debt) => (
          <TableRow key={debt.id}>
            <TableCell className="max-w-xs truncate">{debt.descricao ?? "—"}</TableCell>
            <TableCell>{TIPO_LABEL[debt.tipo]}</TableCell>
            <TableCell>
              {debt.property_id ? propertyLabels[debt.property_id] ?? "Sem nome" : "Sem vínculo"}
            </TableCell>
            <TableCell className="text-right">
              <MonetaryValue value={_toNumberSafe(debt.saldo_devedor_brl)} />
            </TableCell>
            <TableCell>
              {debt.needs_review ? (
                <Badge variant="outline">Precisa revisão</Badge>
              ) : (
                <Badge variant="secondary">OK</Badge>
              )}
            </TableCell>
            {renderActions && (
              <TableCell className="text-right">{renderActions(debt)}</TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
