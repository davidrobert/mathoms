import { describe, expect, it } from "vitest";

import {
  derivePrimaryYear,
  matchIrpfToPeriod,
} from "@/lib/irpf/irpf-period-match";

describe("derivePrimaryYear", () => {
  it("extrai ano do último label YYYY-MM", () => {
    expect(derivePrimaryYear(["2024-01", "2024-06", "2024-12"])).toBe(2024);
  });

  it("retorna null para labels vazios ou malformados", () => {
    expect(derivePrimaryYear([])).toBeNull();
    expect(derivePrimaryYear(undefined)).toBeNull();
    expect(derivePrimaryYear(["abc"])).toBeNull();
  });
});

describe("matchIrpfToPeriod", () => {
  it("considera o mesmo ano e o anterior como autoritativos", () => {
    expect(matchIrpfToPeriod([2023, 2024], 2024)).toEqual({
      anoBase: 2024,
      defasadoAnos: 0,
      authoritative: true,
    });
    expect(matchIrpfToPeriod([2023, 2024], 2025).authoritative).toBe(true);
  });

  it("marca defasagem a partir de dois anos", () => {
    expect(matchIrpfToPeriod([2022], 2025)).toEqual({
      anoBase: 2022,
      defasadoAnos: 3,
      authoritative: false,
    });
  });

  it("ignora anos futuros inelegíveis", () => {
    expect(matchIrpfToPeriod([2023, 2024, 2027], 2024).anoBase).toBe(2024);
    expect(matchIrpfToPeriod([2027, 2028], 2024).anoBase).toBeNull();
  });
});
