import type { RealEstateImovel } from "@/types/report-analysis";

const CLASS_LABEL: Record<RealEstateImovel["classification"], string> = {
  locado: "Imóvel locado",
  comercial: "Imóvel comercial",
  especulacao: "Imóvel em especulação",
};

/** Rótulo curto para a tabela/cards (A40.l6).
 *
 * Lê `endereco_display`, que o E5 só publica quando o valor passa no gate de PII
 * — nunca `endereco_canonical`, cuja cascata devolve `mat:`/`iptu:` (§Ataque A1).
 * Ausente ⇒ classe: cobre payload antigo, anterior ao campo.
 */
export function imovelDisplayLabel(
  im: Pick<RealEstateImovel, "endereco_display" | "classification">,
): string {
  const display = im.endereco_display?.trim();
  if (display) return display;
  return CLASS_LABEL[im.classification] ?? "Imóvel";
}

/** RV3-27: zero no IRPF não é valor apurado — afirmação vira `—`. */
export function valorApurado(value: number | null | undefined): number | null {
  if (value == null || value === 0) return null;
  return value;
}
