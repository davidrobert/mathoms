import { CheckCircle } from "lucide-react";
import { ReportCard } from "../ReportCard";

interface PontoForte {
  titulo?: string;
  descricao?: string;
}

/** F9 · F2.G · S10 — Card "Pontos Fortes". */
export function PontosFortesList({
  pontos,
}: {
  pontos: PontoForte[] | unknown[] | undefined;
}) {
  const items = (pontos ?? []) as PontoForte[];

  return (
    <ReportCard variant="success" size="half" title="Pontos Fortes">
      {items.length === 0 ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhum ponto forte identificado neste período.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((p, i) => (
            <li key={i} className="flex items-start gap-2">
              <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-gain)]" />
              <div>
                <p className="text-sm font-semibold">{p.titulo ?? `Ponto ${i + 1}`}</p>
                {p.descricao && (
                  <p className="text-xs text-[var(--surface-muted-foreground)]">
                    {p.descricao}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </ReportCard>
  );
}
