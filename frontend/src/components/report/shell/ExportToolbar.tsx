"use client";

import { useState } from "react";

export interface ExportToolbarProps {
  readonly onDownloadPdf?: () => void;
  readonly shareUrl?: string;
  readonly className?: string;
}

/** ADR-117 · Fase 4 — toolbar de exportação acima do footer.
 *
 * 2 botões: Baixar PDF (via print) e Copiar link.
 */
export function ExportToolbar({
  onDownloadPdf,
  shareUrl,
  className,
}: ExportToolbarProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">(
    "idle",
  );

  const handleCopy = async () => {
    const url = shareUrl ?? (typeof window !== "undefined" ? window.location.href : "");
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("error");
      setTimeout(() => setCopyState("idle"), 2000);
    }
  };

  const handlePrint = () => {
    if (onDownloadPdf) {
      onDownloadPdf();
    } else if (typeof window !== "undefined") {
      window.print();
    }
  };

  return (
    <div
      className={className}
      data-export-toolbar
      style={{
        padding: "20px 40px",
        background: "var(--report-gradient-nav-sticky)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        flexWrap: "wrap",
      }}
    >
      <ToolbarBtn onClick={handlePrint} icon="🖨">
        Baixar PDF
      </ToolbarBtn>
      <ToolbarBtn onClick={handleCopy} icon={copyState === "copied" ? "✓" : "🔗"}>
        {copyState === "copied"
          ? "Link copiado"
          : copyState === "error"
            ? "Erro ao copiar"
            : "Copiar link"}
      </ToolbarBtn>
    </div>
  );
}

function ToolbarBtn({
  onClick,
  icon,
  children,
}: {
  onClick: () => void;
  icon: string;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 20px",
        borderRadius: 8,
        border: "1px solid rgba(255,255,255,0.2)",
        background: "rgba(255,255,255,0.08)",
        color: "rgba(255,255,255,0.85)",
        fontFamily: "var(--font-body)",
        fontSize: 13,
        fontWeight: 500,
        cursor: "pointer",
        transition: "all 0.2s",
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 16 }}>
        {icon}
      </span>
      {children}
    </button>
  );
}
