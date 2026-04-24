/** ADR-117 · Fase 4 — skip-nav primeiro foco (a11y).
 *
 * Matching `.skip-nav` EXEMPLO_DE_RELATORIO.html linhas 533-539.
 * Escondido fora da viewport até receber foco (via Tab).
 */
export function SkipNav({ targetId = "report-main" }: { readonly targetId?: string }) {
  return (
    <a
      href={`#${targetId}`}
      style={{
        position: "absolute",
        top: -100,
        left: 16,
        zIndex: 9999,
        background: "var(--brand-primary)",
        color: "#fff",
        padding: "12px 24px",
        borderRadius: "var(--radius-lg, 8px)",
        fontWeight: 600,
        fontSize: "var(--report-font-size-md, 14px)",
        textDecoration: "none",
        transition: "top 0.2s",
      }}
      onFocus={(e) => {
        e.currentTarget.style.top = "16px";
        e.currentTarget.style.outline = "3px solid var(--brand-accent)";
      }}
      onBlur={(e) => {
        e.currentTarget.style.top = "-100px";
        e.currentTarget.style.outline = "none";
      }}
    >
      Pular para o conteúdo principal
    </a>
  );
}
