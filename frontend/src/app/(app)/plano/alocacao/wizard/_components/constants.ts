export interface Pcts {
  renda_fixa_pct: number;
  acoes_pct: number;
  imoveis_reits_pct: number;
  liquidez_usd_pct: number;
}

export const PRESETS: Record<string, Pcts> = {
  Conservador: {
    renda_fixa_pct: 60,
    acoes_pct: 20,
    imoveis_reits_pct: 10,
    liquidez_usd_pct: 10,
  },
  Moderado: {
    renda_fixa_pct: 40,
    acoes_pct: 30,
    imoveis_reits_pct: 15,
    liquidez_usd_pct: 15,
  },
  Agressivo: {
    renda_fixa_pct: 25,
    acoes_pct: 45,
    imoveis_reits_pct: 15,
    liquidez_usd_pct: 15,
  },
};

export const REBAL_OPTIONS = [
  "Semestral",
  "Anual",
  "Quando desviar >5%",
] as const;

export const COLORS = {
  renda_fixa: "bg-blue-500",
  acoes: "bg-emerald-500",
  imoveis: "bg-amber-500",
  usd: "bg-purple-500",
} as const;
