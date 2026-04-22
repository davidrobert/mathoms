"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { cn } from "@/lib/cn";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  ChevronUp,
  FileDown,
  FileSpreadsheet,
  Filter,
  Search,
  X,
} from "lucide-react";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { FiltersPanel, type FilterKey, type FilterState } from "./_components/FiltersPanel";
import { SummaryBar } from "./_components/SummaryBar";
import { TransactionsTable } from "./_components/TransactionsTable";
import { Pagination } from "./_components/Pagination";
import { exportTransactions } from "./_components/exportTransactions";

const PAGE_SIZE = 50;

export default function TransactionsPage() {
  const { workspace } = useWorkspace();
  if (!workspace) return null;

  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-24">
          <Spinner size="lg" />
        </div>
      }
    >
      <TransactionsContent />
    </Suspense>
  );
}

function readInitialFilters(searchParams: URLSearchParams): FilterState {
  return {
    bank: searchParams.get("bank") ?? "",
    category: searchParams.get("category") ?? "",
    member: searchParams.get("member") ?? "",
    dateFrom: searchParams.get("date_from") ?? "",
    dateTo: searchParams.get("date_to") ?? "",
    valueMin: searchParams.get("value_min") ?? "",
    valueMax: searchParams.get("value_max") ?? "",
  };
}

function hasAnyFilter(state: FilterState, search: string) {
  return !!(
    search ||
    state.bank ||
    state.category ||
    state.member ||
    state.dateFrom ||
    state.dateTo ||
    state.valueMin ||
    state.valueMax
  );
}

function ExportActions({
  data,
  onExport,
}: {
  data: TransactionListResponse | null;
  onExport: (format: "csv" | "xlsx") => void;
}) {
  const disabled = !data?.transactions.length;
  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" disabled={disabled} onClick={() => onExport("csv")}>
        <FileDown className="mr-1.5 h-3.5 w-3.5" />
        CSV
      </Button>
      <Button variant="outline" size="sm" disabled={disabled} onClick={() => onExport("xlsx")}>
        <FileSpreadsheet className="mr-1.5 h-3.5 w-3.5" />
        XLSX
      </Button>
    </div>
  );
}

function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative mb-4">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder="Buscar por descrição, banco, categoria..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-9 pr-9"
      />
      {value && (
        <button
          onClick={() => onChange("")}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

function FilterToggleBar({
  filters,
  hasActiveFilters,
  filtersOpen,
  onToggle,
  onClear,
}: {
  filters: FilterState;
  hasActiveFilters: boolean;
  filtersOpen: boolean;
  onToggle: () => void;
  onClear: () => void;
}) {
  const active = [
    filters.bank,
    filters.category,
    filters.member,
    filters.dateFrom,
    filters.dateTo,
    filters.valueMin,
    filters.valueMax,
  ].filter(Boolean).length;
  return (
    <div className="mb-4 flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={onToggle}
        className={cn(hasActiveFilters && "border-primary text-primary")}
      >
        <Filter className="mr-1.5 h-3.5 w-3.5" />
        Filtros
        {hasActiveFilters && (
          <Badge variant="default" className="ml-1.5 h-4 min-w-4 px-1 text-[10px]">
            {active}
          </Badge>
        )}
        {filtersOpen ? (
          <ChevronUp className="ml-1 h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="ml-1 h-3.5 w-3.5" />
        )}
      </Button>
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="mr-1 h-3.5 w-3.5" />
          Limpar filtros
        </Button>
      )}
    </div>
  );
}

function TransactionsContent() {
  const { workspace } = useWorkspace();
  const router = useRouter();
  const searchParams = useSearchParams();

  const initial = readInitialFilters(searchParams);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [page, setPage] = useState(Number(searchParams.get("page") ?? "1"));
  const [filters, setFilters] = useState<FilterState>(initial);

  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(hasAnyFilter(initial, ""));

  const [categories, setCategories] = useState<CategoryConfig[]>([]);
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);

  const [editingHash, setEditingHash] = useState<string | null>(null);
  const [editCategory, setEditCategory] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listCategories(workspace!.id).then((r) => setCategories(r.categories)).catch(() => {});
    listMembers(workspace!.id).then((r) => setMembers(r.members)).catch(() => {});
  }, [workspace]);

  const pushParams = useCallback(
    (overrides: Record<string, string | number | undefined>) => {
      const params = new URLSearchParams();
      const merged: Record<string, string | number | undefined> = {
        search,
        bank: filters.bank,
        category: filters.category,
        member: filters.member,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        value_min: filters.valueMin,
        value_max: filters.valueMax,
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
    [search, filters, page, router],
  );

  const fetchData = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    try {
      const result = await listTransactions(workspace!.id, {
        search: search || undefined,
        bank: filters.bank || undefined,
        category: filters.category || undefined,
        member: filters.member || undefined,
        date_from: filters.dateFrom || undefined,
        date_to: filters.dateTo || undefined,
        value_min: filters.valueMin ? Number(filters.valueMin) : undefined,
        value_max: filters.valueMax ? Number(filters.valueMax) : undefined,
        page,
        page_size: PAGE_SIZE,
      });
      if (!controller.signal.aborted) setData(result);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof ApiError ? err.detail : "Erro ao carregar transações");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [search, filters, page, workspace]);

  useEffect(() => {
    fetchData();
    return () => abortRef.current?.abort();
  }, [fetchData]);

  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      pushParams({ search: value, page: 1 });
    }, 300);
  }

  const filterKeyToField: Record<FilterKey, keyof FilterState> = {
    bank: "bank",
    category: "category",
    member: "member",
    date_from: "dateFrom",
    date_to: "dateTo",
    value_min: "valueMin",
    value_max: "valueMax",
  };

  function applyFilter(key: FilterKey, value: string) {
    const field = filterKeyToField[key];
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
    pushParams({ [key]: value, page: 1 });
  }

  function clearAllFilters() {
    setSearch("");
    setFilters({
      bank: "",
      category: "",
      member: "",
      dateFrom: "",
      dateTo: "",
      valueMin: "",
      valueMax: "",
    });
    setPage(1);
    router.replace("/transactions", { scroll: false });
  }

  const hasActiveFilters = hasAnyFilter(filters, search);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function goPage(p: number) {
    setPage(p);
    pushParams({ page: p });
  }

  function startEdit(tx: TransactionItem) {
    setEditingHash(tx.transaction_hash);
    setEditCategory(tx.categoria);
  }

  async function saveOverride(hash: string) {
    if (!editCategory) return;
    setSavingOverride(true);
    try {
      await overrideTransactionCategory(workspace!.id, hash, { new_category: editCategory });
      setEditingHash(null);
      await fetchData();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao salvar override");
    } finally {
      setSavingOverride(false);
    }
  }

  async function removeOverride(hash: string) {
    setSavingOverride(true);
    try {
      await removeTransactionOverride(workspace!.id, hash);
      await fetchData();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erro ao remover override");
    } finally {
      setSavingOverride(false);
    }
  }

  const categoryOptions = useMemo(() => {
    const fromConfig = categories.map((c) => c.code);
    const fromData = data?.transactions.map((t) => t.categoria) ?? [];
    return [...new Set([...fromConfig, ...fromData])].filter(Boolean).sort();
  }, [categories, data]);

  function handleExport(format: "csv" | "xlsx") {
    exportTransactions(format, data?.transactions ?? [], search, filters);
  }

  const summary = data?.summary;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <PageHeader
        title="Transações"
        description="Explore e gerencie todas as transações financeiras"
        actions={<ExportActions data={data} onExport={handleExport} />}
      />

      <SearchBar value={search} onChange={handleSearchChange} />
      <FilterToggleBar
        filters={filters}
        hasActiveFilters={hasActiveFilters}
        filtersOpen={filtersOpen}
        onToggle={() => setFiltersOpen(!filtersOpen)}
        onClear={clearAllFilters}
      />
      {filtersOpen && (
        <FiltersPanel
          state={filters}
          categoryOptions={categoryOptions}
          members={members}
          onApply={applyFilter}
        />
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-loss/10 p-3 text-sm text-loss">
          {error}
          <button onClick={() => setError("")} className="ml-2 font-medium underline">
            fechar
          </button>
        </div>
      )}

      {summary && data && data.transactions.length > 0 && <SummaryBar summary={summary} />}

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
          <TransactionsTable
            transactions={data.transactions}
            categoryOptions={categoryOptions}
            editingHash={editingHash}
            editCategory={editCategory}
            savingOverride={savingOverride}
            onStartEdit={startEdit}
            onCancelEdit={() => setEditingHash(null)}
            onEditCategoryChange={setEditCategory}
            onSaveOverride={saveOverride}
            onRemoveOverride={removeOverride}
          />
          <Pagination
            total={data.total}
            page={page}
            totalPages={totalPages}
            onGoPage={goPage}
          />
        </>
      )}
    </div>
  );
}
