import * as XLSX from "xlsx";
import { toast } from "sonner";
import type { TransactionItem } from "@/lib/api";
import { API_BASE, getToken } from "@/lib/api";
import { bankLabel } from "@/lib/format";
import type { FilterState } from "./FiltersPanel";

function buildFilterQuery(search: string, filters: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (filters.bank) params.set("bank", filters.bank);
  if (filters.category) params.set("category", filters.category);
  if (filters.member) params.set("member", filters.member);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.valueMin) params.set("value_min", filters.valueMin);
  if (filters.valueMax) params.set("value_max", filters.valueMax);
  return params;
}

/** Server-side CSV export — baixa TODAS as transações filtradas
 *  (não apenas a página atual). BUG-009. */
function exportCsvServerSide(search: string, filters: FilterState) {
  const params = buildFilterQuery(search, filters);
  params.set("format", "csv");
  const token = getToken();
  const url = `${API_BASE}/transactions/export?${params.toString()}`;

  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((res) => {
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    })
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "transacoes.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(() => toast.error("Erro ao exportar transações"));
}

/** Client-side XLSX export — apenas a página atual.
 *  (Server-side XLSX ainda não implementado.) */
function exportXlsxClientSide(transactions: TransactionItem[]) {
  const rows = transactions.map((tx) => ({
    Data: tx.data,
    Descrição: tx.descricao,
    Valor: tx.valor,
    Categoria: tx.categoria,
    Banco: bankLabel(tx.banco),
    Titular: tx.titular || "",
    Moeda: tx.moeda || "BRL",
    "Tipo Conta": tx.tipo_conta || "",
    Origem: tx.origem || "",
    Editado: tx.is_overridden ? "Sim" : "Não",
  }));

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Transações");
  XLSX.writeFile(wb, "transacoes.xlsx");
}

export function exportTransactions(
  format: "csv" | "xlsx",
  transactions: TransactionItem[],
  search: string,
  filters: FilterState,
) {
  if (transactions.length === 0) return;
  if (format === "csv") exportCsvServerSide(search, filters);
  else exportXlsxClientSide(transactions);
}
