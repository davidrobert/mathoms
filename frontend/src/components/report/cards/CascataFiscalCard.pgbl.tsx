/** Sprint A16 L2 P5 (ADR-236 §D5) — Bloco "Base para dedução PGBL" do card
 * Cascata Fiscal, com os dois estados em que a dedução não se aplica:
 * `declaracao_simplificada` (flag de atenção) e `renda_tributavel_pf_zerada`
 * (estado neutro — falta IRPF processado, não é problema do usuário).
 */
import { AlertTriangle } from "lucide-react";

import type { CascataPayload } from "@/lib/api";
import { MonetaryValue } from "../MonetaryValue";

export function PgblBlock({ cascata }: { cascata: CascataPayload }) {
  return (
    <section
      aria-labelledby="cascata-pgbl-title"
      className="space-y-3 rounded-md bg-[var(--surface-muted)] p-4"
    >
      <h4
        id="cascata-pgbl-title"
        className="font-display text-sm font-semibold text-[var(--surface-foreground)]"
      >
        Base para dedução PGBL
      </h4>
      <dl className="space-y-2 text-sm">
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[var(--surface-muted-foreground)]">Renda tributável PF/ano</dt>
          <dd>
            <MonetaryValue value={cascata.pgbl_base_anual} fractionDigits={0} />
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[var(--surface-muted-foreground)]">Limite PGBL (12%)</dt>
          <dd>
            <MonetaryValue value={cascata.pgbl_limite_anual} fractionDigits={0} />
          </dd>
        </div>
      </dl>
      <p className="text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
        Base = pró-labore + outras rendas tributáveis IRPF. Lucros distribuídos
        não entram na base PGBL.
      </p>
      <PgblStatus
        aplicavel={cascata.pgbl_aplicavel}
        motivo={cascata.pgbl_motivo_inaplicavel}
      />
      <p
        className="text-[0.7rem] italic leading-relaxed text-[var(--surface-muted-foreground)]"
        data-testid="pgbl-disclaimer-crc"
      >
        Cálculo informativo de capacidade dedutível. Para decisão de aporte em
        PGBL, considere conversar com seu contador — Mathoms consolida, não
        substitui orientação tributária.
      </p>
    </section>
  );
}

function PgblStatus({
  aplicavel,
  motivo,
}: {
  aplicavel: boolean;
  motivo: CascataPayload["pgbl_motivo_inaplicavel"];
}) {
  if (aplicavel) return null;
  if (motivo === "declaracao_simplificada") return <SimplificadaFlag />;
  if (motivo === "renda_tributavel_pf_zerada") return <RendaPfZeradaNotice />;
  return null;
}

function SimplificadaFlag() {
  return (
    <div
      role="note"
      className="flex items-start gap-2 rounded-md border-l-4 border-[var(--semantic-alert)] bg-[color-mix(in_srgb,var(--semantic-alert)_10%,transparent)] p-3 text-xs leading-relaxed"
    >
      {/* Ícone sobre o tint da própria cor: 1.4.11 pede 3:1 e a base dava
          1,93:1 em light. Ver nota igual em ProvenancePopover. */}
      <AlertTriangle
        className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-alert-on-tint)]"
        aria-hidden="true"
      />
      <p>
        PGBL não dedutível — você escolheu desconto simplificado no IRPF.
        Migrar para declaração completa é decisão anual e depende de
        comparação caso-a-caso.
      </p>
    </div>
  );
}

function RendaPfZeradaNotice() {
  return (
    <p className="rounded-md border-l-4 border-[var(--surface-border)] bg-[var(--surface-card)] p-3 text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
      Renda tributável PF não detectada — processar o IRPF mais recente
      libera o cálculo da base PGBL.
    </p>
  );
}
