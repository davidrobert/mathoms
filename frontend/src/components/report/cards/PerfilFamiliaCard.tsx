import { ReportCard } from "../ReportCard";

interface PerfilEntry {
  context?: string;
  conclusion?: string;
}

interface PerfilFamiliaCardProps {
  narrativas: Record<string, unknown> | undefined;
}

/** F9 · Fase D — Card "Perfil da Família".
 *  Exibe contexto narrativo do perfil familiar do E5 JSON.
 *  Renderiza nada se não houver narrativa de perfil.
 */
export function PerfilFamiliaCard({ narrativas }: PerfilFamiliaCardProps) {
  const perfil = narrativas?.["perfil_familia"] as PerfilEntry | undefined;
  const context = perfil?.context;
  const conclusion = perfil?.conclusion;

  if (!context && !conclusion) return null;

  return (
    <ReportCard variant="feature" title="A Família">
      <div className="grid gap-4 md:grid-cols-2">
        {context && (
          <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
            {context}
          </p>
        )}
        {conclusion && (
          <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
            {conclusion}
          </p>
        )}
      </div>
    </ReportCard>
  );
}
