"use client";

// ADR-259 §4 — CPF mascarado por padrão; "Ver completo" decripta sob demanda
// (owner-only) e é auditado no backend. Mesma política do relatório
// (`components/report/ui/CpfField.tsx`), reskinada em Tailwind/shadcn para
// combinar com o resto de `config/` — os dois consomem os mesmos endpoints
// `GET .../cpf` (masked, já embutido em `listMembers`) e `GET .../cpf/full`.

import { useState } from "react";
import { AlertTriangle, Eye, EyeOff, Loader2 } from "lucide-react";

import { ApiError, getMemberCpfFull } from "@/lib/api";

type State = "idle" | "loading" | "revealed" | "error";

export interface CpfMaskedFieldProps {
  readonly workspaceId: string;
  readonly memberId: string;
  readonly memberName: string;
  /** `null` = sem CPF cadastrado. */
  readonly cpfMasked: string | null;
  /** Deriva de `workspace.role === "owner"` no call-site. */
  readonly canReveal: boolean;
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 429) {
    return "Muitas consultas seguidas. Aguarde um instante e tente de novo.";
  }
  return "Não conseguimos exibir o número agora. Tente de novo.";
}

export function CpfMaskedField({ workspaceId, memberId, memberName, cpfMasked, canReveal }: CpfMaskedFieldProps) {
  const [state, setState] = useState<State>("idle");
  const [cpfFull, setCpfFull] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reveal() {
    setState("loading");
    setError(null);
    try {
      const { cpf_full } = await getMemberCpfFull(workspaceId, memberId);
      setCpfFull(cpf_full);
      setState("revealed");
    } catch (err) {
      setError(errorMessage(err));
      setState("error");
    }
  }

  function hide() {
    setCpfFull(null);
    setState("idle");
  }

  if (cpfMasked === null) {
    return <span className="text-muted-foreground">—</span>;
  }

  const revealed = state === "revealed" && cpfFull;
  const value = revealed ? cpfFull : cpfMasked;
  const valueLabel = revealed
    ? `CPF completo: ${cpfFull}`
    : `CPF parcialmente oculto, terminando em ${cpfMasked.slice(-6)}`;

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span aria-label={valueLabel} className="font-mono tabular-nums">
        {value}
      </span>

      {canReveal && state === "idle" && (
        <button
          type="button"
          onClick={reveal}
          aria-label={`Ver CPF completo de ${memberName}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
        >
          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
          Ver completo
        </button>
      )}

      {canReveal && revealed && (
        <button
          type="button"
          onClick={hide}
          aria-label={`Ocultar CPF de ${memberName}`}
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
        >
          <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
          Ocultar
        </button>
      )}

      {state === "loading" && (
        <span role="status" aria-busy="true" className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          Verificando…
        </span>
      )}

      {state === "error" && (
        <span role="alert" className="inline-flex items-center gap-1 text-xs text-[var(--brand-warning)]">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
          {error}
          <button type="button" onClick={reveal} className="font-semibold underline">
            Tentar de novo
          </button>
        </span>
      )}
    </span>
  );
}
