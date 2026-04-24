/**
 * ADR-117 · Fase 6 — adapter proximos_15d → TimelineItem[].
 *
 * E5 produz lista de ações da timeline (normalmente `dashboard.proximos_15d`
 * no tático). Shape solto; aqui normalizamos para o primitivo Timeline.
 */
import type { TimelineItem, TimelineStatus } from "@/components/report/ui";
import type { ReportAnalysisData } from "@/lib/api";

type RawTimelineItem = {
  readonly id?: string | number;
  readonly data?: string;
  readonly date?: string;
  readonly data_iso?: string;
  readonly acao?: string;
  readonly action?: string;
  readonly descricao?: string;
  readonly status?: string;
};

function mapStatus(raw: string | undefined): TimelineStatus | undefined {
  const s = (raw ?? "").toLowerCase();
  if (s === "feito" || s === "concluído" || s === "concluido" || s === "done") return "feito";
  if (s === "aguardando" || s === "waiting") return "aguardando";
  if (s === "pendente" || s === "pending" || s === "a_fazer") return "pendente";
  return undefined;
}

function formatDateBR(iso: string): string {
  // Formato YYYY-MM-DD sem timezone — parsing manual evita shift UTC→local.
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}/${m[2]}`;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
}

/** Tenta vários caminhos onde o E5 pode colocar a timeline. */
function sourceArray(data: ReportAnalysisData): RawTimelineItem[] {
  const candidates: unknown[] = [
    (data as { proximos_15d?: unknown }).proximos_15d,
    ((data as { dashboard?: { proximos_15d?: unknown } }).dashboard ?? {})
      .proximos_15d,
  ];
  for (const c of candidates) {
    if (Array.isArray(c)) return c as RawTimelineItem[];
  }
  return [];
}

export function adaptProximos15dToTimeline(
  data: ReportAnalysisData,
): readonly TimelineItem[] {
  const raw = sourceArray(data);
  return raw
    .filter((item) => {
      const action = item.acao ?? item.action ?? item.descricao;
      const date = item.data ?? item.date ?? item.data_iso;
      return typeof action === "string" && typeof date === "string";
    })
    .map((item, i) => {
      const rawDate = (item.data ?? item.date ?? item.data_iso) as string;
      const action = (item.acao ?? item.action ?? item.descricao) as string;
      return {
        id: String(item.id ?? `tl-${i}`),
        date: formatDateBR(rawDate),
        action,
        status: mapStatus(item.status),
      };
    });
}
