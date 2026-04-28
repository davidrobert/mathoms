"use client";

import { Suspense, useCallback, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/cn";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Spinner } from "@/components/Spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { TransactionListResponse } from "@/lib/api";
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
import { useTransactionsFetch } from "./_components/useTransactionsFetch";
import { useCategoriesAndMembers } from "./_components/useCategoriesAndMembers";
import { useCategoryOverride } from "./_components/useCategoryOverride";

const PAGE_SIZE = 50;

const EMPTY_FILTERS: FilterState = {
  bank: "",
  category: "",
  member: "",
  dateFrom: "",
  dateTo: "",
  valueMin: "",
  valueMax: "",
};

const FILTER_KEY_TO_FIELD: Record<FilterKey, keyof FilterState> = {
  bank: "bank",
  category: "category",
  member: "member",
  date_from: "dateFrom",
  date_to: "dateTo",
  value_min: "valueMin",
  value_max: "valueMax",
};

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

function buildUrlParams(
  search: string,
  filters: FilterState,
  page: number,
  overrides: Record<string, string | number | undefined>,
): URLSearchParams {
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
  return params;
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

function TransactionsEmptyState({
  hasActiveFilters,
  onClear,
}: {
  hasActiveFilters: boolean;
  onClear: () => void;
}) {
  return (
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
          ? { label: "Limpar filtros", onClick: onClear }
          : { label: "Ir para Pipeline", href: "/pipeline" }
      }
    />
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
  const [filtersOpen, setFiltersOpen] = useState(hasAnyFilter(initial, ""));
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { categories, members } = useCategoriesAndMembers(workspace!.id);
  const { data, loading, error, setError, fetchData } = useTransactionsFetch({
    workspaceId: workspace!.id,
    search,
    filters,
    page,
    pageSize: PAGE_SIZE,
  });
  const override = useCategoryOverride({
    workspaceId: workspace!.id,
    onAfterChange: fetchData,
    onError: setError,
  });

  const pushParams = useCallback(
    (overrides: Record<string, string | number | undefined>) => {
      const qs = buildUrlParams(search, filters, page, overrides).toString();
      router.replace(`/transactions${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [search, filters, page, router],
  );

  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      pushParams({ search: value, page: 1 });
    }, 300);
  }

  function applyFilter(key: FilterKey, value: string) {
    const field = FILTER_KEY_TO_FIELD[key];
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
    pushParams({ [key]: value, page: 1 });
  }

  function clearAllFilters() {
    setSearch("");
    setFilters(EMPTY_FILTERS);
    setPage(1);
    router.replace("/transactions", { scroll: false });
  }

  function goPage(p: number) {
    setPage(p);
    pushParams({ page: p });
  }

  function handleExport(format: "csv" | "xlsx") {
    exportTransactions(format, data?.transactions ?? [], search, filters);
  }

  const hasActiveFilters = hasAnyFilter(filters, search);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const categoryOptions = useMemo(() => {
    const fromConfig = categories.map((c) => c.code);
    const fromData = data?.transactions.map((t) => t.categoria) ?? [];
    return [...new Set([...fromConfig, ...fromData])].filter(Boolean).sort();
  }, [categories, data]);

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
        <TransactionsEmptyState
          hasActiveFilters={hasActiveFilters}
          onClear={clearAllFilters}
        />
      ) : (
        <>
          <TransactionsTable
            transactions={data.transactions}
            categoryOptions={categoryOptions}
            editingRowId={override.editingRowId}
            editCategory={override.editCategory}
            savingOverride={override.savingOverride}
            onStartEdit={override.startEdit}
            onCancelEdit={() => override.setEditingRowId(null)}
            onEditCategoryChange={override.setEditCategory}
            onSaveOverride={override.saveOverride}
            onRemoveOverride={override.clearOverride}
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
