import { ReportCard } from "../ReportCard";
import { fiduciaryDisclaimer } from "./protectionBundle.types";

/** APP_E · card `disclaimers` declarado no layout (A40.l60 · ADR-192). */
export function DisclaimersCard({
  effectiveDate = null,
}: {
  effectiveDate?: string | null;
}) {
  return (
    <ReportCard variant="neutral" size="full" title="Ressalvas fiduciárias">
      <p className="text-sm leading-relaxed text-[var(--surface-muted-foreground)]">
        {fiduciaryDisclaimer("wealth management", effectiveDate)}
      </p>
    </ReportCard>
  );
}
