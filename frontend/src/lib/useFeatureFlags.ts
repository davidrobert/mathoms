"use client";

/**
 * useFeatureFlags — lê ``/workspaces/{ws}/feature-flags`` 1× e expõe map.
 *
 * Uso:
 *   const { flags, isEnabled } = useFeatureFlags(workspaceId);
 *   if (isEnabled("learning_loop_enabled")) { ... }
 *
 * Não-disruptivo: durante loading, ``isEnabled`` retorna ``false`` — UI
 * condicional simplesmente não renderiza até flags chegarem.
 */
import { useCallback, useEffect, useState } from "react";

import { getFeatureFlags } from "./api/feature-flags";

interface FeatureFlagsState {
  flags: Record<string, boolean>;
  isLoading: boolean;
  error: Error | null;
  isEnabled: (name: string) => boolean;
  refresh: () => Promise<void>;
}

async function fetchFlags(
  workspaceId: string,
  setFlags: (f: Record<string, boolean>) => void,
  setError: (e: Error | null) => void,
): Promise<void> {
  try {
    const resp = await getFeatureFlags(workspaceId);
    setFlags(resp.flags ?? {});
    setError(null);
  } catch (err) {
    setError(err instanceof Error ? err : new Error(String(err)));
  }
}

export function useFeatureFlags(workspaceId: string | undefined): FeatureFlagsState {
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const load = useCallback(async () => {
    if (!workspaceId) return setIsLoading(false);
    setIsLoading(true);
    await fetchFlags(workspaceId, setFlags, setError);
    setIsLoading(false);
  }, [workspaceId]);
  useEffect(() => {
    load();
  }, [load]);
  const isEnabled = useCallback((name: string) => Boolean(flags[name]), [flags]);
  return { flags, isLoading, error, isEnabled, refresh: load };
}
