import type { RealEstateImovel } from "@/types/report-analysis";

const CLASS_LABEL: Record<RealEstateImovel["classification"], string> = {
  locado: "Imóvel locado",
  comercial: "Imóvel comercial",
  especulacao: "Imóvel em especulação",
};

/** Rótulo curto para a tabela/cards — nunca a descrição cartorial (A40.l6). */
export function imovelDisplayLabel(im: Pick<RealEstateImovel, "endereco_canonical" | "classification">): string {
  const canonical = im.endereco_canonical?.trim();
  if (canonical) return canonical;
  return CLASS_LABEL[im.classification] ?? "Imóvel";
}

/** RV3-27: zero no IRPF não é valor apurado — afirmação vira `—`. */
export function valorApurado(value: number | null | undefined): number | null {
  if (value == null || value === 0) return null;
  return value;
}
