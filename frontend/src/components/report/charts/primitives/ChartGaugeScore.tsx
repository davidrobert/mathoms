"use client";

import { useEffect, useRef, useState } from "react";
import {
  type GaugePalette,
  type ScoreClasseKey,
  resolveGaugeScorePalette,
} from "./gaugeScorePalette";

export type { ScoreClasseKey };

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

interface DrawArgs {
  readonly cssW: number;
  readonly cssH: number;
  readonly fraction: number;
  readonly palette: GaugePalette;
}

function drawArcSegment(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startA: number,
  endA: number,
  fill: string,
): void {
  ctx.beginPath();
  ctx.arc(cx, cy, outerR, startA, endA);
  ctx.arc(cx, cy, innerR, endA, startA, true);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
}

function applyArcShadow(ctx: CanvasRenderingContext2D): void {
  ctx.shadowColor = "rgba(0,0,0,0.08)";
  ctx.shadowBlur = 12;
  ctx.shadowOffsetY = 4;
}

function drawArc(ctx: CanvasRenderingContext2D, cx: number, cy: number, outerR: number, palette: GaugePalette): void {
  const innerR = outerR - outerR * 0.28;
  const gap = 0.02;
  const segCount = palette.segments.length;
  const segArc = (Math.PI - gap * (segCount - 1)) / segCount;
  ctx.save();
  applyArcShadow(ctx);
  for (let i = 0; i < segCount; i++) {
    const startA = Math.PI + i * (segArc + gap);
    drawArcSegment(ctx, cx, cy, outerR, innerR, startA, startA + segArc, palette.segments[i]);
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

function drawNeedleTriangle(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  outerR: number,
  fraction: number,
  fill: string,
): void {
  const angle = Math.PI + fraction * Math.PI;
  const len = outerR * 0.92;
  const baseW = 3.5;
  const perp = angle + Math.PI / 2;
  ctx.beginPath();
  ctx.moveTo(cx + Math.cos(angle) * len, cy + Math.sin(angle) * len);
  ctx.lineTo(cx + Math.cos(perp) * baseW, cy + Math.sin(perp) * baseW);
  ctx.lineTo(cx - Math.cos(perp) * baseW, cy - Math.sin(perp) * baseW);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
}

function drawNeedleHub(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  outer: string,
  inner: string,
): void {
  ctx.beginPath();
  ctx.arc(cx, cy, 7, 0, Math.PI * 2);
  ctx.fillStyle = outer;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
  ctx.fillStyle = inner;
  ctx.fill();
}

function drawNeedle(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  outerR: number,
  fraction: number,
  palette: GaugePalette,
): void {
  ctx.save();
  drawNeedleTriangle(ctx, cx, cy, outerR, fraction, palette.needle);
  drawNeedleHub(ctx, cx, cy, palette.needle, palette.hubInner);
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

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

function startEasedAnimation(
  durationMs: number,
  onProgress: (p: number) => void,
): () => void {
  let raf = 0;
  const start = performance.now();
  const tick = (now: number) => {
    const t = Math.min(1, (now - start) / durationMs);
    onProgress(1 - Math.pow(1 - t, 3));
    if (t < 1) raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}

function useNeedleAnimation(value: number, max: number): number {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setProgress(1);
      return;
    }
    return startEasedAnimation(600, setProgress);
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
      drawGauge(canvas, { cssW, cssH, fraction, palette: resolveGaugeScorePalette() });
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
          fontWeight: 700,
          fontSize: "clamp(11px, 2.1cqw, 14px)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: `var(--score-classe-${classeKey})`,
        }}
      >
        {classeLabel}
      </div>
      <div
        style={{
          marginTop: 6,
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
    </div>
  );
}
