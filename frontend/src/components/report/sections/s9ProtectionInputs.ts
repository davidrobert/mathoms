import type { ProtectionBundle } from "../cards";

/** S9 só sai do empty total quando o snapshot trouxe insumo real (A40.l35). */
export function hasRealProtectionInputs(
  bundle: ProtectionBundle | null | undefined,
): boolean {
  if (!bundle) return false;
  if (bundle.policies.length > 0) return true;
  if (Object.keys(bundle.gap_analysis).length > 0) return true;
  if (bundle.recommendations.length > 0) return true;
  return Object.values(bundle.calculation_status).some(
    (item) => item.status === "computed",
  );
}
