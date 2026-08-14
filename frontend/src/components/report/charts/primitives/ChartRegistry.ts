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

/** Evento que `ChartCanvas` escuta para saber quando o desenho parou.
 *
 * A cada frame de animação (e a cada resize) o Chart.js chama `afterRender`;
 * o consumidor debounça e só então serializa o canvas. Sem isso a captura
 * cai num instante arbitrário do desenho — ver `ChartCanvas`. */
export const CHART_RENDERED_EVENT = "mathoms:chart-rendered";

const renderSignalPlugin = {
  id: "mathomsRenderSignal",
  afterRender(chart: Chart): void {
    chart.canvas?.dispatchEvent(new CustomEvent(CHART_RENDERED_EVENT));
  },
};

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
    renderSignalPlugin,
  );
  Chart.defaults.font.family =
    "var(--font-body), Inter, system-ui, -apple-system, sans-serif";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 12;
  Chart.defaults.plugins.legend.labels.padding = 12;
  // Datalabels opt-in por chart — off por default evita poluição visual
  Chart.defaults.set("plugins.datalabels", { display: false });
  // A40.l53 — `prefers-reduced-motion` desliga a animação do canvas, como
  // `ChartGaugeScore` já faz para a agulha desenhada à mão. Sem isto o
  // Chart.js anima sempre: a media query cobrindo CSS e o gauge deixava de
  // fora justamente os canvas.
  if (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  ) {
    Chart.defaults.animation = false;
  }
  registered = true;
}
