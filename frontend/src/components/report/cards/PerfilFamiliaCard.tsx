import { ReportCard } from "../ReportCard";

interface PerfilEntry {
  // Onda R2 (PD-01): o narrador emite `left`/`right` (2 colunas, HTML de parágrafos).
  // O contrato antigo `context`/`conclusion` nunca casava → o card renderizava null.
  left?: string;
  right?: string;
}

interface PerfilFamiliaCardProps {
  narrativas: Record<string, unknown> | undefined;
}

/** Quebra o HTML de parágrafos (`<p>…</p>`) do narrador em texto, sem
 *  dangerouslySetInnerHTML (precedente zero-HTML-injection do relatório). */
function parseParagraphs(html?: string): string[] {
  if (!html) return [];
  return html
    .split(/<\/p>/i)
    .map((chunk) => chunk.replace(/<[^>]*>/g, "").trim())
    .filter(Boolean);
}

/** F9 · Fase D — Card "Perfil da Família".
 *  Exibe a apresentação narrativa da família (2 colunas) do E5 JSON.
 *  Renderiza nada se não houver narrativa de perfil.
 */
export function PerfilFamiliaCard({ narrativas }: PerfilFamiliaCardProps) {
  const perfil = narrativas?.["perfil_familia"] as PerfilEntry | undefined;
  const colunas = [parseParagraphs(perfil?.left), parseParagraphs(perfil?.right)];

  if (colunas.every((c) => c.length === 0)) return null;

  return (
    <ReportCard variant="feature" title="A Família">
      <div className="grid gap-4 md:grid-cols-2">
        {colunas.map((coluna, i) =>
          coluna.length > 0 ? (
            <div key={i} className="flex flex-col gap-2">
              {coluna.map((paragrafo, j) => (
                <p
                  key={j}
                  className="text-sm leading-relaxed text-[var(--surface-foreground)]"
                >
                  {paragrafo}
                </p>
              ))}
            </div>
          ) : null,
        )}
      </div>
    </ReportCard>
  );
}
