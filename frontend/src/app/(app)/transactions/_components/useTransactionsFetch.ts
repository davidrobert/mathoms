"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  listTransactions,
  type TransactionListResponse,
  ApiError,
} from "@/lib/api";
import type { FilterState } from "./FiltersPanel";

export type TransactionSort = "data_desc" | "valor_desc";

interface FetchArgs {
  workspaceId: string;
  search: string;
  filters: FilterState;
  page: number;
  pageSize: number;
  sort: TransactionSort;
}

function toApiParams(args: FetchArgs) {
  const { search, filters, page, pageSize, sort } = args;
  return {
    search: search || undefined,
    bank: filters.bank || undefined,
    category: filters.category || undefined,
    member: filters.member || undefined,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
    value_min: filters.valueMin ? Number(filters.valueMin) : undefined,
    value_max: filters.valueMax ? Number(filters.valueMax) : undefined,
    page,
    page_size: pageSize,
    sort: sort === "data_desc" ? undefined : sort,
  };
}

export function useTransactionsFetch(args: FetchArgs) {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const fetchData = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    try {
      const result = await listTransactions(args.workspaceId, toApiParams(args));
      if (!controller.signal.aborted) setData(result);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof ApiError ? err.detail : "Erro ao carregar transações");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [args.workspaceId, args.search, args.filters, args.page, args.pageSize, args.sort]);

  useEffect(() => {
    fetchData();
    return () => abortRef.current?.abort();
  }, [fetchData]);

  return { data, loading, error, setError, fetchData };
}
