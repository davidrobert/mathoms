/**
 * E2E smoke — Parecer do Planejador @critical (ADR-199 Ato 5).
 *
 * Cobre o caminho premium: relatório aberto → S_parecer renderizada →
 * hero presente → risco crítico visível → movimento P0 com CTA "Promover".
 *
 * Estratégia: `mockReportPage` serve o relatório inteiro por `page.route`
 * (mesma fixture dos specs em `tests/e2e/reports/`), e `plannerReview`
 * injeta o payload premium abaixo. Sem backend, sem pipeline, sem listagem.
 *
 * Antes desta versão o spec navegava para `/reports` e, quando a listagem
 * vinha vazia — o que é o normal no CI, cujo Postgres sobe limpo e cujo
 * `ensureLoggedIn` cria só um workspace mínimo —, chamava `test.skip()`.
 * Todos os asserts abaixo ficavam inalcançáveis e o gate passava verde sem
 * exercitar nada. Um gate que se auto-pula não é gate: se o relatório não
 * abrir, o teste tem de ficar vermelho.
 *
 * Tagged @critical → gate de deploy.
 */
import { test, expect } from "@playwright/test";

import {
  MOCK_WORKSPACE_ID,
  mockReportPage,
  waitForReportReady,
} from "./helpers/mock-report";

const SIGILO_TERMS = ["perini", "cerbasi", "auvp"] as const;

const PARECER_PAYLOAD = {
  id: "pr-smoke",
  workspace_id: MOCK_WORKSPACE_ID,
  pipeline_run_id: "run-smoke",
  status: "Gerado",
  persona_hash: "a".repeat(64),
  manifest_version: "1.0",
  schema_version: "1.0",
  model_id: "anthropic/claude-sonnet-4",
  tier_at_generation: "premium",
  items_shown_count: 5,
  items_gated_count: 0,
  cost_usd_cents: 42,
  created_at: "2026-05-13T16:00:00Z",
  published_at: null,
  superseded_at: null,
  supersedes_id: null,
  superseded_by_id: null,
  immutable_hash: null,
  content: {
    version: "1.0",
    diagnostico_geral:
      "Família com reserva sólida, exposição imobiliária acima do recomendado para o perfil de risco.",
    pontos_fortes: [
      {
        titulo: "Reserva 12 meses",
        descricao: "Liquidez adequada para emergências.",
        tema_canonico: "Saúde de balanço",
        section_id: "S1",
      },
    ],
    riscos: [
      {
        severidade: "Crítica",
        titulo: "Concentração imobiliária 70%",
        descricao:
          "Patrimônio acima do teto recomendado em ativos imobiliários.",
        tema_canonico: "Alocação",
        evidencia: null,
        evidencia_path: null,
        section_id: "S4",
        confianca: "alta",
      },
    ],
    sugestoes_execucao: [
      {
        prioridade: "P0",
        acao: "Diversificar 15% do patrimônio imobiliário",
        impacto_qualitativo:
          "Reduz risco sistêmico imobiliário sem perder renda passiva.",
        tema_canonico: "Alocação",
        confianca: "alta",
        section_id: "S4",
        suggestion_dedup_key: "d".repeat(64),
        impacto_estimado: null,
        evidencia_path: null,
      },
    ],
    sugestoes_taticas: [],
    sugestoes_estrategicas: [],
    metricas: [],
    notas_metodologicas: [],
    meta: {
      tier_at_generation: "premium",
      persona_hash: "a".repeat(64),
      manifest_version: "1.0",
      schema_version: "1.0",
      model_id: "anthropic/claude-sonnet-4",
      generated_at: "2026-05-13T16:00:00Z",
      gated_counts: {
        pontos_fortes: 0,
        riscos: 0,
        sugestoes_execucao: 0,
        sugestoes_taticas: 0,
        sugestoes_estrategicas: 0,
        metricas: 0,
        notas_metodologicas: 0,
      },
    },
  },
};

test.describe("Parecer do Planejador @critical", () => {
  test("relatório premium renderiza S_parecer com hero + risco + movimento P0", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page, {
      plannerReview: { status: 200, body: PARECER_PAYLOAD },
    });
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    // Hero do parecer presente
    const hero = page.getByTestId("parecer-hero");
    await expect(hero).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("parecer-tier-badge")).toHaveText(/Premium/);

    // Risco crítico
    await expect(page.getByText("Concentração imobiliária 70%")).toBeVisible();

    // Movimento P0 + CTA Promover
    const movimento = page.getByTestId("parecer-movimento-card").first();
    await expect(movimento).toBeVisible();
    await expect(movimento).toHaveAttribute("data-priority", "P0");
    await expect(page.getByTestId("movimento-promover").first()).toBeVisible();

    // Disclaimer fiduciário
    await expect(page.getByTestId("parecer-disclaimer")).toBeVisible();

    // Sigilo §13 — o parecer é gerado por LLM com persona construída sobre
    // Perini/Cerbasi/AUVP. Nome de metodologia vazando da geração para a copy
    // do cliente é o risco que esta seção carrega; asserção estrita, sem
    // exceção. Texto visível, não HTML: §13.4 permite atribuição em id/classe
    // /docstring, e `data-section-id="m_auvp_desvio"` é exatamente isso.
    const parecerText = (
      await page.locator("section#S_parecer").innerText()
    ).toLowerCase();
    for (const termo of SIGILO_TERMS) {
      expect(parecerText, `§13: "${termo}" na copy do parecer`).not.toContain(
        termo,
      );
    }

    // Resto do relatório: mesma regra, sem subtração.
    //
    // Havia aqui um `SIGILO_DEBT` que descontava "proteção patrimonial —
    // pilar auvp" (título de `config/report_layout.yaml`). Medindo antes de
    // remover: a string **nunca** chegava a este `innerText`. Ela vive na
    // entrada 2.5 do índice, e no viewport desktop deste spec as duas
    // superfícies de índice estão fechadas — sidebar por default
    // (`useReportTocOpen`) e drawer do `FloatingNav` por ser `<lg`. Só
    // aparecia a 390px, com o drawer aberto. Ou seja: a subtração era inerte,
    // e esta varredura não gateia copy de índice.
    //
    // Quem gateia a classe é o hook `sigilo-terms`, que ganhou surface para
    // YAML de copy (`dev/_sigilo_copy_yaml.py`) e cobre tanto a origem em
    // config quanto a em `frontend/src/components`. O escopo real daqui é o
    // texto visível do relatório no desktop — mantido estrito.
    const pageText = (await page.locator("body").innerText()).toLowerCase();
    for (const termo of SIGILO_TERMS) {
      expect(pageText, `§13: "${termo}" na copy renderizada`).not.toContain(
        termo,
      );
    }
  });
});
