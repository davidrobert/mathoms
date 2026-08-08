/** Sprint A16 L2 P5 (ADR-236 §D5) — Estados em que a cascata fiscal não é
 * renderizável: perfil tributário incompleto, Lucro Real (fora do escopo V1)
 * e anexo do Simples pendente. Cada um explica o que falta e de quem depende
 * a complementação.
 */
import { ReportCard } from "../ReportCard";
import { HEADER_TITLE } from "./CascataFiscalCard.copy";

export function PerfilPendenteState() {
  return (
    <ReportCard variant="neutral" size="full" title={HEADER_TITLE}>
      <EmptyStateBody
        ariaLabel="Perfil tributário PJ incompleto"
        title="Perfil tributário PJ incompleto."
        body="A cascata fiscal ficará disponível quando seu consultor preencher regime, anexo Simples, CNAE e modelo de declaração IRPF no perfil do workspace."
        hint="Solicite ao seu consultor a complementação do perfil para receber a análise completa."
      />
    </ReportCard>
  );
}

export function LucroRealState() {
  return (
    <ReportCard
      variant="neutral"
      size="full"
      title={HEADER_TITLE}
      headerRight={<EmptyStateBadge label="Lucro Real" />}
    >
      <EmptyStateBody
        ariaLabel="Regime Lucro Real — cascata em desenvolvimento"
        title="Regime Lucro Real — cascata em desenvolvimento (V2)."
        body="Lucro Real exige escrituração contábil completa (LALUR, depreciações, ajustes IRPJ) fora do escopo desta versão da cascata."
        hint="Trabalhe com seu contador para os números detalhados."
      />
    </ReportCard>
  );
}

export function AnexoPendenteState() {
  return (
    <ReportCard
      variant="neutral"
      size="full"
      title={HEADER_TITLE}
      headerRight={<EmptyStateBadge label="Simples Nacional" />}
    >
      <EmptyStateBody
        ariaLabel="Anexo Simples pendente"
        title="Anexo Simples pendente."
        body="O regime está marcado como Simples Nacional, mas o anexo (III ou V) ainda não foi informado. O anexo depende do CNAE e do fator-R; peça ao seu consultor a complementação."
      />
    </ReportCard>
  );
}

function EmptyStateBadge({ label }: { label: string }) {
  return (
    <span className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
      {label}
    </span>
  );
}

function EmptyStateBody({
  ariaLabel,
  title,
  body,
  hint,
}: {
  ariaLabel: string;
  title: string;
  body: string;
  hint?: string;
}) {
  return (
    <section role="region" aria-label={ariaLabel} className="space-y-3">
      <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
        <strong>{title}</strong> {body}
      </p>
      {hint && (
        <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
          {hint}
        </p>
      )}
    </section>
  );
}
