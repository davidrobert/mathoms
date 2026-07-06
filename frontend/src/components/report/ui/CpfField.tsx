"use client";

import { useRef, useState, type CSSProperties } from "react";
import { AlertTriangle, Eye, EyeOff, Loader2 } from "lucide-react";

import { ApiError, getMemberCpfFull } from "@/lib/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { useIsPrint } from "../hooks/useIsPrint";

type FieldState = "idle" | "loading" | "revealed" | "error";

export interface CpfFieldProps {
  readonly workspaceId: string;
  readonly memberId: string;
  readonly memberName: string;
  /** Máscara pronta do servidor (`***.***.789-00`); `null` = sem CPF cadastrado. */
  readonly cpfMasked: string | null;
  /** Deriva de `role === "owner"` no call-site — o componente não resolve role. */
  readonly canReveal: boolean;
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 429) {
    return "Muitas consultas seguidas. Aguarde um instante e tente de novo.";
  }
  return "Não conseguimos exibir o número agora. Tente de novo.";
}

/** ADR-259 §4 — CPF mascarado por padrão; "Ver completo" decripta sob demanda
 * (owner-only) e é auditado no backend. Nunca mascara localmente: recebe
 * `cpfMasked` pronto e só busca o valor completo ao clique. */
export function CpfField({ workspaceId, memberId, memberName, cpfMasked, canReveal }: CpfFieldProps) {
  const [state, setState] = useState<FieldState>("idle");
  const [cpfFull, setCpfFull] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hideButtonRef = useRef<HTMLButtonElement>(null);
  const isPrint = useIsPrint();

  async function reveal() {
    setState("loading");
    setError(null);
    try {
      const { cpf_full } = await getMemberCpfFull(workspaceId, memberId);
      setCpfFull(cpf_full);
      setState("revealed");
      hideButtonRef.current?.focus();
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
    return <span style={{ color: "var(--surface-muted-foreground)" }}>—</span>;
  }

  const showRevealed = state === "revealed" && !isPrint;
  const displayValue = showRevealed && cpfFull ? cpfFull : cpfMasked;
  const valueLabel = showRevealed
    ? `CPF completo: ${cpfFull}`
    : `CPF parcialmente oculto, terminando em ${cpfMasked.slice(-6)}`;

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <span
        aria-label={valueLabel}
        style={{ fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}
      >
        {displayValue}
      </span>

      {canReveal && showRevealed && (
        <button
          ref={hideButtonRef}
          type="button"
          onClick={hide}
          aria-label={`Ocultar CPF de ${memberName}`}
          style={linkButtonStyle}
        >
          <EyeOff size={14} aria-hidden="true" />
          Ocultar
        </button>
      )}

      {canReveal && !isPrint && state === "idle" && (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
          <button
            type="button"
            onClick={reveal}
            aria-label={`Ver CPF completo de ${memberName}`}
            style={linkButtonStyle}
          >
            <Eye size={14} aria-hidden="true" />
            Ver completo
          </button>
          <InfoTooltip
            ariaLabel="Sobre a exibição do CPF completo"
            content="Cada vez que o número completo é exibido, registramos o acesso — data, hora e responsável. O registro protege os dados da família."
          />
        </span>
      )}

      {state === "loading" && (
        <span role="status" aria-busy="true" style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--surface-muted-foreground)" }}>
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Verificando…
        </span>
      )}

      {state === "error" && (
        <span role="alert" style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--brand-warning)" }}>
          <AlertTriangle size={14} aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={reveal} style={linkButtonStyle}>
            Tentar de novo
          </button>
        </span>
      )}
    </span>
  );
}

const linkButtonStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  background: "none",
  border: "none",
  padding: 0,
  color: "var(--brand-primary)",
  fontSize: "var(--report-font-size-sm, 12px)",
  fontWeight: 600,
  cursor: "pointer",
};
