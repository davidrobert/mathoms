/**
 * ADR-117 · Fase 2 — registra scales e plugins do Chart.js uma única vez.
 *
 * Chart.js 4+ requer registro explícito dos controllers/elementos/escalas
 * usados (tree-shaking). Este módulo é importado pelo ChartCanvas e por
 * qualquer primitivo de chart — idempotente, seguro importar N vezes.
 */
import {
  Chart,
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PieController,
  PointElement,
  TimeScale,
  Title,
  Tooltip,
} from "chart.js";
import DatalabelsPlugin from "chartjs-plugin-datalabels";

let registered = false;

export function ensureChartRegistered(): void {
  if (registered) return;
  Chart.register(
    ArcElement,
    BarController,
    BarElement,
    CategoryScale,
    DoughnutController,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PieController,
    PointElement,
    TimeScale,
    Title,
    Tooltip,
    DatalabelsPlugin,
  );
  Chart.defaults.font.family =
    "var(--font-body), Inter, system-ui, -apple-system, sans-serif";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 12;
  Chart.defaults.plugins.legend.labels.padding = 12;
  // Datalabels opt-in por chart — off por default evita poluição visual
  Chart.defaults.set("plugins.datalabels", { display: false });
  registered = true;
}
