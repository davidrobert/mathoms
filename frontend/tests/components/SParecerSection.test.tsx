/**
 * Unit tests — SParecerSection (ADR-199 / ADR-208 · Ato 5).
 *
 * Cobre:
 * - empty state (404) → "Parecer ainda não gerado";
 * - render premium (full content) com hero + risk + movimento + métrica;
 * - render free (teaser): chip "Amostra", teaser "+N no Premium";
 * - sigilo §13: jamais cita Perini/Cerbasi/AUVP no DOM.
 *
 * MSW intercepta GET /workspaces/:wsId/reports/:reportId/planner-review.
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";

import { SParecerSection } from "@/components/report/sections/SParecer";
import type { PlannerReviewResponse } from "@/lib/api";
import { DELIMITACAO_DE_DANO } from "@/lib/parecerAusenciaCopy";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-test-uuid-1";
const REPORT_ID = "report-test-uuid-1";

function premiumResponse(): PlannerReviewResponse {
  return {
    id: "pr-1",
    workspace_id: WS_ID,
    pipeline_run_id: "run-1",
    status: "Gerado",
    persona_hash: "a".repeat(64),
    manifest_version: "1.0",
    schema_version: "1.0",
    model_id: "anthropic/claude-sonnet-4",
    tier_at_generation: "premium",
    items_shown_count: 5,
    items_gated_count: 0,
    outcome: "entregue",
    retention: null,
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
        "Família com reserva sólida, exposição imobiliária acima do recomendado.",
      pontos_fortes: [
        {
          titulo: "Reserva 12 meses",
          descricao: "Liquidez adequada.",
          tema_canonico: "Saúde de balanço",
          section_id: "S1",
        },
      ],
      riscos: [
        {
          severidade: "Crítica",
          titulo: "Concentração imobiliária 70%",
          descricao: "Acima do teto recomendado.",
          tema_canonico: "Alocação",
          evidencia: null,
          evidencia_path: null,
          ancoras: [],
          section_id: "S4",
          confianca: "alta",
        },
      ],
      sugestoes_execucao: [
        {
          prioridade: "P0",
          acao: "Diversificar 15% do imobiliário",
          impacto_qualitativo: "Reduz risco sistêmico imobiliário.",
          tema_canonico: "Alocação",
          confianca: "alta",
          section_id: "S4",
          suggestion_dedup_key: "d".repeat(64),
          impacto_estimado: null,
          evidencia_path: null,
          ancoras: [],
        },
      ],
      sugestoes_taticas: [],
      sugestoes_estrategicas: [],
      metricas: [
        {
          nome: "Concentração imobiliária",
          valor_atual: "70%",
          target: "45%",
          frequencia_revisao: "trimestral",
          section_id: "S4",
          tema_canonico: "Alocação",
        },
      ],
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
}

function freeResponse(): PlannerReviewResponse {
  const p = premiumResponse();
  const base = p.content!;
  return {
    ...p,
    tier_at_generation: "free",
    items_gated_count: 14,
    content: {
      ...base,
      pontos_fortes: base.pontos_fortes.slice(0, 1),
      sugestoes_execucao: [],
      sugestoes_taticas: [],
      sugestoes_estrategicas: [],
      metricas: [],
      meta: {
        ...base.meta,
        tier_at_generation: "free",
        gated_counts: {
          pontos_fortes: 2,
          riscos: 3,
          sugestoes_execucao: 2,
          sugestoes_taticas: 1,
          sugestoes_estrategicas: 1,
          metricas: 4,
          notas_metodologicas: 2,
        },
      },
    },
  };
}

function retainedResponse(
  reason:
    | "parecer.citacao_nao_confirmada"
    | "parecer.sigilo" = "parecer.citacao_nao_confirmada",
): PlannerReviewResponse {
  return {
    ...premiumResponse(),
    items_shown_count: 0,
    outcome: "retido",
    retention: { reason, items_dropped_count: 0 },
    content: null,
  };
}

/** Parecer ENTREGUE com itens retidos na conferência (A40.l22 · ADR-366 §D1).
 *
 * `content` presente + `outcome: entregue_com_retencao` — o desfecho que hoje
 * chega à tela como um parecer íntegro, com a lacuna indetectável. `riscos`
 * ganha um 2º item para que a caption tenha "Mostrando 2 de 2" e a aritmética
 * "visíveis + retidos = total" fique **falsa** de propósito: é ela que o
 * substantivo de cada contador tem de impedir.
 */
function parcialResponse(dropped = 2): PlannerReviewResponse {
  const p = premiumResponse();
  const base = p.content!;
  return {
    ...p,
    outcome: "entregue_com_retencao",
    retention: {
      reason: "parecer.citacao_nao_confirmada",
      items_dropped_count: dropped,
    },
    content: {
      ...base,
      riscos: [
        base.riscos[0],
        { ...base.riscos[0], titulo: "Cobertura de seguro abaixo do necessário" },
      ],
    },
  };
}

function serve(body: PlannerReviewResponse) {
  server.use(
    http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
      HttpResponse.json(body),
    ),
  );
}

describe("<SParecerSection /> — retenção parcial @A40.l22", () => {
  it("declara a nota de retenção acima do diagnóstico, em texto no DOM", async () => {
    serve(parcialResponse(2));
    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    const nota = await screen.findByTestId("parecer-retencao-parcial");
    expect(nota).toHaveTextContent("2 itens do parecer retidos na conferência");
    expect(nota).toHaveTextContent("Os números das demais seções não mudam.");
    // Nunca `title=`/hover: falha WCAG 1.4.13 e desaparece no PDF.
    expect(nota.querySelector("[title]")).toBeNull();
    // A ação vem junto com o fato (COPY_GUIDELINES §7.1).
    expect(
      screen.getAllByRole("link", { name: /Reprocessar o parecer/i }).length,
    ).toBeGreaterThan(0);
  });

  it("a nota precede o diagnóstico na ordem de leitura", async () => {
    serve(parcialResponse(2));
    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    const nota = await screen.findByTestId("parecer-retencao-parcial");
    const corpo = screen.getByTestId("parecer-diagnostico-body");
    // `DOCUMENT_POSITION_FOLLOWING` = 4: o corpo vem DEPOIS da nota.
    expect(nota.compareDocumentPosition(corpo) & 4).toBe(4);
  });

  it("caption separa os 3 contadores pelo substantivo — 'riscos' vs 'itens do parecer'", async () => {
    const body = parcialResponse(2);
    body.content!.meta.gated_counts = { ...body.content!.meta.gated_counts, riscos: 3 };
    serve(body);
    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    const caption = await screen.findByTestId("parecer-risks-caption");
    expect(caption).toHaveTextContent("Mostrando 2 de 2 riscos");
    expect(caption).toHaveTextContent("2 itens do parecer retidos na conferência");
    expect(caption).toHaveTextContent("+3 no Premium");
    // O contador de retenção NÃO pode se apresentar como contador de riscos —
    // o item retido pode ter sido uma sugestão.
    expect(caption.textContent).not.toMatch(/\d+\s+riscos?\s+retid/i);
    // Retido (qualidade) e gated (comercial) nunca somados: ações diferentes.
    expect(caption.textContent).not.toContain("5 no Premium");
  });

  it("parecer íntegro não ganha nota nem 3º contador", async () => {
    serve(premiumResponse());
    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("parecer-retencao-parcial")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("parecer-risks-caption-retidos"),
    ).not.toBeInTheDocument();
  });

  it("desfecho `entregue` com contador preenchido por engano NÃO acende o sinal", async () => {
    // O gate é o `outcome` (ADR-366 §D1), nunca o contador — este é o teste que
    // fica vermelho se alguém "simplificar" para ler `items_dropped_count` cru.
    serve({
      ...premiumResponse(),
      retention: {
        reason: "parecer.citacao_nao_confirmada",
        items_dropped_count: 2,
      },
    });
    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("parecer-retencao-parcial")).not.toBeInTheDocument();
  });

  it("não vaza vocabulário de operador no estado parcial", async () => {
    serve(parcialResponse(2));
    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );
    await screen.findByTestId("parecer-retencao-parcial");

    const html = container.innerHTML;
    for (const leak of [
      "error_detail",
      "_meta",
      "whitelist_miss",
      "resolve_null",
      "pairing_mismatch",
      "number_in_prose",
      "needs_review",
      "parecer.citacao_nao_confirmada",
      "entregue_com_retencao",
      "items_dropped",
      "E5",
      "E6",
    ]) {
      expect(html).not.toContain(leak);
    }
    expect(html).not.toMatch(/risco:\s*\d/i);
    expect(html).not.toMatch(/\bstage\b/i);
  });
});

function absence404(code: string) {
  return http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
    HttpResponse.json({ detail: { code, message: "sem parecer" } }, { status: 404 }),
  );
}

describe("<SParecerSection /> @ADR-199", () => {
  it("renderiza empty state quando endpoint retorna 404 not_generated_yet", async () => {
    server.use(absence404("not_generated_yet"));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Parecer não disponível neste relatório"),
    ).toBeInTheDocument();
  });

  // Uma copy POR código (A40.l22), porque as 4 AÇÕES são distintas — que é o
  // teste do `RETAINED_BODY` (colapsar quando a ação é a mesma), não exceção a
  // ele. Sem asserção por código, colapsar as 4 num texto só passa verde.
  const CASOS = [
    {
      code: "not_generated_yet",
      titulo: "Parecer não disponível neste relatório",
      cta: null,
    },
    {
      code: "tier_gated",
      titulo: "Parecer exige uma chave de IA ativa",
      cta: "Cadastrar sua chave de IA",
    },
    {
      code: "generation_unavailable",
      titulo: "Não conseguimos gerar o parecer deste relatório",
      cta: "Reprocessar o parecer",
    },
    {
      code: "parecer_artifact_missing",
      titulo: "Não conseguimos recuperar o parecer deste relatório",
      cta: "Reprocessar o parecer",
    },
  ] as const;

  it.each(CASOS)("404 $code renderiza copy e CTA próprios", async ({ code, titulo, cta }) => {
    server.use(absence404(code));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(screen.getByText(titulo)).toBeInTheDocument();
    expect(screen.getByTestId("parecer-empty")).toHaveAttribute("data-absence-code", code);
    // Título é heading: no PDF em A4 nenhum <h2> de seção chega, então este é o
    // único rótulo do bloco naquela superfície (test.fixme em print.@critical).
    expect(screen.getByRole("heading", { level: 3, name: titulo })).toBeInTheDocument();
    for (const outro of CASOS.filter((c) => c.cta && c.cta !== cta)) {
      expect(screen.queryByText(outro.cta!)).not.toBeInTheDocument();
    }
    if (cta) expect(screen.getByText(cta)).toBeInTheDocument();
  });

  // O cliente aprende UM idioma de delimitação — a mesma regra que o comentário
  // do `ParecerRetencaoNota` já estabelece para a retenção. Três redações para o
  // mesmo fato é o que faz o leitor achar que são fatos diferentes.
  it.each(CASOS)("404 $code fecha com a delimitação de dano literal", async ({ code }) => {
    server.use(absence404(code));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("parecer-empty").textContent).toContain(
      DELIMITACAO_DE_DANO,
    );
  });

  // Falha e vazio não podem dividir o idioma visual: borda tracejada centralizada
  // é "ainda não há nada aqui", e diria isso sobre uma geração que quebrou.
  it.each(CASOS)("404 $code separa falha de vazio no peso visual", async ({ code }) => {
    server.use(absence404(code));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    const ehFalha = code.startsWith("generation_") || code.startsWith("parecer_artifact");
    const alerta = screen
      .getByTestId("parecer-empty")
      .closest("[data-alert-severity='warning']");
    expect(alerta !== null).toBe(ehFalha);
  });

  // `tier` é BYOK, não plano: "premium" ⟺ chave de IA decriptável
  // (`_classify_llm_config`). Enquadrar por plano acusaria de downgrade quem
  // perdeu a chave numa rotação de FERNET_KEY.
  it("tier_gated aponta para a chave de IA, não para uma compra", async () => {
    server.use(absence404("tier_gated"));

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    const link = container.querySelector('a[href^="/config"]');
    expect(link).not.toBeNull();
    expect(container.innerHTML).not.toMatch(/assinar|comprar|plano Free/i);
  });

  // "por um planejador" afirmaria agente humano e contradiria o disclaimer
  // fiduciário que roda na MESMA seção.
  it.each(CASOS)("404 $code não promete um planejador humano", async ({ code }) => {
    server.use(absence404(code));

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(container.innerHTML).not.toMatch(/por um planejador|planejador (vai|irá)/i);
  });

  it("nenhuma copy de ausência promete o que a anterior prometia", async () => {
    server.use(absence404("not_generated_yet"));

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    // A copy antiga afirmava entrega futura para QUALQUER ausência — falso para
    // o premium cujo run tentou e não entregou. É o defeito que a lane fecha.
    expect(container.innerHTML).not.toContain("Próximo relatório premium incluirá");
  });

  it("report_not_found vira erro, não ausência de parecer", async () => {
    server.use(absence404("report_not_found"));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    // Dizer "parecer não disponível" numa página cujo RELATÓRIO não resolve
    // descreve o defeito errado para quem só pode agir sobre ele.
    await waitFor(() => {
      expect(screen.getByTestId("parecer-error")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("parecer-empty")).not.toBeInTheDocument();
  });

  it("código desconhecido segue caindo no conservador, não em erro", async () => {
    server.use(absence404("codigo_que_o_cliente_ainda_nao_conhece"));

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    // O servidor pode ganhar membro antes do cliente. Preservado de propósito:
    // só o caso NOMEADO (`report_not_found`) mudou de destino.
    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("parecer-error")).not.toBeInTheDocument();
  });

  it("declara o parecer retido em vez de dizer que não foi gerado (ADR-366)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(retainedResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-retained")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Parecer retido neste relatório"),
    ).toBeInTheDocument();
    // Delimitação de dano: o cliente não pode generalizar a lacuna do add-on.
    expect(
      screen.getByText("Os números das demais seções não mudam."),
    ).toBeInTheDocument();
    // A copy de "ainda não gerado" MENTE aqui — é o defeito que a lane conserta.
    expect(screen.queryByTestId("parecer-empty")).not.toBeInTheDocument();
  });

  it("não vaza vocabulário de operador no estado retido (ADR-366 §D3)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(retainedResponse("parecer.sigilo")),
      ),
    );

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("parecer-retained")).toBeInTheDocument();
    });

    const html = container.innerHTML;
    for (const leak of [
      "placeholder",
      "error_detail",
      "_meta",
      "whitelist_miss",
      "resolve_null",
      "pairing_mismatch",
      "needs_review",
      "parecer.sigilo",
    ]) {
      expect(html).not.toContain(leak);
    }
    // `risco:N` é o shape do vocabulário de operador; "Risco" sozinho é legítimo.
    expect(html).not.toMatch(/risco:\s*\d/i);
  });

  it("motivo desconhecido cai no fallback — classe nova não apaga a seção", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json({
          ...retainedResponse(),
          retention: {
            reason: "parecer.motivo_do_futuro",
            items_dropped_count: 0,
          },
        }),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-retained")).toBeInTheDocument();
    });
    expect(
      screen.getByText("O parecer deste relatório foi retido antes da publicação."),
    ).toBeInTheDocument();
    // COPY_GUIDELINES §2.2 `@2026-08-06` bane "não publicado" (colide com o
    // estado `Publicado` da ADR-204) — era a redação anterior deste fallback.
    expect(document.body.innerHTML).not.toMatch(/n[ãa]o (foi )?publicad/i);
  });

  it("renderiza parecer premium completo (hero + risco crítico + movimento P0)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(premiumResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });
    expect(screen.getByTestId("parecer-tier-badge")).toHaveTextContent(
      "Premium",
    );
    expect(screen.getByTestId("parecer-risks-table")).toBeInTheDocument();
    expect(
      screen.getByText("Concentração imobiliária 70%"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("parecer-movimento-card")).toBeInTheDocument();
    expect(
      screen.getByText("Diversificar 15% do imobiliário"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("parecer-metricas-table")).toBeInTheDocument();
    expect(screen.getByTestId("parecer-disclaimer")).toBeInTheDocument();
  });

  it("renderiza tier free com badge Amostra + teaser '+N no Premium'", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(freeResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-tier-badge")).toHaveTextContent(
        "Amostra",
      );
    });
    // Teaser de horizonte execução
    expect(
      screen.getByTestId("parecer-horizonte-teaser-execucao"),
    ).toBeInTheDocument();
    expect(screen.getByText(/2 movimento/i)).toBeInTheDocument();
  });

  it("não cita Perini/Cerbasi/AUVP no DOM renderizado (sigilo §13)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(premiumResponse()),
      ),
    );

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });

    const html = container.innerHTML.toLowerCase();
    expect(html).not.toContain("perini");
    expect(html).not.toContain("cerbasi");
    expect(html).not.toContain("auvp");
    expect(html).not.toContain("viver de renda");
  });

  it("renderiza disclaimer fiduciário visível", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/reports/:reportId/planner-review`, () =>
        HttpResponse.json(premiumResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);
    await waitFor(() => {
      expect(screen.getByTestId("parecer-disclaimer")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/não constitui recomendação personalizada/i),
    ).toBeInTheDocument();
  });
});
