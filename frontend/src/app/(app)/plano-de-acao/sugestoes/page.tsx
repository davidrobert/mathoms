"use client";

/**
 * /plano-de-acao/sugestoes — fila de sugestões do E5.N aguardando
 * aprovação humana (ADR-074).
 *
 * Cada card mostra o payload proposto (título, categoria, prioridade,
 * deadline) + 3 actions:
 *   - ✓ Aprovar 1-click (materializa Task)
 *   - ✗ Rejeitar (com motivo opcional)
 *   - ⌲ Mesclar em task existente (F9+: seletor de task alvo)
 *
 * Toggle de filtro: pending (default) | approved | rejected | merged.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Sparkles, X } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";

import { TaskPriorityChip } from "@/components/tasks/TaskPriorityChip";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  approveTaskSuggestion,
  listTaskSuggestions,
  rejectTaskSuggestion,
  ApiError,
  type SuggestionStatus,
  type TaskSuggestionResponse,
} from "@/lib/api";


const STATUS_LABEL: Record<SuggestionStatus, string> = {
  pending: "Pendentes",
  approved: "Aprovadas",
  rejected: "Rejeitadas",
  merged: "Mescladas",
};

const SOURCE_LABEL: Record<string, string> = {
  e5n_llm: "LLM (narrativas)",
  cross_validation: "Cross-validation",
  system_rule: "Regra do sistema",
};


export default function SugestoesPage() {
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const [items, setItems] = useState<TaskSuggestionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SuggestionStatus>("pending");
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const reload = useCallback(async () => {
    if (!workspace?.id) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await listTaskSuggestions(workspace.id, filter);
      setItems(resp.suggestions);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Erro ao carregar sugestões");
    } finally {
      setLoading(false);
    }
  }, [workspace?.id, filter]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleApprove(sugg: TaskSuggestionResponse) {
    if (!workspace?.id) return;
    setActingId(sugg.id);
    try {
      await approveTaskSuggestion(workspace.id, sugg.id);
      await reload();
    } catch (err) {
      if (err instanceof ApiError) alert(err.detail);
      else alert("Erro ao aprovar sugestão");
    } finally {
      setActingId(null);
    }
  }

  async function handleReject(sugg: TaskSuggestionResponse) {
    if (!workspace?.id) return;
    setActingId(sugg.id);
    try {
      await rejectTaskSuggestion(
        workspace.id,
        sugg.id,
        rejectReason.trim() || undefined
      );
      setRejectId(null);
      setRejectReason("");
      await reload();
    } catch (err) {
      if (err instanceof ApiError) alert(err.detail);
      else alert("Erro ao rejeitar sugestão");
    } finally {
      setActingId(null);
    }
  }

  if (wsLoading) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <Skeleton className="h-8 w-64" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <p className="text-muted-foreground">Nenhum workspace encontrado.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <PageHeader
        title="Sugestões do pipeline"
        description="Tarefas propostas pelo E5.N que aguardam sua aprovação"
        actions={
          <Button
            variant="ghost"
            size="sm"
            nativeButton={false}
            render={<Link href="/plano-de-acao" />}
          >
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Voltar
          </Button>
        }
      />

      {/* Filter toggle */}
      <div className="mb-6 flex gap-1 rounded-lg bg-muted p-1 text-sm">
        {(["pending", "approved", "rejected", "merged"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            className={
              "flex-1 rounded px-3 py-1.5 transition " +
              (filter === s
                ? "bg-background font-medium shadow-sm"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {error && (
        <Card className="mb-6 border-destructive/40">
          <CardContent className="py-4 text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Sparkles className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">
              Nenhuma sugestão {STATUS_LABEL[filter].toLowerCase()}.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {filter === "pending"
                ? "Sugestões aparecem aqui após o E5.N rodar."
                : null}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((sugg) => (
            <SuggestionCard
              key={sugg.id}
              sugg={sugg}
              isActing={actingId === sugg.id}
              onApprove={() => handleApprove(sugg)}
              onStartReject={() => {
                setRejectId(sugg.id);
                setRejectReason("");
              }}
              onCancelReject={() => {
                setRejectId(null);
                setRejectReason("");
              }}
              onConfirmReject={() => handleReject(sugg)}
              showingReject={rejectId === sugg.id}
              rejectReason={rejectReason}
              onRejectReasonChange={setRejectReason}
            />
          ))}
        </div>
      )}
    </div>
  );
}


// ─── SuggestionCard ────────────────────────────────────────────────────


interface SuggestionCardProps {
  sugg: TaskSuggestionResponse;
  isActing: boolean;
  onApprove: () => void;
  onStartReject: () => void;
  onCancelReject: () => void;
  onConfirmReject: () => void;
  showingReject: boolean;
  rejectReason: string;
  onRejectReasonChange: (v: string) => void;
}


function SuggestionCard({
  sugg,
  isActing,
  onApprove,
  onStartReject,
  onCancelReject,
  onConfirmReject,
  showingReject,
  rejectReason,
  onRejectReasonChange,
}: SuggestionCardProps) {
  const p = sugg.proposed_payload;
  const isPending = sugg.status === "pending";

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="h-3 w-3" />
              <span>{SOURCE_LABEL[sugg.source] ?? sugg.source}</span>
              <span>·</span>
              <span>
                {new Date(sugg.created_at).toLocaleDateString("pt-BR")}
              </span>
              {sugg.status !== "pending" && (
                <Badge variant="outline" className="ml-1">
                  {STATUS_LABEL[sugg.status]}
                </Badge>
              )}
            </div>

            <h3 className="mt-2 text-sm font-medium">{p.title}</h3>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <TaskPriorityChip priority={p.priority} />
              <Badge variant="outline">{p.category}</Badge>
              {p.deadline_label && (
                <span className="text-xs text-muted-foreground">
                  {p.deadline_label}
                </span>
              )}
            </div>

            {p.description && (
              <p className="mt-2 text-xs text-muted-foreground">
                {String(p.description)}
              </p>
            )}

            {sugg.status === "rejected" && sugg.rejection_reason && (
              <p className="mt-2 text-xs italic text-muted-foreground">
                Motivo: {sugg.rejection_reason}
              </p>
            )}
          </div>

          {isPending && (
            <div className="flex shrink-0 gap-1">
              <Button
                size="sm"
                variant="default"
                onClick={onApprove}
                disabled={isActing}
                aria-label="Aprovar sugestão"
              >
                <Check className="mr-1 h-3.5 w-3.5" />
                Aprovar
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={onStartReject}
                disabled={isActing}
                aria-label="Rejeitar sugestão"
              >
                <X className="mr-1 h-3.5 w-3.5" />
                Rejeitar
              </Button>
            </div>
          )}
        </div>

        {/* Inline form de motivo de rejeição */}
        {showingReject && (
          <div className="mt-3 flex items-center gap-2 rounded-md bg-muted/50 p-3">
            <Input
              placeholder="Motivo (opcional)"
              value={rejectReason}
              onChange={(e) => onRejectReasonChange(e.target.value)}
              maxLength={1000}
              className="flex-1"
              autoFocus
            />
            <Button
              size="sm"
              variant="destructive"
              onClick={onConfirmReject}
              disabled={isActing}
            >
              Confirmar
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onCancelReject}
              disabled={isActing}
            >
              Cancelar
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
