"use client";

import { useId } from "react";

/**
 * Read-only JSON tree viewer.
 *
 * Renderiza `value` como JSON formatado em um <pre>, com `data-json-path`
 * em cada elemento para permitir scroll-into-view a partir de
 * ValidationErrorsPanel (heurística leve, melhor esforço — ADR-158).
 *
 * Não usa lib externa (zero deps) — JSON.stringify(..., 2) basta para v1.
 * Highlight de campos com erro é via `errorPaths` (Set de strings normalizadas).
 */
export function JsonViewer({
  value,
  errorPaths,
}: {
  value: Record<string, unknown> | null;
  errorPaths?: Set<string>;
}) {
  const fallbackId = useId();
  if (value === null || value === undefined) {
    return (
      <pre
        aria-label="Output original vazio"
        className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground"
      >
        (sem output)
      </pre>
    );
  }

  const pretty = JSON.stringify(value, null, 2);
  return (
    <pre
      id={`json-viewer-${fallbackId}`}
      aria-label="Output original do stage"
      className="max-h-[60vh] overflow-auto rounded-lg border border-border bg-muted/30 p-3 font-mono text-xs leading-relaxed text-foreground"
    >
      {highlightLines(pretty, errorPaths)}
    </pre>
  );
}

/**
 * Heurística para destacar linhas que mencionam paths em `errorPaths`.
 * Não é AST-aware — splita por linha e marca linhas que contêm `"<path>":`.
 * Falsos negativos toleráveis (highlight é hint, não fonte de verdade).
 */
function highlightLines(
  text: string,
  errorPaths: Set<string> | undefined,
): React.ReactNode {
  if (!errorPaths || errorPaths.size === 0) return text;
  const lines = text.split("\n");
  return lines.map((line, idx) => (
    <HighlightedLine
      key={idx}
      line={line}
      isLast={idx === lines.length - 1}
      errorPaths={errorPaths}
    />
  ));
}

function HighlightedLine({
  line,
  isLast,
  errorPaths,
}: {
  line: string;
  isLast: boolean;
  errorPaths: Set<string>;
}) {
  const match = /"([^"]+)"\s*:/.exec(line);
  const key = match?.[1];
  const isError = key !== undefined && errorPaths.has(key);
  return (
    <span
      data-json-path={key}
      className={isError ? "block bg-alert/10 text-alert" : "block"}
    >
      {line}
      {!isLast ? "\n" : ""}
    </span>
  );
}
