"use client";

import type { DocumentaryCoverage } from "../cards";
import { CATEGORY_LABELS, type ProtectionCategory } from "../cards/protectionBundle.types";

const CTA_HREF = "/protecao";

function categoriaLabel(categoria: string): string {
  return CATEGORY_LABELS[categoria as ProtectionCategory] ?? categoria;
}

function listar(itens: string[]): string {
  if (itens.length <= 1) return itens.join("");
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

function frasePolice(documentary: DocumentaryCoverage): string {
  const n = documentary.active_policies_count;
  const plural = n === 1 ? "apólice vigente" : "apólices vigentes";
  const seguradoras = documentary.insurers.length
    ? ` (${listar(documentary.insurers)})`
    : "";
  return `Encontramos ${n} ${plural} nos documentos que você enviou${seguradoras}.`;
}

function fraseRetencao(documentary: DocumentaryCoverage): string {
  const categorias = documentary.unconfirmed_categories.map(categoriaLabel);
  if (categorias.length === 0) {
    return (
      "Nenhuma delas confirma cobertura de vida, invalidez ou sucessão, " +
      "então esta seção fica sem cálculo de gap."
    );
  }
  const alvo = listar(categorias);
  const verbo = categorias.length === 1 ? "está" : "estão";
  return (
    `Elas não constam do seu cadastro de proteção, então o capital contratado ` +
    `não foi confirmado e o gap de ${alvo} ${verbo} retido — não publicamos ` +
    `número nem recomendação sobre ele.`
  );
}

function fraseVigencia(documentary: DocumentaryCoverage): string | null {
  const fim = documentary.earliest_coverage_end;
  if (!fim) return null;
  return `A vigência mais próxima que lemos nos documentos termina em ${fim}.`;
}

/** Estado PARCIAL da S9 (ADR-395 §D3) — nomeia o identificado, não julga.
 *
 * Substitui o `<EmptyState/>` "sem riscos cadastrados", que desqualificava
 * dado exibido no próprio relatório (PD-4 / RV6-20). A copy declara o que
 * falta — a **confirmação** — sem afirmar que a cobertura é adequada nem que
 * falta cobertura. O follow-up de prestamista / vida em grupo é exatamente o
 * motivo de não afirmar adequação aqui.
 */
export function S9CoberturaNaoConfirmada({
  documentary,
}: {
  documentary: DocumentaryCoverage;
}) {
  const vigencia = fraseVigencia(documentary);
  return (
    <div
      className="report-card report-card--neutral md:col-span-2"
      data-testid="s9-cobertura-nao-confirmada"
    >
      <h3 className="text-style-subtitle">Cobertura identificada, ainda não confirmada</h3>
      <p className="text-style-body mt-2">
        {frasePolice(documentary)} {fraseRetencao(documentary)}
      </p>
      {vigencia && <p className="text-style-caption mt-2 text-muted">{vigencia}</p>}
      <p className="text-style-caption mt-2 text-muted">
        Isto não afirma que sua cobertura é adequada nem que falta cobertura: o que falta é a
        confirmação do que está contratado.
      </p>
      <p className="text-style-body mt-3">
        <a href={CTA_HREF} className="underline">
          Confirmar apólices no cadastro de proteção
        </a>
      </p>
    </div>
  );
}
