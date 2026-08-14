/** Sprint A16 L2 P5 (ADR-236 §D5) — Bloco "Base para dedução PGBL" do card
 * Cascata Fiscal, com os estados em que a dedução não se aplica:
 * `declaracao_simplificada` (flag de atenção) e `renda_tributavel_pf_zerada`
 * (estado neutro — falta IRPF processado, não é problema do usuário).
 */
import { AlertTriangle } from "lucide-react";

import type { CascataPayload } from "@/lib/api";
import { MonetaryValue } from "../MonetaryValue";

export function PgblBlock({
  cascata,
  hasIrpf,
}: {
  cascata: CascataPayload;
  hasIrpf: boolean;
}) {
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
      </dl>
      <p className="text-xs leading-relaxed text-[var(--surface-muted-foreground)]">
        Base = pró-labore + outras rendas tributáveis IRPF. Lucros distribuídos
        não compõem esta base. <PgblDestination hasIrpf={hasIrpf} />
      </p>
      <PgblStatus
        aplicavel={cascata.pgbl_aplicavel}
        motivo={cascata.pgbl_motivo_inaplicavel}
      />
      <p
        className="text-xs italic leading-relaxed text-[var(--surface-muted-foreground)]"
        data-testid="pgbl-disclaimer-crc"
      >
        Base informativa para análise de PGBL. Para decidir sobre aportes,
        confirme os requisitos previdenciários aplicáveis e converse com seu
        contador — o Mathoms consolida dados e não substitui orientação
        tributária.
      </p>
    </section>
  );
}

function PgblDestination({ hasIrpf }: { hasIrpf: boolean }) {
  if (!hasIrpf) {
    return <>O teto e a capacidade dedutível dependem de uma declaração de IRPF processada.</>;
  }
  return (
    <>
      Ver teto e capacidade dedutível em{" "}
      <a
        href="#S_IRPF_OTIMIZACAO"
        className="underline decoration-dotted underline-offset-2 text-[var(--brand-info)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        Otimização Tributária
      </a>
      .
    </>
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
  if (motivo === "tipo_declaracao_desconhecido")
    return <TipoDeclaracaoDesconhecidoNotice />;
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

// ADR-375 D4 cond. 1: estado neutro, não flag de atenção — o insumo falta no
// cadastro, não há erro do usuário. Declara a precondição legal (só a completa
// deduz) em vez de imprimir o teto como se ele estivesse disponível.
function TipoDeclaracaoDesconhecidoNotice() {
  return (
    <p
      data-testid="pgbl-tipo-declaracao-desconhecido"
      className="rounded-md border-l-4 border-[var(--surface-border)] bg-[var(--surface-card)] p-3 text-xs leading-relaxed text-[var(--surface-muted-foreground)]"
    >
      Modelo de declaração do IRPF não registrado — só a declaração completa
      admite a dedução de PGBL. Informe o modelo no perfil tributário para que
      avaliar a dedutibilidade.
    </p>
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
