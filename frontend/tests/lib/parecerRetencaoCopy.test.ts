/**
 * A40.l22 — a frase do contador de retenção do parecer.
 *
 * Os asserts negativos são o coração: a frase erra de duas maneiras que passam
 * despercebidas em revisão de diff.
 *
 * 1. **"riscos"** — `items_dropped_count` é escalar do parecer inteiro e o
 *    enforcement remove risco OU sugestão, então nomear o bucket em que a
 *    caption mora é falso quando o item retido foi uma sugestão. A frase de
 *    exemplo em COPY_GUIDELINES §2.2 ("2 riscos retidos na conferência") é o
 *    caminho que um refactor "alinhe com o guia" tomaria.
 * 2. **"não publicado"** — banido pelo §2.2 `@2026-08-06` (colide com o estado
 *    `Publicado` da ADR-204). É a redação que estava no código antes desta lane.
 */
import { describe, expect, it } from "vitest";

import { frasePecasRetidas } from "@/lib/parecerRetencaoCopy";

describe("frasePecasRetidas", () => {
  it("concorda em número", () => {
    expect(frasePecasRetidas(1)).toBe("1 item do parecer retido na conferência");
    expect(frasePecasRetidas(2)).toBe("2 itens do parecer retidos na conferência");
  });

  it("nomeia o parecer, nunca o bucket — atribuir a 'riscos' mente quando o item retido foi sugestão", () => {
    for (const n of [1, 2, 12]) {
      expect(frasePecasRetidas(n)).not.toMatch(/risco/i);
      expect(frasePecasRetidas(n)).toMatch(/ite(m|ns) do parecer/);
    }
  });

  it("usa 'retido' e nunca 'não publicado' (COPY_GUIDELINES §2.2)", () => {
    for (const n of [1, 3]) {
      expect(frasePecasRetidas(n)).toMatch(/retid[oa]s?/);
      expect(frasePecasRetidas(n)).not.toMatch(/n[ãa]o publicad/i);
    }
  });

  it("nunca solta 'retenção' sem objeto (colide com retenção de IRRF, já user-facing)", () => {
    expect(frasePecasRetidas(2)).not.toMatch(/reten[çc][ãa]o/i);
  });
});
