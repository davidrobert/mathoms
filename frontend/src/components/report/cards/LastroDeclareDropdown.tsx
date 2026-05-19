"use client";

// ADR-224 PR-E — dropdown inline para declarar lastro_moeda de um ativo.
// Compacto, sem modal — pattern de "quick action" inline em listas/tabelas.

import { useState } from "react";

import type { LastroMoeda, MatchKind } from "@/lib/api/exposicaoCambial";

const MOEDAS: { value: LastroMoeda; label: string }[] = [
  { value: "BRL", label: "BRL · Real" },
  { value: "USD", label: "USD · Dólar" },
  { value: "EUR", label: "EUR · Euro" },
  { value: "MIXED", label: "MIXED · multi-moeda" },
  { value: "OTHER", label: "OTHER · outra moeda" },
];

interface Props {
  ativoNome: string;
  matchKind: MatchKind;
  assetMatchKey: string;
  currentLastro: LastroMoeda;
  onDeclare: (lastro: LastroMoeda) => Promise<void>;
  onCancel: () => void;
  disabled?: boolean;
}

export function LastroDeclareDropdown({
  ativoNome,
  currentLastro,
  onDeclare,
  onCancel,
  disabled = false,
}: Props) {
  const [selected, setSelected] = useState<LastroMoeda>(currentLastro);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleConfirm = async () => {
    if (selected === currentLastro) {
      onCancel();
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await onDeclare(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar");
      setSubmitting(false);
    }
  };

  return (
    <div
      className="rounded-md border border-[var(--surface-border)] bg-[var(--surface-card)] p-3 text-sm"
      role="group"
      aria-label={`Declarar lastro de ${ativoNome}`}
    >
      <label className="block text-xs font-medium text-[var(--surface-muted-foreground)]">
        Lastro econômico de {ativoNome}
      </label>
      <select
        className="mt-1 w-full rounded border border-[var(--surface-border)] bg-[var(--surface-background)] px-2 py-1 font-mono"
        value={selected}
        disabled={disabled || submitting}
        onChange={(e) => setSelected(e.target.value as LastroMoeda)}
        aria-label="Selecione o lastro"
      >
        {MOEDAS.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="mt-1 text-xs text-[var(--semantic-danger)]" role="alert">
          {error}
        </p>
      )}
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          className="rounded bg-[var(--brand-primary)] px-2 py-1 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
          onClick={handleConfirm}
          disabled={disabled || submitting}
        >
          {submitting ? "Salvando…" : "Salvar"}
        </button>
        <button
          type="button"
          className="rounded border border-[var(--surface-border)] px-2 py-1 text-xs text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)]"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
