"use client";

// A40.l22 — superfície de degradação do parecer.
//
// Dois consumidores: o estado retido inteiro (`SParecerSection`) e a nota do
// estado parcial (`ParecerHeroDiagnostico`). Vivem juntos porque abrem com a
// mesma frase de propósito — o cliente aprende UM idioma para "conferimos e
// parte não passou", não dois.

import Link from "next/link";

import { frasePecasRetidas } from "@/lib/parecerRetencaoCopy";

export function ReprocessarParecerLink() {
  return (
    <p className="mt-2 text-sm">
      <Link href="/pipeline" className="text-[var(--brand-primary)] underline">
        Reprocessar o parecer
      </Link>{" "}
      <span className="text-[var(--surface-muted-foreground)]">
        — refaz somente o parecer e usa sua chave de IA novamente.
      </span>
    </p>
  );
}

/** Nota do parecer ENTREGUE com itens retidos.
 *
 * Texto no DOM, nunca `title=`/hover: hover falha WCAG 1.4.13 e desaparece no
 * PDF, que é a superfície que sai do produto e chega a terceiro que não pode
 * perguntar. Mora acima do diagnóstico porque a ressalva precede o que ela
 * ressalva na ordem de leitura e de screen reader — e o item retido pode ser
 * uma sugestão, que renderiza depois da tabela de riscos.
 */
export function ParecerRetencaoParcialNota({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <div className="mb-3" data-testid="parecer-retencao-parcial">
      <p className="text-sm text-[var(--surface-foreground)]">
        Antes de publicar, conferimos cada item deste parecer.{" "}
        {frasePecasRetidas(count)} — {count === 1 ? "ele não aparece" : "eles não aparecem"}{" "}
        nas listas abaixo. Os números das demais seções não mudam.
      </p>
      <ReprocessarParecerLink />
    </div>
  );
}
