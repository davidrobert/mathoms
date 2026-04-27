"use client";

import { useEffect, useRef, useState } from "react";

export type ScoreClasseKey =
  | "pessimo"
  | "ruim"
  | "regular"
  | "bom"
  | "excelente"
  | "critico";

export interface ChartGaugeScoreProps {
  /** Valor 0..max. */
  readonly value: number;
  /** Escala. Default 10. */
  readonly max?: number;
  /** Classificação textual exibida sob o gauge ("BOM", "REGULAR"…). */
  readonly classeLabel: string;
  /** Chave da classe — define cor do label. */
  readonly classeKey: ScoreClasseKey;
  /** Largura máxima do gauge em px. Default 520 (mesmo do exemplar). */
  readonly maxWidth?: number;
  /** ARIA label completo. Default: "Score X de Y, classificação Z". */
  readonly ariaLabel?: string;
  readonly "data-testid"?: string;
}

const SEGMENT_TOKENS: readonly ScoreClasseKey[] = [
  "pessimo",
  "ruim",
  "regular",
  "bom",
  "excelente",
];

const FALLBACK_COLORS: Record<ScoreClasseKey, string> = {
  pessimo: "#DC2640",
  ruim: "#F0924A",
  regular: "#F5BF2F",
  bom: "#6EDBA0",
  excelente: "#22B566",
  critico: "#B91C1C",
};

interface GaugePalette {
  readonly segments: readonly string[];
  readonly tickLabel: string;
  readonly tickStroke: string;
  readonly needle: string;
  readonly hubInner: string;
}

interface DrawArgs {
  readonly cssW: number;
  readonly cssH: number;
  readonly fraction: number;
  readonly palette: GaugePalette;
}

function readVar(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function resolvePalette(): GaugePalette {
  return {
    segments: SEGMENT_TOKENS.map((k) =>
      readVar(`--score-classe-${k}`, FALLBACK_COLORS[k]),
    ),
    tickLabel: readVar("--surface-muted-foreground", "#94A3B8"),
    tickStroke: readVar("--surface-border", "#CBD5E1"),
    needle: readVar("--brand-primary", "#1A2E44"),
    hubInner: readVar("--surface-card", "#FFFFFF"),
  };
}

function drawArc(ctx: CanvasRenderingContext2D, cx: number, cy: number, outerR: number, palette: GaugePalette): void {
  const thickness = outerR * 0.28;
  const innerR = outerR - thickness;
  const gap = 0.02;
  const segCount = palette.segments.length;
  const totalArc = Math.PI - gap * (segCount - 1);
  const segArc = totalArc / segCount;
  ctx.save();
  ctx.shadowColor = "rgba(0,0,0,0.08)";
  ctx.shadowBlur = 12;
  ctx.shadowOffsetY = 4;
  for (let i = 0; i < segCount; i++) {
    const startA = Math.PI + i * (segArc + gap);
    const endA = startA + segArc;
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, startA, endA);
    ctx.arc(cx, cy, innerR, endA, startA, true);
    ctx.closePath();
    ctx.fillStyle = palette.segments[i];
    ctx.fill();
  }
  ctx.restore();
}

function drawTicks(ctx: CanvasRenderingContext2D, cx: number, cy: number, outerR: number, palette: GaugePalette): void {
  const tickR = outerR + 14;
  ctx.save();
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `600 ${Math.round(outerR * 0.075)}px Inter, system-ui, sans-serif`;
  ctx.fillStyle = palette.tickLabel;
  for (let t = 0; t <= 10; t += 2) {
    const angle = Math.PI + (t / 10) * Math.PI;
    ctx.fillText(String(t), cx + Math.cos(angle) * tickR, cy + Math.sin(angle) * tickR);
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(angle) * (outerR + 2), cy + Math.sin(angle) * (outerR + 2));
    ctx.lineTo(cx + Math.cos(angle) * (outerR + 6), cy + Math.sin(angle) * (outerR + 6));
    ctx.strokeStyle = palette.tickStroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.restore();
}

function drawNeedle(ctx: CanvasRenderingContext2D, cx: number, cy: number, outerR: number, fraction: number, palette: GaugePalette): void {
  const needleAngle = Math.PI + fraction * Math.PI;
  const needleLen = outerR * 0.92;
  const baseW = 3.5;
  const nx = cx + Math.cos(needleAngle) * needleLen;
  const ny = cy + Math.sin(needleAngle) * needleLen;
  const perpAngle = needleAngle + Math.PI / 2;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(nx, ny);
  ctx.lineTo(cx + Math.cos(perpAngle) * baseW, cy + Math.sin(perpAngle) * baseW);
  ctx.lineTo(cx - Math.cos(perpAngle) * baseW, cy - Math.sin(perpAngle) * baseW);
  ctx.closePath();
  ctx.fillStyle = palette.needle;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 7, 0, Math.PI * 2);
  ctx.fillStyle = palette.needle;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
  ctx.fillStyle = palette.hubInner;
  ctx.fill();
  ctx.restore();
}

function drawGauge(canvas: HTMLCanvasElement, args: DrawArgs): void {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.round(args.cssW * dpr);
  canvas.height = Math.round(args.cssH * dpr);
  canvas.style.width = `${args.cssW}px`;
  canvas.style.height = `${args.cssH}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, args.cssW, args.cssH);
  const cx = args.cssW / 2;
  const cy = args.cssH * 0.84;
  const outerR = Math.min(cx, cy) * 0.88;
  drawArc(ctx, cx, cy, outerR, args.palette);
  drawTicks(ctx, cx, cy, outerR, args.palette);
  drawNeedle(ctx, cx, cy, outerR, args.fraction, args.palette);
}

function useThemeKey(): number {
  const [key, setKey] = useState(0);
  useEffect(() => {
    const observer = new MutationObserver(() => setKey((k) => k + 1));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  return key;
}

function useNeedleAnimation(value: number, max: number): number {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setProgress(1);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const duration = 600;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setProgress(eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, max]);
  return progress;
}

/** ADR-117 · Gauge semi-circular do Score Financeiro.
 *
 * Paridade com `#chart-score-gauge` de `EXEMPLO_DE_RELATORIO.html`
 * 7984-8112: 5 segmentos coloridos + ticks + agulha + hub + sombra.
 * Texto fica em overlay HTML (a11y, i18n, zoom).
 */
export function ChartGaugeScore({
  value,
  max = 10,
  classeLabel,
  classeKey,
  maxWidth = 520,
  ariaLabel,
  ...rest
}: ChartGaugeScoreProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const themeKey = useThemeKey();
  const animProgress = useNeedleAnimation(value, max);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;
    const clamped = Math.max(0, Math.min(max, value));
    const fraction = (clamped / max) * animProgress;
    const draw = () => {
      const cssW = wrapper.clientWidth;
      const cssH = cssW * (1.1 / 2);
      drawGauge(canvas, { cssW, cssH, fraction, palette: resolvePalette() });
    };
    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(wrapper);
    return () => ro.disconnect();
  }, [value, max, animProgress, themeKey]);

  const formattedValue = value.toFixed(1).replace(".", ",");
  const computedAria =
    ariaLabel ?? `Score ${formattedValue} de ${max}, classificação ${classeLabel}`;

  return (
    <div
      ref={wrapperRef}
      role="img"
      aria-label={computedAria}
      data-testid={rest["data-testid"]}
      style={{
        position: "relative",
        width: "100%",
        maxWidth,
        margin: "0 auto",
        aspectRatio: "2 / 1.1",
      }}
    >
      <canvas ref={canvasRef} aria-hidden="true" style={{ display: "block", width: "100%" }} />
      <ScoreOverlay value={formattedValue} max={max} classeLabel={classeLabel} classeKey={classeKey} />
    </div>
  );
}

interface OverlayProps {
  readonly value: string;
  readonly max: number;
  readonly classeLabel: string;
  readonly classeKey: ScoreClasseKey;
}

function ScoreOverlay({ value, max, classeLabel, classeKey }: OverlayProps) {
  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: "72%",
        textAlign: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 800,
          fontSize: "clamp(20px, 4.6cqw, 36px)",
          color: "var(--surface-foreground)",
          lineHeight: 1,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
        <span
          style={{
            fontSize: "0.55em",
            color: "var(--surface-muted-foreground)",
            fontWeight: 600,
            marginLeft: 4,
          }}
        >
          / {max}
        </span>
      </div>
      <div
        style={{
          marginTop: 6,
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: "clamp(11px, 2.1cqw, 14px)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: `var(--score-classe-${classeKey})`,
        }}
      >
        {classeLabel}
      </div>
    </div>
  );
}
