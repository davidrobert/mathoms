"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { Textarea } from "@/components/ui/textarea";

/**
 * Editor JSON D1 (textarea + JSON.parse no submit) — ADR-158.
 *
 * Decisão: D1 (textarea) ao invés de D2 (Monaco) para evitar bundle ~300KB
 * extra. v1 prioriza tornar a edição possível; UX pode evoluir em follow-up.
 *
 * Validação: client só checa se é JSON parseável (e expõe `isValid`/`parsed`
 * via `onChange`). NÃO valida contra schema do stage — re-validação é
 * responsabilidade do pipeline downstream (ADR-097), conforme regra
 * inegociável §8 do spec.
 */
export function JsonEditor({
  initialValue,
  onValidChange,
}: {
  initialValue: Record<string, unknown> | null;
  onValidChange: (parsed: Record<string, unknown> | null) => void;
}) {
  const [text, setText] = useState(() =>
    initialValue ? JSON.stringify(initialValue, null, 2) : "",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (text.trim() === "") {
      setError("JSON vazio");
      onValidChange(null);
      return;
    }
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setError("JSON precisa ser um objeto (não array, não primitivo)");
        onValidChange(null);
        return;
      }
      setError(null);
      onValidChange(parsed as Record<string, unknown>);
    } catch (e) {
      setError(e instanceof Error ? e.message : "JSON inválido");
      onValidChange(null);
    }
  }, [text, onValidChange]);

  const isInvalid = error !== null;

  return (
    <div className="space-y-2">
      <label
        htmlFor="json-editor-textarea"
        className="block text-sm font-medium text-foreground"
      >
        Editar output do stage
      </label>
      <Textarea
        id="json-editor-textarea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        aria-invalid={isInvalid}
        aria-describedby={isInvalid ? "json-editor-error" : "json-editor-hint"}
        spellCheck={false}
        rows={20}
        className="min-h-[40vh] font-mono text-xs leading-relaxed"
      />
      <p id="json-editor-hint" className="text-xs text-muted-foreground">
        Edição não validada — schema só será re-checado quando o pipeline
        retomar.
      </p>
      {isInvalid && (
        <p
          id="json-editor-error"
          role="alert"
          className="flex items-start gap-2 rounded-md border border-alert/40 bg-alert/5 p-2 text-xs text-alert"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>JSON inválido: {error}</span>
        </p>
      )}
    </div>
  );
}
