/**
 * ADR-117 · Fase 2 — playground de primitivos de chart.
 *
 * Rota acessível apenas em DEV (NODE_ENV !== "production"). Renderiza
 * cada primitivo com fixtures sintéticas. Serve como smoke test visual
 * + referência para Fases 7/8/9 que vão consumir os primitivos.
 */
import { notFound } from "next/navigation";
import { ChartsDevPlayground } from "./ChartsDevPlayground";

export const metadata = { title: "Charts dev playground" };

export default function ChartsDevPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }
  return <ChartsDevPlayground />;
}
