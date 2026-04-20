import { ReportCard } from "../ReportCard";

interface ContrafluxoData {
  selic_atual?: number;
  cenarios?: {
    pessimista?: { selic?: number; cdi?: number };
    base?: { selic?: number; cdi?: number };
    otimista?: { selic?: number; cdi?: number };
  };
}

interface ContrafluxoCardProps {
  contrafluxo?: ContrafluxoData;
  cdi_anual?: number;
}

const CENARIO_LABELS: Record<string, string> = {
  pessimista: "Queda acentuada",
  base: "Estabilidade (base)",
  otimista: "Alta adicional",
};

const CENARIO_ACOES: Record<string, string> = {
  pessimista: "Manter IPCA+ até vencimento; aumentar prefixados longos.",
  base: "Manter estratégia atual (contrafluxo IPCA+).",
  otimista: "Aumentar CDBs pós-fixados curtos; evitar IPCA+ longo novo.",
};

/** F9 · F2.C · S3 — Card "Contrafluxo" (AUVP Raul Sena).
 *  Exibe Selic/CDI atuais e tabela de sensibilidade por cenário.
 */
export function ContrafluxoCard({ contrafluxo, cdi_anual }: ContrafluxoCardProps) {
  const selic = contrafluxo?.selic_atual;
  const cdi = cdi_anual;

  const subtitle = [
    selic !== undefined ? `Selic atual: ${selic.toFixed(2)}% a.a.` : null,
    cdi !== undefined ? `CDI: ${cdi.toFixed(2)}%` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  const cenarios = contrafluxo?.cenarios;
  const cenarioKeys = cenarios ? Object.keys(cenarios) : [];

  return (
    <ReportCard variant="primary" title="Contrafluxo">
      {subtitle && (
        <p className="mb-4 text-sm text-[var(--surface-muted-foreground)]">{subtitle}</p>
      )}

      <p className="mb-4 text-sm text-[var(--surface-foreground)]">
        Estratégia AUVP: investir no indexador que está fora de moda. Com Selic alta, prefixados e IPCA+ oferecem melhor relação risco/retorno. Quando a Selic cair, os IPCA+ longos valorizam via marcação a mercado.
      </p>

      {cenarioKeys.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
                <th className="pb-2 font-semibold">Cenário</th>
                <th className="pb-2 text-right font-semibold">Selic</th>
                <th className="pb-2 text-right font-semibold">CDI</th>
                <th className="hidden pb-2 font-semibold sm:table-cell">Ação</th>
              </tr>
            </thead>
            <tbody>
              {cenarioKeys.map((key) => {
                const c = (cenarios as Record<string, { selic?: number; cdi?: number }>)[key];
                const isBase = key === "base";
                return (
                  <tr
                    key={key}
                    className={`border-b border-[var(--surface-border)]/40 last:border-0 ${isBase ? "font-semibold" : ""}`}
                  >
                    <td className="py-2 pr-3">{CENARIO_LABELS[key] ?? key}</td>
                    <td className="py-2 pr-3 text-right font-mono tabular-nums">
                      {c?.selic !== undefined ? `${c.selic.toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
                      {c?.cdi !== undefined ? `${c.cdi.toFixed(1)}%` : "—"}
                    </td>
                    <td className="hidden py-2 text-xs text-[var(--surface-muted-foreground)] sm:table-cell">
                      {CENARIO_ACOES[key] ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!selic && !cdi && cenarioKeys.length === 0 && (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados de Selic/CDI não disponíveis neste relatório.
        </p>
      )}
    </ReportCard>
  );
}
