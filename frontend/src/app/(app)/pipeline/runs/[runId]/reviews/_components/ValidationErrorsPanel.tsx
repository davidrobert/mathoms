"use client";

import { AlertTriangle } from "lucide-react";

/**
 * Lista os erros de schema do StageReview.
 *
 * `validation_errors` chega como string single-line ou multi-line do backend.
 * Quebramos por `\n` e renderizamos como bullets. Cada bullet é clicável e
 * dispara `onErrorClick(path)` quando consegue extrair um path no formato
 * `field` ou `$.path.to.field` (heurística leve, melhor esforço — ADR-158).
 */
export function ValidationErrorsPanel({
  errors,
  onErrorClick,
}: {
  errors: string | null;
  onErrorClick?: (path: string) => void;
}) {
  if (!errors || errors.trim() === "") {
    return (
      <p className="text-sm text-muted-foreground">
        Sem erros de validação registrados.
      </p>
    );
  }
  const lines = errors
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  return (
    <ul aria-label="Erros de validação" className="space-y-2">
      {lines.map((line, idx) => {
        const path = extractPath(line);
        const clickable = path !== null && onErrorClick !== undefined;
        return (
          <li
            key={idx}
            className="flex items-start gap-2 rounded-md border border-alert/40 bg-alert/5 p-2 text-xs text-foreground"
          >
            <AlertTriangle
              aria-hidden
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-alert"
            />
            {clickable ? (
              <button
                type="button"
                onClick={() => onErrorClick(path)}
                className="text-left hover:underline focus-visible:underline"
              >
                {line}
              </button>
            ) : (
              <span>{line}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Extrai um nome de campo da mensagem de erro. Tenta:
 * 1. `$.path.field` (jsonpath) → retorna last segment.
 * 2. `field 'name'` ou `field "name"` → retorna `name`.
 * 3. `name:` no começo da linha → retorna `name`.
 *
 * Retorna null se nenhum padrão bate (highlight não vai funcionar — ok,
 * é hint visual, não load-bearing).
 */
function extractPath(message: string): string | null {
  const jp = /\$\.([\w.[\]]+)/.exec(message);
  if (jp?.[1]) {
    const segs = jp[1].split(".");
    const last = segs[segs.length - 1];
    return last ? last.replace(/\[\d+\]/g, "") : null;
  }
  const quoted = /['"]([\w_]+)['"]/.exec(message);
  if (quoted?.[1]) return quoted[1];
  const prefix = /^([\w_]+):/.exec(message);
  if (prefix?.[1]) return prefix[1];
  return null;
}

/** Helper exportado p/ teste — extrai o set de paths para passar ao viewer. */
export function extractErrorPaths(errors: string | null): Set<string> {
  if (!errors) return new Set();
  const out = new Set<string>();
  for (const line of errors.split("\n")) {
    const p = extractPath(line.trim());
    if (p) out.add(p);
  }
  return out;
}
