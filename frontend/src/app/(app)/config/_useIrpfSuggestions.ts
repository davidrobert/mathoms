"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  ApiError,
  createBankAccount,
  dismissIrpfSuggestion,
  listIrpfSuggestions,
  type BankAccountConfig,
  type FamilyMemberConfig,
  type IrpfSuggestion,
} from "@/lib/api";
import { useFeatureFlags } from "@/lib/useFeatureFlags";
import { bankLabel } from "@/lib/format";

import type { DiffResolution } from "./_IrpfDiffModal";

interface PendingCollision {
  suggestion: IrpfSuggestion;
  collision: BankAccountConfig;
  memberId: string;
}

interface UseIrpfSuggestionsResult {
  enabled: boolean;
  busy: boolean;
  suggestionsByMember: Map<string, IrpfSuggestion[]>;
  pendingCollision: PendingCollision | null;
  accept: (s: IrpfSuggestion) => Promise<void>;
  dismiss: (s: IrpfSuggestion) => Promise<void>;
  resolveCollision: (resolution: DiffResolution) => Promise<void>;
  cancelCollision: () => void;
}

async function _createFromSuggestion(
  workspaceId: string,
  memberId: string,
  s: IrpfSuggestion,
): Promise<void> {
  await createBankAccount(workspaceId, memberId, {
    institution_code: s.institution_code,
    account_type: s.account_type,
    agency: s.agency ?? undefined,
    account_number: s.account_number_raw ?? s.account_number_norm ?? undefined,
    origem_irpf: true,
    origem_irpf_year: s.irpf_year,
  });
}

function _toastAccepted(s: IrpfSuggestion, suffix = "") {
  toast.success(
    `Conta ${bankLabel(s.institution_code)} adicionada${suffix} · Origem: IRPF ${s.irpf_year}`,
    { duration: 10_000 },
  );
}

function _groupByMember(items: IrpfSuggestion[]): Map<string, IrpfSuggestion[]> {
  const map = new Map<string, IrpfSuggestion[]>();
  for (const s of items) {
    const arr = map.get(s.member_key) ?? [];
    arr.push(s);
    map.set(s.member_key, arr);
  }
  return map;
}

interface _Ctx {
  workspaceId: string;
  members: FamilyMemberConfig[];
  setBusy: (v: boolean) => void;
  setPending: (v: PendingCollision | null) => void;
  reload: () => Promise<void>;
  onError: (msg: string) => void;
  onMembersInvalidate: () => Promise<void>;
}

function _msgFromErr(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.detail : fallback;
}

function _interceptCollision(s: IrpfSuggestion, ctx: _Ctx): boolean {
  if (s.match_kind !== "partial_collision") return false;
  const member = ctx.members.find((m) => m.key === s.member_key);
  const collision = member?.accounts.find((a) => a.id === s.collision_with_account_id);
  if (member?.id && collision) {
    ctx.setPending({ suggestion: s, collision, memberId: member.id });
    return true;
  }
  return false;
}

async function _runAccept(s: IrpfSuggestion, ctx: _Ctx): Promise<void> {
  const member = ctx.members.find((m) => m.key === s.member_key);
  if (!member?.id) {
    ctx.onError(`Não foi possível identificar o membro "${s.member_key}".`);
    return;
  }
  if (_interceptCollision(s, ctx)) return;
  ctx.setBusy(true);
  try {
    await _createFromSuggestion(ctx.workspaceId, member.id, s);
    _toastAccepted(s);
    await Promise.all([ctx.onMembersInvalidate(), ctx.reload()]);
  } catch (err) {
    ctx.onError(_msgFromErr(err, "Erro ao adicionar conta sugerida"));
  } finally {
    ctx.setBusy(false);
  }
}

async function _runDismiss(s: IrpfSuggestion, ctx: _Ctx): Promise<void> {
  ctx.setBusy(true);
  try {
    await dismissIrpfSuggestion(ctx.workspaceId, {
      irpf_year: s.irpf_year,
      institution_code: s.institution_code,
      account_number_norm: s.account_number_norm,
      member_key: s.member_key,
    });
    toast.success("Sugestão descartada", { duration: 5_000 });
    await ctx.reload();
  } catch (err) {
    ctx.onError(_msgFromErr(err, "Erro ao descartar sugestão"));
  } finally {
    ctx.setBusy(false);
  }
}

async function _runCreateSeparate(p: PendingCollision, ctx: _Ctx): Promise<void> {
  ctx.setBusy(true);
  try {
    await _createFromSuggestion(ctx.workspaceId, p.memberId, p.suggestion);
    _toastAccepted(p.suggestion, " como separada");
    await Promise.all([ctx.onMembersInvalidate(), ctx.reload()]);
  } catch (err) {
    ctx.onError(_msgFromErr(err, "Erro ao adicionar conta separada"));
  } finally {
    ctx.setBusy(false);
  }
}

async function _runResolve(
  r: DiffResolution,
  p: PendingCollision | null,
  ctx: _Ctx,
): Promise<void> {
  if (!p) return;
  ctx.setPending(null);
  if (r === "merge") return _runDismiss(p.suggestion, ctx);
  return _runCreateSeparate(p, ctx);
}

function useIrpfReload(workspaceId: string, enabled: boolean, setItems: (v: IrpfSuggestion[]) => void) {
  return useCallback(async () => {
    if (!enabled) return setItems([]);
    try {
      const resp = await listIrpfSuggestions(workspaceId);
      setItems(resp.suggestions);
    } catch {
      setItems([]);
    }
  }, [enabled, workspaceId, setItems]);
}

export function useIrpfSuggestions(
  workspaceId: string,
  members: FamilyMemberConfig[],
  onMembersInvalidate: () => Promise<void>,
  onError: (msg: string) => void,
): UseIrpfSuggestionsResult {
  const { isEnabled } = useFeatureFlags(workspaceId);
  const enabled = isEnabled("irpf_prefill_enabled");
  const [items, setItems] = useState<IrpfSuggestion[]>([]);
  const [busy, setBusy] = useState(false);
  const [pendingCollision, setPendingCollision] = useState<PendingCollision | null>(null);
  const reload = useIrpfReload(workspaceId, enabled, setItems);
  useEffect(() => {
    reload();
  }, [reload]);
  const ctx: _Ctx = {
    workspaceId, members, setBusy,
    setPending: setPendingCollision, reload, onError, onMembersInvalidate,
  };
  const accept = useCallback((s: IrpfSuggestion) => _runAccept(s, ctx), [ctx]);
  const dismiss = useCallback((s: IrpfSuggestion) => _runDismiss(s, ctx), [ctx]);
  const resolveCollision = useCallback(
    (r: DiffResolution) => _runResolve(r, pendingCollision, ctx),
    [pendingCollision, ctx],
  );
  const cancelCollision = useCallback(() => setPendingCollision(null), []);
  const suggestionsByMember = useMemo(() => _groupByMember(items), [items]);
  return {
    enabled, busy, suggestionsByMember, pendingCollision,
    accept, dismiss, resolveCollision, cancelCollision,
  };
}
