import { useMemo } from "react";
import { isIrpfKpis, type IrpfKpis } from "@/types/irpf";

/** ADR-157 · IRPF Full Schema · UI.
 *
 * Lê `output.irpf_kpis` do snapshot E5 com narrow guard. Retorna `null`
 * quando o workspace não tem declaração IRPF processada — caller deve
 * omitir a seção (degradação graciosa do relatório). */
export function useIrpfKpis(reportOutput: unknown): IrpfKpis | null {
  return useMemo(() => {
    if (typeof reportOutput !== "object" || reportOutput === null) return null;
    const candidate = (reportOutput as Record<string, unknown>)["irpf_kpis"];
    return isIrpfKpis(candidate) ? candidate : null;
  }, [reportOutput]);
}
