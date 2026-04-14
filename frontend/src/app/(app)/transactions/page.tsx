"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import * as XLSX from "xlsx";
import {
  listTransactions,
  listCategories,
  listMembers,
  overrideTransactionCategory,
  removeTransactionOverride,
  type TransactionItem,
  type TransactionListResponse,
  type CategoryConfig,
  type FamilyMemberConfig,
  ApiError,
} from "@/lib/api";
import { formatCurrency, formatDateShort, bankLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  X,
  Pencil,
  Check,
  Undo2,
  FileSpreadsheet,
  FileDown,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  ArrowLeftRight,
} from "lucide-react";

const PAGE_SIZE = 50;

const BANK_OPTIONS = [
  { value: "itau", label: "Itaú" },
  { value: "bradesco", label: "Bradesco" },
  { value: "santander", label: "Santander" },
  { value: "c6bank", label: "C6 Bank" },
  { value: "btgpactual", label: "BTG Pactual" },
  { value: "rico", label: "Rico" },
  { value: "picpay", label: "PicPay" },
  { value: "wise", label: "Wise" },
  { value: "bankofamerica", label: "Bank of America" },
  { value: "quintoandar", label: "QuintoAndar" },
  { value: "binance", label: "Binance" },
  { value: "nubank", label: "Nubank" },
  { value: "inter", label: "Inter" },
];

export default function TransactionsPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    }>
      <TransactionsContent />
    </Suspense>
  );
}

function TransactionsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // --- State from URL ---
  const initialSearch = searchParams.get("search") ?? "";
  const initialPage = Number(searchParams.get("page") ?? "1");
  const initialBank = searchParams.get("bank") ?? "";
  const initialCategory = searchParams.get("category") ?? "";
  const initialMember = searchParams.get("member") ?? "";
  const initialDateFrom = searchParams.get("date_from") ?? "";
  const initialDateTo = searchParams.get("date_to") ?? "";
  const initialValueMin = searchParams.get("value_min") ?? "";
  const initialValueMax = searchParams.get("value_max") ?? "";

  const [search, setSearch] = useState(initialSearch);
  const [bank, setBank] = useState(initialBank);
  const [category, setCategory] = useState(initialCategory);
  const [member, setMember] = useState(initialMember);
  const [dateFrom, setDateFrom] = useState(initialDateFrom);
  const [dateTo, setDateTo] = useState(initialDateTo);
  const [valueMin, setValueMin] = useState(initialValueMin);
  const [valueMax, setValueMax] = useState(initialValueMax);
  const [page, setPage] = useState(initialPage);

  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(
    !!(initialBank || initialCategory || initialMember || initialDateFrom || initialDateTo || initialValueMin || initialValueMax)
  );

  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);

  const [editingHash, setEditingHash] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // --- Load categories & members for filter dropdowns ---
  useEffect(() => {
    listCategories().then((r) => setCategories(r.categories)).catch(() => {});
    listMembers().then((r) => setMembers(r.members)).catch(() => {});
  }, []);

  // --- Build query params and push to URL ---
  const pushParams = useCallback(
    (overrides: Record<string, string | number | undefined>) => {
      const params = new URLSearchParams();
      const merged: Record<string, string | number | undefined> = {
        search,
        bank,
        category,
        member,
        date_from: dateFrom,
        date_to: dateTo,
        value_min: valueMin,
        value_max: valueMax,
        page,
        ...overrides,
      };
      Object.entries(merged).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "" && v !== 0 && !(k === "page" && v === 1)) {
          params.set(k, String(v));
        }
      });
      const qs = params.toString();
      router.replace(`/transactions${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [search, bank, category, member, dateFrom, dateTo, valueMin, valueMax, page, router]
  );

  // --- Fetch transactions ---
  const fetchData = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    try {
      const result = await listTransactions({
        search: search || undefined,
        bank: bank || undefined,
        category: category || undefined,
        member: member || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        value_min: valueMin ? Number(valueMin) : undefined,
        value_max: valueMax ? Number(valueMax) : undefined,
        page,
        page_size: PAGE_SIZE,
      });
      if (!controller.signal.aborted) {
        setData(result);
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(
          err instanceof ApiError ? err.detail : "Erro ao carregar transações"
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [search, bank, category, member, dateFrom, dateTo, valueMin, valueMax, page]);

  useEffect(() => {
    fetchData();
    return () => abortRef.current?.abort();
  }, [fetchData]);

  // --- Debounced search ---
  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      pushParams({ search: value, page: 1 });
    }, 300);
  }

  // --- Filter changes ---
  function applyFilter(key: string, value: string) {
    const setters: Record<string, (v: string) => void> = {
      bank: setBank,
      category: setCategory,
      member: setMember,
      date_from: setDateFrom,
      date_to: setDateTo,
      value_min: setValueMin,
      value_max: setValueMax,
    };
    setters[key]?.(value);
    setPage(1);
    pushParams({ [key]: value, page: 1 });
  }

  function clearAllFilters() {
    setSearch("");
    setBank("");
    setCategory("");
    setMember("");
    setDateFrom("");
    setDateTo("");
    setValueMin("");
    setValueMax("");
    setPage(1);
    router.replace("/transactions", { scroll: false });
  }

  const hasActiveFilters = !!(search || bank || category || member || dateFrom || dateTo || valueMin || valueMax);

  // --- Pagination ---
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function goPage(p: number) {
    setPage(p);
    pushParams({ page: p });
  }

  // --- Category override ---
  function startEdit(tx: TransactionItem) {
    setEditingHash(tx.transaction_hash);
    setEditCategory(tx.categoria);
  }

  async function saveOverride(hash: string) {
    if (!editCategory) return;
    setSavingOverride(true);
    try {
      await overrideTransactionCategory(hash, { new_category: editCategory });
      setEditingHash(null);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Erro ao salvar override"
      );
    } finally {
      setSavingOverride(false);
    }
  }

  async function removeOverride(hash: string) {
    setSavingOverride(true);
    try {
      await removeTransactionOverride(hash);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Erro ao remover override"
      );
    } finally {
      setSavingOverride(false);
    }
  }

  // --- Unique categories from data + config ---
  const categoryOptions = useMemo(() => {
    const fromConfig = categories.map((c) => c.code);
    const fromData = data?.transactions.map((t) => t.categoria) ?? [];
    const all = [...new Set([...fromConfig, ...fromData])].filter(Boolean).sort();
    return all;
  }, [categories, data]);

  // --- Export ---
  function exportTransactions(format: "csv" | "xlsx") {
    if (!data?.transactions.length) return;

    const rows = data.transactions.map((tx) => ({
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

    if (format === "xlsx") {
      XLSX.writeFile(wb, "transacoes.xlsx");
    } else {
      XLSX.writeFile(wb, "transacoes.csv", { bookType: "csv" });
    }
  }

  // --- Render ---
  const summary = data?.summary;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Transações"
        description="Explore e gerencie todas as transações financeiras"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data?.transactions.length}
              onClick={() => exportTransactions("csv")}
            >
              <FileDown className="mr-1.5 h-3.5 w-3.5" />
              CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data?.transactions.length}
              onClick={() => exportTransactions("xlsx")}
            >
              <FileSpreadsheet className="mr-1.5 h-3.5 w-3.5" />
              XLSX
            </Button>
          </div>
        }
      />

      {/* Search bar */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar por descrição, banco, categoria..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="pl-9 pr-9"
        />
        {search && (
          <button
            onClick={() => handleSearchChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Filter toggle */}
      <div className="mb-4 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFiltersOpen(!filtersOpen)}
          className={cn(hasActiveFilters && "border-primary text-primary")}
        >
          <Filter className="mr-1.5 h-3.5 w-3.5" />
          Filtros
          {hasActiveFilters && (
            <Badge variant="default" className="ml-1.5 h-4 min-w-4 px-1 text-[10px]">
              {[bank, category, member, dateFrom, dateTo, valueMin, valueMax].filter(Boolean).length}
            </Badge>
          )}
          {filtersOpen ? (
            <ChevronUp className="ml-1 h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="ml-1 h-3.5 w-3.5" />
          )}
        </Button>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            <X className="mr-1 h-3.5 w-3.5" />
            Limpar filtros
          </Button>
        )}
      </div>

      {/* Filter panel */}
      {filtersOpen && (
        <Card className="mb-6 p-0">
          <div className="grid grid-cols-1 gap-4 px-4 py-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Date range */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Data início</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => applyFilter("date_from", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Data fim</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => applyFilter("date_to", e.target.value)}
              />
            </div>

            {/* Bank */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Banco</label>
              <Select value={bank} onValueChange={(v) => applyFilter("bank", v as string)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  {BANK_OPTIONS.map((b) => (
                    <SelectItem key={b.value} value={b.value}>{b.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Category */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Categoria</label>
              <Select value={category} onValueChange={(v) => applyFilter("category", v as string)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todas</SelectItem>
                  {categoryOptions.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Member */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Titular</label>
              <Select value={member} onValueChange={(v) => applyFilter("member", v as string)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  {members.map((m) => (
                    <SelectItem key={m.key} value={m.key}>{m.short_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Value range */}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Valor mínimo</label>
              <Input
                type="number"
                step="0.01"
                placeholder="0,00"
                value={valueMin}
                onChange={(e) => applyFilter("value_min", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Valor máximo</label>
              <Input
                type="number"
                step="0.01"
                placeholder="0,00"
                value={valueMax}
                onChange={(e) => applyFilter("value_max", e.target.value)}
              />
            </div>
          </div>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">
            fechar
          </button>
        </div>
      )}

      {/* Summary bar */}
      {summary && data && data.transactions.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
            <TrendingUp className="h-4 w-4 text-gain" />
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Receitas</p>
              <p className="text-sm font-semibold tabular-nums text-gain">{formatCurrency(summary.total_receitas)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
            <TrendingDown className="h-4 w-4 text-loss" />
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Despesas</p>
              <p className="text-sm font-semibold tabular-nums text-loss">{formatCurrency(summary.total_despesas)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
            <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Saldo</p>
              <p className={cn(
                "text-sm font-semibold tabular-nums",
                summary.saldo >= 0 ? "text-gain" : "text-loss"
              )}>
                {formatCurrency(summary.saldo)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
            <Download className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Transações</p>
              <p className="text-sm font-semibold tabular-nums">{summary.count.toLocaleString("pt-BR")}</p>
            </div>
          </div>
        </div>
      )}

      {/* Period info */}
      {summary?.periodo_inicio && summary?.periodo_fim && (
        <p className="mb-4 text-xs text-muted-foreground">
          Período: {formatDateShort(summary.periodo_inicio)} — {formatDateShort(summary.periodo_fim)}
        </p>
      )}

      {/* Main content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : !data || data.transactions.length === 0 ? (
        <EmptyState
          variant="no-data"
          title="Nenhuma transação encontrada"
          description={
            hasActiveFilters
              ? "Tente ajustar os filtros para encontrar transações."
              : "Execute o pipeline para processar documentos e gerar transações."
          }
          action={
            hasActiveFilters
              ? { label: "Limpar filtros", onClick: clearAllFilters }
              : { label: "Ir para Pipeline", href: "/pipeline" }
          }
        />
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead className="min-w-[200px]">Descrição</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead>Banco</TableHead>
                  <TableHead>Titular</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.transactions.map((tx) => (
                  <TableRow key={tx.transaction_hash}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {formatDateShort(tx.data)}
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate" title={tx.descricao}>
                      {tx.descricao}
                    </TableCell>
                    <TableCell>
                      {editingHash === tx.transaction_hash ? (
                        <div className="flex items-center gap-1">
                          <select
                            value={editCategory}
                            onChange={(e) => setEditCategory(e.target.value)}
                            className="h-7 rounded-md border border-input bg-transparent px-2 text-xs outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
                          >
                            {categoryOptions.map((c) => (
                              <option key={c} value={c}>{c}</option>
                            ))}
                          </select>
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            disabled={savingOverride}
                            onClick={() => saveOverride(tx.transaction_hash)}
                          >
                            <Check className="h-3.5 w-3.5 text-gain" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            onClick={() => setEditingHash(null)}
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1">
                          <Badge
                            variant="outline"
                            className="cursor-pointer hover:bg-accent"
                            onClick={() => startEdit(tx)}
                          >
                            {tx.categoria || "—"}
                            <Pencil className="ml-0.5 h-2.5 w-2.5 opacity-50" />
                          </Badge>
                          {tx.is_overridden && (
                            <span className="inline-flex items-center gap-0.5">
                              <Badge variant="secondary" className="h-4 px-1 text-[10px]">
                                editado
                              </Badge>
                              <button
                                onClick={() => removeOverride(tx.transaction_hash)}
                                className="text-muted-foreground hover:text-foreground"
                                title="Desfazer override"
                              >
                                <Undo2 className="h-3 w-3" />
                              </button>
                            </span>
                          )}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className={cn(
                      "text-right font-mono text-sm tabular-nums font-medium",
                      tx.valor >= 0 ? "text-gain" : "text-loss"
                    )}>
                      {formatCurrency(tx.valor, (tx.moeda === "USD" ? "USD" : "BRL"))}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {bankLabel(tx.banco)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {tx.titular || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {data.total.toLocaleString("pt-BR")} transação(ões) — página {page} de {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => goPage(page - 1)}
              >
                <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => goPage(page + 1)}
              >
                Próxima
                <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
